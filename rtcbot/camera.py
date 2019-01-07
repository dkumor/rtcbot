import threading
import asyncio
import logging
import time
import numpy as np

from .subscriptions import BaseSubscriptionHandler, MostRecentSubscription


class CVCamera(BaseSubscriptionHandler):
    """
    Uses a camera supported by OpenCV. 

    When initializing, can give an optional function which preprocesses frames as they are read, and returns the
    modified versions thereof. Please note that the preprocessing happens synchronously in the camera capture thread,
    so any processing should be relatively fast, and should avoid pure python code due to the GIL. Numpy and openCV functions
    should be OK.
    """

    def __init__(
        self,
        width=320,
        height=240,
        cameranumber=0,
        fps=30,
        preprocessframe=lambda x: x,
        loop=None,
    ):
        super().__init__(MostRecentSubscription)

        self._width = width
        self._height = height
        self._cameranumber = cameranumber
        self._fps = fps
        self._processframe = preprocessframe

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        # Start the camera stream in the background
        self._workerThread = threading.Thread(target=self._captureWorker)
        self._workerThread.daemon = True
        self._workerThread.start()
        self._shouldCloseWorkerThread = False

    def _captureWorker(self):
        """
        Runs the actual frame capturing code.
        """
        import cv2

        log = logging.getLogger("rtcbot.CVCamera")

        log.debug("Started camera thread")
        cap = cv2.VideoCapture(self._cameranumber)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        cap.set(cv2.CAP_PROP_FPS, self._fps)

        ret, frame = cap.read()
        if not ret:
            log.error(f"Camera Read Failed {ret}")
            cap.release()
            return
        else:
            log.debug("Camera Ready")

        t = time.time()
        i = 0
        while not self._shouldCloseWorkerThread:
            ret, frame = cap.read()
            if not ret:
                log.error(f"CV read error {ret}")
            else:
                # This optional function is given by the user. default is identity x->x
                frame = self._processframe(frame)

                # Send the frame to all subscribers
                self._loop.call_soon_threadsafe(self._put_nowait, frame)

                i += 1
                if time.time() > t + 1:
                    log.debug(f" {i} fps")
                    i = 0
                    t = time.time()
        cap.release()
        log.debug("Closing camera capture")

    def subscribe(self, subscription=None):
        """
        Subscribe to new frames as they come in. By default returns a MostRecentSubscription object, which can be awaited
        to get the most recent frame, and skips missed frames.

        Note that all subscribers get the same object,
        so if you are going to modify the values of the frame itself, please do so in a copy!::

            # Set up a camera and subscribe to new frames
            cam = CVCamera()
            subs = cam.subscribe()

            async def mytask():
                
                # Wait for the next frame
                myframe = await subs.get()

                # Do stuff with the frame

        If you want to have a different subscription type, you can pass anything which has a put_nowait method, 
        which is called each time a frame comes in::

            subs = cam.subscribe(asyncio.Queue()) # asyncio queue has a put_nowait method
            await subs.get()
        """
        # This function actually only exists for the docstring. It uses the superclass function.
        return super().subscribe(subscription)

    def close(self):
        """
        Closes capture on the camera, and waits until the camera capture thread joins
        """
        self._shouldCloseWorkerThread = True
        self._workerThread.join()


class PiCamera(CVCamera):
    """
    Instead of using OpenCV camera support, uses the picamera library for direct access to the Raspberry Pi's CSI camera.
    
    The interface is identical to CVCamera. When testing code on a desktop computer, it can be useful to
    have the code automatically choose the correct camera::

        try:
            import picamera # picamera import will fail if not on pi
            cam = PiCamera()
        except ImportError:
            cam = CVCamera()

    This enables simple drop-in replacement between the two.
    """

    def _captureWorker(self):
        log = logging.getLogger("rtcbot.PiCamera")
        import picamera

        with picamera.PiCamera() as cam:
            cam.resolution = (self._width, self._height)
            cam.framerate = self._fps
            time.sleep(2)  # Why is this needed?
            log.debug("PiCamera Ready")

            t = time.time()
            i = 0
            while not self._shouldCloseWorkerThread:
                # https://picamera.readthedocs.io/en/release-1.13/recipes2.html#capturing-to-an-opencv-object
                frame = np.empty((self._width * self._height * 3,), dtype=np.uint8)
                cam.capture(frame, "bgr", use_video_port=True)
                frame = frame.reshape((self._height, self._width, 3))

                # This optional function is given by the user. default is identity x->x
                frame = self._processframe(frame)

                # Set the frame arrival event
                self._loop.call_soon_threadsafe(self._put_nowait, frame)

                i += 1
                if time.time() > t + 1:
                    log.debug(f" {i} fps")
                    i = 0
                    t = time.time()
        log.debug("Closing camera capture")
