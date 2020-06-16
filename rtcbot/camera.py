import asyncio
import logging
import time
import numpy as np
import queue
import threading

from .base import (
    ThreadedSubscriptionProducer,
    BaseSubscriptionConsumer,
    SubscriptionClosed,
)
from .subscriptions import MostRecentSubscription


class CVCamera(ThreadedSubscriptionProducer):
    """
    Uses a camera supported by OpenCV. 

    When initializing, can give an optional function which preprocesses frames as they are read, and returns the
    modified versions thereof. Please note that the preprocessing happens synchronously in the camera capture thread,
    so any processing should be relatively fast, and should avoid pure python code due to the GIL. Numpy and openCV functions
    should be OK.
    """

    _log = logging.getLogger("rtcbot.CVCamera")

    def __init__(
        self,
        width=320,
        height=240,
        cameranumber=0,
        fps=30,
        preprocessframe=lambda x: x,
        loop=None,
    ):

        self._width = width
        self._height = height
        self._cameranumber = cameranumber
        self._fps = fps
        self._processframe = preprocessframe

        super().__init__(MostRecentSubscription, self._log, loop=loop)

    def _producer(self):
        """
        Runs the actual frame capturing code.
        """
        import cv2

        self._log.info("Started camera thread")
        cap = cv2.VideoCapture(self._cameranumber)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        cap.set(cv2.CAP_PROP_FPS, self._fps)

        ret, frame = cap.read()
        if not ret:
            self._log.error("Camera Read Failed %s", str(ret))
            cap.release()
            self._setError(ret)
            return
        else:
            self._log.debug("Camera Ready")

        t = time.time()
        i = 0
        self._setReady(True)
        while not self._shouldClose:
            ret, frame = cap.read()
            if not ret:
                self._log.error("CV read error %s", str(ret))
            else:
                # This optional function is given by the user. default is identity x->x
                frame = self._processframe(frame)

                # Send the frame to all subscribers
                self._put_nowait(frame)

                i += 1
                if time.time() > t + 1:
                    self._log.debug(" %d fps", i)
                    i = 0
                    t = time.time()
        cap.release()
        self._setReady(False)
        self._log.info("Ended camera capture")

    def subscribe(self, subscription=None):
        """
        Subscribe to new frames as they come in. By default returns a MostRecentSubscription object, which can be awaited
        to get the most recent frame, and skips missed frames.

        Note that all subscribers get the same frame data numpy array,
        so if you are going to modify the values of the array itself, please do so in a copy!::

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

    _log = logging.getLogger("rtcbot.PiCamera")

    def _producer(self):
        import picamera

        with picamera.PiCamera() as cam:
            cam.resolution = (self._width, self._height)
            cam.framerate = self._fps
            time.sleep(2)  # Why is this needed?
            self._log.debug("PiCamera Ready")
            self._setReady(True)

            t = time.time()
            i = 0
            while not self._shouldClose:
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
                    self._log.debug(" %d fps", i)
                    i = 0
                    t = time.time()
        self._setReady(False)
        self._log.info("Closed camera capture")


class CVDisplay(BaseSubscriptionConsumer):
    """
    Displays the frames in an openCV `imshow` window

    .. warning::
        Due to an issue with `threading in OpenCV on Mac <https://github.com/opencv/opencv/issues/6039>`_,
        CVDisplay does not work on Mac.
    """

    _log = logging.getLogger("rtcbot.CVDisplay")
    _windowNameIterator = 1

    # To allow multiple CVDisplays, all of them must be managed from a single thread
    _mainThread = None
    _mainQueue = queue.Queue()

    def __init__(self, name=None, loop=None):
        if CVDisplay._mainThread is None:
            CVDisplay._mainThread = threading.Thread(target=self._consumer)
            CVDisplay._mainThread.daemon = True
            CVDisplay._mainThread.start()

        self._name = name
        if self._name is None:
            self._name = str(CVDisplay._windowNameIterator)
            CVDisplay._windowNameIterator += 1
        super().__init__(MostRecentSubscription, self._log)

        asyncio.ensure_future(self._queueWriter())

    async def _queueWriter(self):
        self._setReady(True)
        while not self._shouldClose:
            try:
                data = await self._get()
                self._mainQueue.put_nowait({"name": self._name, "frame": data})
            except SubscriptionClosed:
                pass
        self._mainQueue.put_nowait({"name": self._name, "frame": None})

    @staticmethod
    def _consumer():
        import cv2

        CVDisplay._log.debug("Started Video Display Thread")

        while True:
            data = CVDisplay._mainQueue.get()
            if data["frame"] is None:
                cv2.destroyWindow(data["name"])
            else:
                cv2.imshow(data["name"], data["frame"])
            cv2.waitKey(1)
