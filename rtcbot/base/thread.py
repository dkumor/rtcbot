import asyncio
import logging
import threading

from .base import BaseSubscriptionConsumer, BaseSubscriptionProducer, SubscriptionClosed
from .events import threadedEventHandler


class ThreadedSubscriptionProducer(BaseSubscriptionProducer, threadedEventHandler):
    def __init__(
        self,
        defaultSubscriptionType=asyncio.Queue,
        logger=None,
        loop=None,
        daemonThread=True,
    ):
        threadedEventHandler.__init__(self, logger, loop)
        BaseSubscriptionProducer.__init__(self, defaultSubscriptionType, logger=logger)

        self._producerThread = threading.Thread(target=self._producer)
        self._producerThread.daemon = daemonThread
        self._producerThread.start()

    def _put_nowait(self, data):
        """
        To be called by the producer thread to insert data.

        """
        self._loop.call_soon_threadsafe(super()._put_nowait, data)

    def _producer(self):
        """
        This is the function run in another thread. You override the function with your own logic.

        The base implementation is used for testing
        """
        import queue

        self.testQueue = queue.Queue()
        self.testResultQueue = queue.Queue()

        # We are ready!
        self._setReady(True)
        while not self._shouldClose:
            # In real code, there should be a timeout in get to make sure _shouldClose is not True
            try:
                self._put_nowait(self.testQueue.get(1))
            except TimeoutError:
                pass
        self.testResultQueue.put("<<END>>")
        self._setReady(False)

    def _close(self):
        """
        Can be called by the external thread to close in a threadsafe manner
        """
        self._loop.call_soon_threadsafe(super()._close)

    def close(self):
        """
        Shuts down data gathering, and closes all subscriptions. Note that it is not recommended
        to call this in an async function, since it waits until the background thread joins.

        The object is meant to be used as a singleton, which is initialized at the start of your code,
        and is closed when exiting the program.
        """
        super().close()
        self._producerThread.join()


class ThreadedSubscriptionConsumer(BaseSubscriptionConsumer, threadedEventHandler):
    def __init__(
        self,
        directPutSubscriptionType=asyncio.Queue,
        logger=None,
        loop=None,
        daemonThread=True,
    ):
        threadedEventHandler.__init__(self, logger, loop)
        BaseSubscriptionConsumer.__init__(
            self, directPutSubscriptionType, logger=logger
        )

        if logger is None:
            self.__sclog = logging.getLogger(self.__class__.__name__).getChild(
                "ThreadedSubscriptionConsumer"
            )
        else:
            self.__sclog = logger.getChild("ThreadedSubscriptionConsumer")

        self._taskLock = threading.Lock()

        self._consumerThread = threading.Thread(target=self._consumer)
        self._consumerThread.daemon = daemonThread
        self._consumerThread.start()

    def _get(self):
        """
        This is not a coroutine - it is to be called in the worker thread.
        If the worker thread is to be shut down, raises a SubscriptionClosed exception.
        """
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
                return self._getTask.result(1)
            except asyncio.CancelledError:
                self.__sclog.debug("Subscription cancelled - checking for new tasks")
            except asyncio.TimeoutError:
                self.__sclog.debug("No incoming data for 1 second...")
                timedout = True
            except SubscriptionClosed:
                self.__sclog.debug(
                    "Incoming stream closed... Checking for new subscription"
                )
        self.__sclog.debug(
            "close() was called on the aio thread. raising SubscriptionClosed."
        )
        raise SubscriptionClosed("ThreadedSubscriptionConsumer has been closed")

    def _consumer(self):
        """
        This is the function that is to be overloaded by the superclass to read data.
        It is run in a separate thread. It should call self._get() to get the next datapoint coming
        from a subscription.

        The default implementation is used for testing
        """

        import queue

        self.testQueue = queue.Queue()

        # We are ready!
        self._setReady(True)
        try:
            while True:
                data = self._get()
                self.testQueue.put(data)
        except SubscriptionClosed:
            self.testQueue.put("<<END>>")
        self._setReady(False)

    def putSubscription(self, subscription):
        with self._taskLock:
            super().putSubscription(subscription)

    def _close(self):
        """
        Can be called by the external thread to close in a threadsafe manner
        """
        self._loop.call_soon_threadsafe(super()._close)

    def close(self):
        """
        The object is meant to be used as a singleton, which is initialized at the start of your code,
        and is closed when exiting the program.

        Make sure to run close on exit, since sometimes Python has trouble exiting from multiple threads without
        having them closed explicitly.
        """
        with self._taskLock:
            super().close()
        self._consumerThread.join()
