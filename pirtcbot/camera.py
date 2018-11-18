import threading

import asyncio


import logging
import time
import numpy as np


class FrameSubscription:
    """
    A FrameSubscription gives asynchronous access to video frames. It is returned by `CVCamera`, and allows 
    """

    def __init__(self, cvcamera):
        self.cvcamera = cvcamera
        self.frameEvent = asyncio.Event()

    async def getFrame(self):
        """
        Gets the most recent frame from the video stream. Note that all subscribers get the same object,
        so if you are going to modify the values of the array, please do so in a copy!::

            # Set up a camera and subscribe to new frames
            cam = CVCamera()
            subs = cam.frameSubscribe()

            async def mytask():
                
                # Wait for the next frame
                myframe = await subs.getFrame()

                # Do stuff with the frame

        One thing to note is that frames are not queued. The frame returned by getFrame is always the most recently captured frame.
        If you get a frame, and immediately call getFrame again, it will wait until the next frame is captured - it will not return
        frames that were already processed.
        
        """

        # Wait for the event marking the next frame
        await self.frameEvent.wait()

        # reset the event so that we can wait for the next frame
        self.frameEvent.clear()

        # the frameLock is a threading lock, so no awaiting here.
        self.cvcamera.frameLock.acquire()
        frame = self.cvcamera.frame
        self.cvcamera.frameLock.release()
        return frame


class CVCamera:
    """
    Uses a camera supported by OpenCV. 
    """

    def __init__(
        self, width=320, height=240, cameranumber=0, fps=30, preprocessframe=lambda x: x
    ):
        """
        Runs the camera. 
        
        Can give an optional function which preprocesses frames as they are read, and returns the
        modified versions thereof. Please note that the preprocessing happens synchronously in the reader thread,
        so any processing should be relatively fast, and should avoid pure python code due to the GIL. Numpy and openCV functions
        should be OK.
        """

        self.width = width
        self.height = height
        self.cameranumber = cameranumber
        self.fps = fps
        self.processframe = preprocessframe
        self.closed = False

        self.frameReadyEvent = asyncio.Event()
        self.frameLock = threading.Lock()
        self.frame = None

        self.loop = asyncio.get_event_loop()

        # Schedule the event handler. Should be changed to create_task when the pi updates to python 3.7
        self.handler = self.loop.create_task(self.__eventhandler())

        # Start the camera stream in the background
        self.camerathread = threading.Thread(target=self._capture_thread)
        self.camerathread.daemon = True
        self.camerathread.start()

        self.subscriptions = []

    def _capture_thread(self):
        import cv2

        log = logging.getLogger("pirtcbot.CVCamera")

        log.debug("Started camera thread")
        cap = cv2.VideoCapture(self.cameranumber)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)

        ret, frame = cap.read()
        if not ret:
            log.error(f"Camera Read Failed {ret}")
            cap.release()
            return
        else:
            log.debug("Camera Ready")

        t = time.time()
        i = 0
        while not self.closed:
            ret, frame = cap.read()
            if not ret:
                log.error(f"CV read error {ret}")
            else:
                # This optional function is given by the user. default is identity x->x
                frame = self.processframe(frame)

                with self.frameLock:
                    self.frame = frame

                # This code has a technical weakness, where under high load the handler could
                # pick up the next frame here, when it should have picked up the previous frame.
                # It would then have the frameReadyEvent set again for the same frame it just got.

                # Set the frame arrival event
                self.loop.call_soon_threadsafe(self.frameReadyEvent.set)

                i += 1
                if time.time() > t + 1:
                    log.debug(f" {i} fps")
                    i = 0
                    t = time.time()
        cap.release()
        log.debug("Closing camera capture")

    async def __eventhandler(self):
        """
        As frames arrive from the camera thread, we send out the events for all subscribed 
        objects. While this is technically an extra level of indirection, it is useful for enabling
        the frames to go to multiple destinations, allowing each destination to not worry about the others.
        """
        while not self.closed:
            # Get the frame coming from the thread
            await self.frameReadyEvent.wait()
            self.frameReadyEvent.clear()

            # Wake all the subscribers to the frame
            for s in self.subscriptions:
                s.frameEvent.set()

    def frameSubscribe(self):
        """
        Subscribe to new frames as they come in. Returns a FrameSubscription object, which 
        can be awaited to get the most recent frame. Skips frames that are missed 
        """
        subs = FrameSubscription(self)
        self.subscriptions.append(subs)
        return subs

    def close(self):
        """
        Closes capture on the camera, and waits until the camera capture thread joins
        """
        self.closed = True
        self.camerathread.join()


class PiCamera(CVCamera):
    """
    Instead of using OpenCV camera support, uses the picamera library for direct access to the CSI camera.
    
    The interface is identical to CVCamera. When testing code on a desktop computer, it can be useful to
    have the code automatically choose the correct camera::

        try:
            import picamera # picamera import will fail if not on pi
            cam = PiCamera()
        except ImportError:
            cam = CVCamera()

    This enables simple drop-in replacement between the two.
    """

    def _capture_thread(self):
        log = logging.getLogger("pirtcbot.PiCamera")
        import picamera

        with picamera.PiCamera() as cam:
            cam.resolution = (self.width, self.height)
            cam.framerate = self.fps
            time.sleep(2)  # Why is this needed?
            log.debug("PiCamera Ready")

            t = time.time()
            i = 0
            while not self.closed:
                # https://picamera.readthedocs.io/en/release-1.13/recipes2.html#capturing-to-an-opencv-object
                frame = np.empty((self.width * self.height * 3,), dtype=np.uint8)
                cam.capture(frame, "bgr", use_video_port=True)
                frame = frame.reshape((self.height, self.width, 3))

                # This optional function is given by the user. default is identity x->x
                frame = self.processframe(frame)

                with self.frameLock:
                    self.frame = frame

                # This code has a technical weakness, where under high load the handler could
                # pick up the next frame here, when it should have picked up the previous frame.
                # It would then have the frameReadyEvent set again for the same frame it just got.

                # Set the frame arrival event
                self.loop.call_soon_threadsafe(self.frameReadyEvent.set)

                i += 1
                if time.time() > t + 1:
                    log.debug(f" {i} fps")
                    i = 0
                    t = time.time()
        log.debug("Closing camera capture")
