import asyncio
import logging
import signal
import multiprocessing
import threading
import queue
import concurrent.futures

from rtcbot.base import BaseSubscriptionProducer, BaseSubscriptionConsumer, SubscriptionClosed


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
            self.__splog = logger.getChild("ProcessSubscriptionProducer")

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


class ProcessSubscriptionConsumer(BaseSubscriptionConsumer):
    def __init__(
        self,
        directPutSubscriptionType=asyncio.Queue,
        logger=None,
        loop=None,
        daemonProcess=True,
        joinTimeout=1,
    ):
        self._joinTimeout = joinTimeout
        if logger is None:
            self.__splog = logging.getLogger(self.__class__.__name__).getChild(
                "ProcessSubscriptionConsumer"
            )
        else:
            self.__splog = logger.getChild("ProcessSubscriptionConsumer")

        self.__closeEvent = multiprocessing.Event()

        self._taskLock = multiprocessing.Lock()
        self._getEvent = multiprocessing.Event()

        super().__init__(directPutSubscriptionType, logger=logger)

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        self._consumerQueue = multiprocessing.Queue()

        self.__queueReaderThread = threading.Thread(target=self.__queueReader)
        self.__queueReaderThread.daemon = True
        self.__queueReaderThread.start()

        self._consumerProcess = multiprocessing.Process(target=self.__consumerSetup)
        self._consumerProcess.daemon = daemonProcess
        self._consumerProcess.start()

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
        self._loop.call_soon_threadsafe(super()._setReady, value)

    def _setError(self, err):
        self._loop.call_soon_threadsafe(super()._setError, err)

    def _close(self):
        self._loop.call_soon_threadsafe(super()._close)

    def __queueReader(self):
        while not self._shouldClose:
            if self._getEvent.is_set():
                timedout = False
                while not self._shouldClose:
                    with self._taskLock:
                        # Only create a new task if it was finished, and did not time out
                        if not timedout:
                            self._getTask = asyncio.run_coroutine_threadsafe(
                                self._subscription.get(), self._loop
                            )
                    timedout = False
                    try:
                        self._consumerQueue.put(self._getTask.result(self._joinTimeout))
                        self._getEvent.clear()
                        break
                    except (asyncio.CancelledError, concurrent.futures.CancelledError):
                        self.__splog.debug("Subscription cancelled - checking for new tasks")
                    except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
                        self.__splog.debug(f"No incoming data for {self._joinTimeout} seconds...")
                        timedout = True
                    except SubscriptionClosed:
                        self.__splog.debug(
                            "Incoming stream closed... Checking for new subscription"
                        )

    def _get(self):
        """
        This is not a coroutine - it is to be called in the worker thread.
        If the worker thread is to be shut down, raises a SubscriptionClosed exception.
        """
        self._getEvent.set()
        while not self._shouldClose:
            try:
                return self._consumerQueue.get(timeout=self._joinTimeout)
            except queue.Empty:
                pass  # No need to notify each time we check whether we chould close

        self.__splog.debug(
            "close() was called on the aio thread. raising SubscriptionClosed."
        )
        raise SubscriptionClosed("ProcessSubscriptionConsumer has been closed")

    def putSubscription(self, subscription):
        with self._taskLock:
            super().putSubscription(subscription)

    def _consumer(self):
        """
        This is the function run in another thread. You override the function with your own logic.

        The base implementation is used for testing
        """

        # We are ready!
        self._setReady(True)
        # Have to think how to make this work
        # in testing

    def __consumerSetup(self):
        # This function sets up the consumer. In particular, it receives KeyboardInterrupts

        def handleInterrupt(sig, frame):
            self.__splog.debug("Received KeyboardInterrupt - not notifying process")

        old_handler = signal.signal(signal.SIGINT, handleInterrupt)
        try:
            self._consumer()
        except:
            self.__splog.exception("The remote process had an exception!")
        # self._setReady(False)
        self._shouldClose = True

        signal.signal(signal.SIGINT, old_handler)

        self.__splog.debug("Exiting remote process")

    def close(self):
        """
        Shuts down data gathering, and closes all subscriptions. Note that it is not recommended
        to call this in an async function, since it waits until the background thread joins.

        The object is meant to be used as a singleton, which is initialized at the start of your code,
        and is closed when shutting down.
        """
        with self._taskLock:
            super().close()
        self._consumerProcess.join(self._joinTimeout)
        self.__queueReaderThread.join()
        if self._consumerProcess.is_alive():
            self.__splog.debug("Process did not terminate in time. Killing it.")
            self._consumerProcess.terminate()
            self._consumerProcess.join()


class ProcessSubscriptionProducerConsumer(BaseSubscriptionConsumer, BaseSubscriptionProducer):
    """
    This base class represents an object which is both a producer and consumer, run as a separate process.
    This is common with two-way connections.
    Here, you call _get() to consume the incoming data, and _put_nowait() to produce outgoing data.
    """

    def __init__(
        self,
        directPutSubscriptionType=asyncio.Queue,
        defaultSubscriptionType=asyncio.Queue,
        logger=None,
        defaultAutosubscribe=False,
        loop=None,
        daemonProcess=True,
        joinTimeout=1,
    ):
        self._joinTimeout = joinTimeout
        if logger is None:
            self.__splog = logging.getLogger(self.__class__.__name__).getChild(
                "ProcessSubscriptionProducerConsumer"
            )
        else:
            self.__splog = logger.getChild("ProcessSubscriptionProducerConsumer")

        self.__closeEvent = multiprocessing.Event()

        self._taskLock = multiprocessing.Lock()
        self._getEvent = multiprocessing.Event()

        BaseSubscriptionConsumer.__init__(
            self, directPutSubscriptionType, logger=logger
        )
        BaseSubscriptionProducer.__init__(
            self,
            defaultSubscriptionType,
            logger=logger,
            defaultAutosubscribe=defaultAutosubscribe,
        )

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        self._producerQueue = multiprocessing.Queue()
        self._consumerQueue = multiprocessing.Queue()

        self.__queueConsumerThread = threading.Thread(target=self.__queueConsumer)
        self.__queueConsumerThread.daemon = True
        self.__queueConsumerThread.start()

        self.__queueProducerThread = threading.Thread(target=self.__queueProducer)
        self.__queueProducerThread.daemon = True
        self.__queueProducerThread.start()

        self._producerConsumerProcess = multiprocessing.Process(target=self.__producerConsumerSetup)
        self._producerConsumerProcess.daemon = daemonProcess
        self._producerConsumerProcess.start()

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
        self._loop.call_soon_threadsafe(super()._setReady, value)

    def _setError(self, err):
        self._loop.call_soon_threadsafe(super()._setError, err)

    def _close(self):
        self._loop.call_soon_threadsafe(super()._close)

    def close(self):
        BaseSubscriptionConsumer.close(self)
        BaseSubscriptionProducer.close(self)

    def _close(self):
        self.close()

    def __queueProducer(self):
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

    def __queueConsumer(self):
        while not self._shouldClose:
            if self._getEvent.is_set():
                timedout = False
                while not self._shouldClose:
                    with self._taskLock:
                        # Only create a new task if it was finished, and did not time out
                        if not timedout:
                            self._getTask = asyncio.run_coroutine_threadsafe(
                                self._subscription.get(), self._loop
                            )
                    timedout = False
                    try:
                        self._consumerQueue.put(self._getTask.result(self._joinTimeout))
                        self._getEvent.clear()
                        break
                    except (asyncio.CancelledError, concurrent.futures.CancelledError):
                        self.__splog.debug("Subscription cancelled - checking for new tasks")
                    except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
                        self.__splog.debug(f"No incoming data for {self._joinTimeout} seconds...")
                        timedout = True
                    except SubscriptionClosed:
                        self.__splog.debug(
                            "Incoming stream closed... Checking for new subscription"
                        )

    def __producerConsumerSetup(self):
        # This function sets up the producerConsumer. In particular, it receives KeyboardInterrupts

        def handleInterrupt(sig, frame):
            self.__splog.debug("Received KeyboardInterrupt - not notifying process")

        old_handler = signal.signal(signal.SIGINT, handleInterrupt)
        try:
            self._producerConsumer()
        except:
            self.__splog.exception("The remote process had an exception!")
        # self._setReady(False)
        self._shouldClose = True

        signal.signal(signal.SIGINT, old_handler)

        self.__splog.debug("Exiting remote process")

    def _put_nowait(self, data):
        """
        To be called by the producer thread to insert data.

        """
        self.__splog.debug("Sending data from remote process")
        self._producerQueue.put_nowait(data)

    def _get(self):
        """
        This is not a coroutine - it is to be called in the worker thread.
        If the worker thread is to be shut down, raises a SubscriptionClosed exception.
        """
        self._getEvent.set()
        while not self._shouldClose:
            try:
                return self._consumerQueue.get(timeout=self._joinTimeout)
            except queue.Empty:
                pass  # No need to notify each time we check whether we chould close

        self.__splog.debug(
            "close() was called on the aio thread. raising SubscriptionClosed."
        )
        raise SubscriptionClosed("ProcessSubscriptionProducerConsumer has been closed")

    def putSubscription(self, subscription):
        with self._taskLock:
            super().putSubscription(subscription)

    def _producerConsumer(self):
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
        self._producerConsumerProcess.join(self._joinTimeout)
        self.__queueProducerThread.join()
        self.__queueConsumerThread.join()
        if self._producerConsumerProcess.is_alive():
            self.__splog.debug("Process did not terminate in time. Killing it.")
            self._producerConsumerProcess.terminate()
            self._producerConsumerProcess.join()
