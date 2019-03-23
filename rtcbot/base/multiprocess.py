import asyncio
import logging
import signal
import multiprocessing
import threading
import queue

from .base import BaseSubscriptionProducer, SubscriptionClosed


class internalSubscriptionMessage:
    # This message is sent from the remote process to communicate with local stuff
    def __init__(self, type, value):
        self.type = type
        self.value = value


class ProcessSubscriptionProducer(BaseSubscriptionProducer):
    def __init__(
        self,
        defaultSubscriptionType=asyncio.Queue,
        logger=None,
        loop=None,
        daemonProcess=True,
        joinTimeout=1,
    ):
        self._joinTimeout = joinTimeout
        if logger is None:
            self.__splog = logging.getLogger(self.__class__.__name__).getChild(
                "ProcessSubscriptionProducer"
            )
        else:
            self.__splog = logger.getChild("ProcessSubscriptionConsumer")

        self.__closeEvent = multiprocessing.Event()

        super().__init__(defaultSubscriptionType, logger=logger)

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        self._producerQueue = multiprocessing.Queue()

        self.__queueReaderThread = threading.Thread(target=self.__queueReader)
        self.__queueReaderThread.daemon = True
        self.__queueReaderThread.start()

        self._producerProcess = multiprocessing.Process(target=self.__producerSetup)
        self._producerProcess.daemon = daemonProcess
        self._producerProcess.start()

    @property
    def _shouldClose(self):
        # We need to check the event
        return self.__closeEvent.is_set()

    @_shouldClose.setter
    def _shouldClose(self, value):
        self.__splog.debug("Setting _shouldClose to %s", value)
        if value:
            self.__closeEvent.set()
        else:
            self.__closeEvent.clear()

    def _setReady(self, value):
        # Here, we actually exploit the main producerQueue to send the events to the main thread
        self.__splog.debug("setting ready to %s", value)
        self._producerQueue.put_nowait(internalSubscriptionMessage("ready", value))

    def _setError(self, err):
        # Here, we actually exploit the main producerQueue to send the events to the main thread
        self.__splog.debug("setting error to %s", err)
        self._producerQueue.put_nowait(internalSubscriptionMessage("error", err))

    def _close(self):
        # Here, we actually exploit the main producerQueue to send the events to the main thread
        self.__splog.debug("sending close message")
        self._producerQueue.put_nowait(internalSubscriptionMessage("close", True))

    def __queueReader(self):
        while not self._shouldClose:
            try:
                data = self._producerQueue.get(timeout=self._joinTimeout)
                if isinstance(data, internalSubscriptionMessage):
                    if data.type == "ready":
                        self._loop.call_soon_threadsafe(super()._setReady, data.value)
                    elif data.type == "error":
                        self._loop.call_soon_threadsafe(super()._setError, data.value)
                    elif data.type == "close":
                        self._loop.call_soon_threadsafe(super()._close)
                    else:
                        self.__splog.error("Unrecognized message: %s", data)
                else:
                    self.__splog.debug("Received data from remote process")
                    self._loop.call_soon_threadsafe(super()._put_nowait, data)
            except queue.Empty:
                pass  # No need to notify each time we check whether we chould close

    def _put_nowait(self, data):
        """
        To be called by the producer thread to insert data.

        """
        self.__splog.debug("Sending data from remote process")
        self._producerQueue.put_nowait(data)

    def __producerSetup(self):
        # This function sets up the producer. In particular, it receives KeyboardInterrupts

        def handleInterrupt(sig, frame):
            self.__splog.debug("Received KeyboardInterrupt - not notifying process")

        old_handler = signal.signal(signal.SIGINT, handleInterrupt)
        try:
            self._producer()
        except:
            self.__splog.exception("The remote process had an exception!")
        # self._setReady(False)
        self._shouldClose = True

        signal.signal(signal.SIGINT, old_handler)

        self.__splog.debug("Exiting remote process")

    def _producer(self):
        """
        This is the function run in another thread. You override the function with your own logic.

        The base implementation is used for testing
        """

        # We are ready!
        self._setReady(True)
        # Have to think how to make this work
        # in testing

    def close(self):
        """
        Shuts down data gathering, and closes all subscriptions. Note that it is not recommended
        to call this in an async function, since it waits until the background thread joins.

        The object is meant to be used as a singleton, which is initialized at the start of your code,
        and is closed when shutting down.
        """
        super().close()
        self._producerProcess.join(self._joinTimeout)
        self.__queueReaderThread.join()
        if self._producerProcess.is_alive():
            self.__splog.debug("Process did not terminate in time. Killing it.")
            self._producerProcess.terminate()
            self._producerProcess.join()
