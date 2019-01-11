import asyncio
import threading
import logging
import time


class BaseSubscriptionProducer:
    def __init__(
        self,
        defaultSubscriptionClass=asyncio.Queue,
        defaultAutosubscribe=False,
        logger=None,
        ready=True,
    ):
        self.__subscriptions = set()
        self.__defaultSubscriptionClass = defaultSubscriptionClass
        self.__defaultSubscription = None

        self._shouldClose = False

        if logger is None:
            self.__splog = logging.getLogger(self.__class__.__name__).getChild(
                "SubscriptionProducer"
            )
        else:
            self.__splog = logger.getChild("SubscriptionProducer")

        # Once all init is finished, need to set self._ready to True if we don't set it by default
        self._ready = ready

        if defaultAutosubscribe:
            self.__defaultSubscribe()

    def subscribe(self, subscription=None):
        """
        Subscribes to new data as it comes in. There can be multiple independent
        subscriptions active at the same time.
        """
        if subscription is None:
            subscription = self.__defaultSubscriptionClass()
        self.__splog.debug("Added subscription %s", subscription)
        self.__subscriptions.add(subscription)
        return subscription

    def _put_nowait(self, element):
        for s in self.__subscriptions:
            self.__splog.debug("put data into %s", s)
            s.put_nowait(element)

    def unsubscribe(self, subscription=None):
        """
        Removes the given subscription, so that it no longer gets updated::

            subs = o.subscribe()
            o.unsubscribe(subs)

        If no argument is given, removes the default subscription created by `get()`.
        If none exists, then does nothing.
        """
        if subscription is None:
            if self.__defaultSubscription is not None:
                self.__splog.debug("Removing default subscription")
                self.unsubscribe(self.__defaultSubscription)
                self.__defaultSubscription = None
            else:
                # Otherwise, do nothing
                self.__splog.debug(
                    "Unsubscribe called, but no default subscription is active. Doing nothing."
                )
        else:
            self.__splog.debug("Removing subscription %s", subscription)
            self.__subscriptions.remove(subscription)

    def unsubscribeAll(self):
        """
        Removes all currently active subscriptions, including the default one if it was intialized.
        """
        self.__subscriptions = set()
        self.__defaultSubscription = None

    def __defaultSubscribe(self):
        if self.__defaultSubscription is None:
            self.__defaultSubscription = self.subscribe()
            self.__splog.debug(
                "Created default subscription %s", self.__defaultSubscription
            )

    async def get(self):
        """
        Same as `o.subscribe().get()`. On the first call, creates a default 
        subscription, and all subsequent calls to `get()` use that subscription.

        If `unsubscribe` is called, the subscription is deleted, so a subsequent call to `get`
        will create a new one::

            data = await o.get() # Creates subscription on first call
            data = await o.get() # Same subscription
            o.unsubscribe()
            data2 = await o.get() # A new subscription

        The above code is equivalent to the following::

            defaultSubscription = o.subscribe()
            data = await defaultSubscription.get()
            data = await defaultSubscription.get()
            o.unsubscribe(defaultSubscription)
            newDefaultSubscription = o.subscribe()
            data = await newDefaultSubscription.get()
        """
        self.__defaultSubscribe()

        return await self.__defaultSubscription.get()

    def close(self):
        self._shouldClose = True
        self.unsubscribeAll()
        self._ready = False

    @property
    def ready(self):
        return self._ready  # No need to lock, as this thread only reads a binary T/F


class BaseSubscriptionConsumer:
    """
    A base class upon which consumers of subscriptions can be built. 

    The BaseSubscriptionConsumer class handles the logic of switching incoming subscriptions mid-stream and
    all the other annoying stuff.
    """

    def __init__(
        self, directPutSubscriptionType=asyncio.Queue, logger=None, ready=True
    ):

        self.__directPutSubscriptionType = directPutSubscriptionType
        self.__directPutSubscription = directPutSubscriptionType()
        self._subscription = self.__directPutSubscription
        self._shouldClose = False

        # The task used for getting data in _get. This allows us to cancel the task, and switch out subscriptions
        # at any point in time!
        self._getTask = None

        if logger is None:
            self.__sclog = logging.getLogger(self.__class__.__name__).getChild(
                "SubscriptionConsumer"
            )
        else:
            self.__sclog = logger.getChild("SubscriptionConsumer")

        # Once all init is finished, need to set self._ready to True
        self._ready = ready

    async def _get(self):
        """
        This function is to be called by the backend of the StreamReader to get new data instead of 
        calling get() on the subscription itself.
        """
        while True:
            self._getTask = asyncio.create_task(self._subscription.get())

            try:
                await self._getTask
            except asyncio.CancelledError:
                # If the coroutine was cancelled, it means that self._subscription was replaced,
                # so we just loop back to await the new one
                self.__sclog.debug(
                    "Subscription cancelled - waiting for new subscription's data"
                )
            else:
                return self._getTask.result()

    def put_nowait(self, data):
        """
        Direct API for sending data to the reader, without needing to pass a subscription.
        """
        if self._subscription != self.__directPutSubscription:
            # If the subscription is not the default, stop, which will create a new default,
            # to which we can add our data
            self.stop()
        self.__sclog.debug(
            "put data with subscription %s", self.__directPutSubscription
        )
        self.__directPutSubscription.put_nowait(data)

    def putSubscription(self, subscription):
        """
        Given a subscription, such that `await subscription.get()` returns successive pieces of data,
        keeps reading the subscription until it is replaced.
        Equivalent to doing the following in the background::

            while True:
                sr.put_nowait(await subscription.get())
        """
        self.__sclog.debug(
            "Changing subscription from %s to %s", self._subscription, subscription
        )
        self._subscription = subscription
        if self._getTask is not None and not self._getTask.done():
            self.__sclog.debug("Canceling currently running subscription")
            self._getTask.cancel()

    def stop(self):
        """
        Stops reading the current subscription. Forgets any subscription,
        and waits for new data, which is passed through `put_nowait` or `readSubscription`
        """
        self.__directPutSubscription = self.__directPutSubscriptionType()
        self.putSubscription(
            self.__directPutSubscription
        )  # read the empty subscription

    def close(self):
        """
        Close the consumer - 
        """

        self._ready = False
        self._shouldClose = True
        if self._getTask is not None and not self._getTask.done():
            self._getTask.cancel()

    @property
    def ready(self):
        return self._ready  # No need to lock, as this thread only reads a binary T/F


class ThreadedSubscriptionProducer(BaseSubscriptionProducer):
    def __init__(self, defaultSubscriptionType=asyncio.Queue, logger=None, loop=None):
        super().__init__(defaultSubscriptionType, logger=logger, ready=False)

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        self._producerThread = threading.Thread(target=self._producer)
        self._producerThread.daemon = True
        self._producerThread.start()

    def _put_nowait(self, data):
        """
        To be called by the producer thread to insert data.

        """
        # raises a StopIteration if the producer was closed, and the thread should exit
        # if self._shouldClose:
        #    raise StopIteration("ThreadedSubscriptionProducer has been closed")
        # EDIT: no it doesn't because that is just too annoying
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
        self._ready = True
        try:
            while True:
                # In real code, there should be a timeout in get to make sure _shouldClose is not True
                self._put_nowait(self.testQueue.get())
        except StopIteration:
            self.testResultQueue.put("<<END>>")

    def close(self):
        super().close()
        self._producerThread.join()


class ThreadedSubscriptionConsumer(BaseSubscriptionConsumer):
    def __init__(self, directPutSubscriptionType=asyncio.Queue, logger=None, loop=None):
        super().__init__(directPutSubscriptionType, logger=logger, ready=False)

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        if logger is None:
            self.__sclog = logging.getLogger(self.__class__.__name__).getChild(
                "ThreadedSubscriptionConsumer"
            )
        else:
            self.__sclog = logger.getChild("ThreadedSubscriptionConsumer")

        self._taskLock = threading.Lock()

        self._consumerThread = threading.Thread(target=self._consumer)
        self._consumerThread.daemon = True
        self._consumerThread.start()

    def _get(self):
        """
        This is not a coroutine - it is to be called in the worker thread.
        If the worker thread is to be shut down, raises a StopIteration exception.
        """
        while not self._shouldClose:
            with self._taskLock:
                self._getTask = asyncio.run_coroutine_threadsafe(
                    self._subscription.get(), self._loop
                )
            try:
                return self._getTask.result(10)
            except asyncio.CancelledError:
                self.__sclog.debug(
                    "Subscription cancelled - waiting for new subscription's data"
                )
            except asyncio.TimeoutError:
                self.__sclog.debug("No incoming data for 10 seconds...")
        self.__sclog.debug(
            "close() was called on the aio thread. raising StopIteration."
        )
        raise StopIteration("ThreadedSubscriptionConsumer has been closed")

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
        self._ready = True
        try:
            while True:
                data = self._get()
                self.testQueue.put(data)
        except StopIteration:
            self.testQueue.put("<<END>>")

    def putSubscription(self, subscription):
        with self._taskLock:
            super().putSubscription(subscription)

    def close(self):
        with self._taskLock:
            super().close()
        self._consumerThread.join()


class SubscriptionProducer(BaseSubscriptionProducer):
    def put_nowait(self, element):
        self._put_nowait(element)


class SubscriptionConsumer(BaseSubscriptionConsumer):
    async def get(self):
        return await self._get()


class BaseSubscriptionProducerConsumer(
    BaseSubscriptionConsumer, BaseSubscriptionProducer
):
    """
    This base class represents an object which is both a producer and consumer. This is common
    with two-way connections.

    Here, you call _get() to consume the incoming data, and _put_nowait() to produce outgoing data.
    """

    def __init__(
        self,
        directPutSubscriptionType=asyncio.Queue,
        defaultSubscriptionType=asyncio.Queue,
        logger=None,
        ready=False,
        defaultAutosubscribe=False,
    ):
        BaseSubscriptionConsumer.__init__(
            self, directPutSubscriptionType, logger=logger, ready=ready
        )
        BaseSubscriptionProducer.__init__(
            self,
            defaultSubscriptionType,
            logger=logger,
            ready=ready,
            defaultAutosubscribe=defaultAutosubscribe,
        )

    def close(self):
        BaseSubscriptionConsumer.close(self)
        BaseSubscriptionProducer.close(self)

