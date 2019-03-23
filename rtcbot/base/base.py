import asyncio
import logging
import inspect

from .events import baseEventHandler


class SubscriptionClosed(Exception):
    """
    This error is returned internally by :func:`_get` in all subclasses of :class:`BaseSubscriptionConsumer`
    when :func:`close` is called, and signals the consumer to shut down. For more detail, see :func:`BaseSubscriptionConsumer._get`.
    """

    pass


class NoClosedSubscription:
    """
    NoClosedSubscription wraps a callback, and doesn't pass forward SubscriptionClosed errors - it converts them to
    :class:`asyncio.CancelledError`. This allows exiting the application in a clean way.
    """

    def __init__(self, awaitable):
        self._callback = awaitable

    async def get(self):
        try:
            return await self._callback()
        except SubscriptionClosed:
            raise asyncio.CancelledError("Subscription was Closed")


class BaseSubscriptionProducer(baseEventHandler):
    """
    This is a base class upon which all things that emit data in RTCBot are built.

    This class offers all the machinery necessary to keep track of subscriptions to the incoming data.
    The most important methods from a user's perspective are the :func:`subscribe`, :func:`get` and :func:`close` functions,
    which manage subscriptions to the data, and finally close everything.

    From an subclass's perspective, the most important pieces are the :func:`_put_nowait` method,
    and the :attr:`_shouldClose` and :attr:`_ready` attributes.

    Once the subclass is ready, it should set :attr:`_ready` to True, and when receiving data,
    it should call :func:`_put_nowait` to insert it. Finally, it should either listen to :attr:`_shouldClose` or override
    the close method to stop producing data.

    Example:
        A sample basic class that builds on the :class:`BaseSubscriptionProvider`::

            class MyProvider(BaseSubscriptionProvider):
                def __init__(self):
                    super().__init__()

                    # Add data in the background
                    asyncio.ensure_future(self._dataProducer)

                async def _dataProducer(self):
                    self._ready = True
                    while not self._shouldClose:
                        data = await get_data_here()
                        self._put_nowait(data)
                    self._ready = False
                def close():
                    super().close()
                    stop_gathering_data()

            # you can now subscribe to the data
            s = MyProvider().subscribe()

    Args:
        defaultSubscriptionClass (optional):
            The subscription type to return by default if :func:`subscribe` is called without arguments.
            By default, it uses :class:`asyncio.Queue`::

                sp = SubscriptionProducer(defaultSubscriptionClass=asyncio.Queue)
                q = sp.subscribe()

                q is asyncio.Queue # True
        defaultAutosubscribe (bool,optional):
            Calling :func:`get` creates a default subscription on first time it is called. Sometimes the data is very critical,
            and you want the default subscription to be created right away, so it never misses data. Be aware,
            though, if your `defaultSubscriptionClass` is :class:`asyncio.Queue`, if :func:`get` is never called,
            such as when someone just uses :func:`subscribe`, it will just keep piling up queued data!
            To avoid this, it is `False` by default.
        logger (optional):
            Your class logger - it gets a child of this logger for debug messages. If nothing is passed,
            creates a root logger for your class, and uses a child for that.
        ready (bool,optional):
            Your producer probably doesn't need setup time, so this is set to `True` automatically, which 
            automatically sets :attr:`_ready`. If you need to do background tasks, set this to False.
    """

    def __init__(
        self,
        defaultSubscriptionClass=asyncio.Queue,
        defaultAutosubscribe=False,
        logger=None,
    ):
        self.__subscriptions = set()
        self.__callbacks = set()
        self.__cocallbacks = set()
        self.__defaultSubscriptionClass = defaultSubscriptionClass
        self.__defaultSubscription = None

        #: Whether or not :func:`close` was called, and the user wants the class to stop
        #: gathering data. Should only be accessed from a subclass.
        self._shouldClose = False

        if logger is None:
            self.__splog = logging.getLogger(self.__class__.__name__).getChild(
                "SubscriptionProducer"
            )
        else:
            self.__splog = logger.getChild("SubscriptionProducer")

        if defaultAutosubscribe:
            self.__defaultSubscribe()

        super().__init__(self.__splog)

    def subscribe(self, subscription=None):
        """
        Allows subscribing to new data as it comes in, returning a subscription (see :doc:`subscriptions`)::

            s = myobj.subscribe()
            while True:
                data = await s.get()
                print(data)

        There can be multiple subscriptions active at the same time, each of which get identical data.
        Each call to :func:`subscribe` returns a new, independent subscription::

            s1 = myobj.subscribe()
            s2 = myobj.subscribe()
            while True:
                assert await s1.get()== await s2.get()

        This function can also be used as a callback::

            @myobj.subscribe
            def newData(data):
                print("Got data:",data)

        If passed an argument, it attempts to use the given callback/coroutine/subscription to notify of incoming data.

        Args:
            subscription (optional):
                An optional existing subscription to subscribe to. This can be one of 3 things:
                    1) An object which has the method `put_nowait` (see :doc:`subscriptions`)::
                        
                        q = asyncio.Queue()
                        myobj.subscribe(q)
                        while True:
                            data = await q.get()
                            print(data)
                    2) A callback function - this will be called the moment new data is inserted::
                        
                        @myobj.subscribe
                        def myfunction(data):
                            print(data)
                    3) An coroutine callback - A future of this coroutine is created on each insert::
                        
                        @myobj.subscribe
                        async def myfunction(data):
                            await asyncio.sleep(5)
                            print(data)
                    
        Returns:
            A subscription. If one was passed in, returns the passed in subscription::

                q = asyncio.Queue()
                ret = thing.subscribe(q)
                assert ret==q

        """
        if subscription is None:
            subscription = self.__defaultSubscriptionClass()
        if callable(getattr(subscription, "put_nowait", None)):
            self.__splog.debug("Added subscription %s", subscription)
            self.__subscriptions.add(subscription)
        elif inspect.iscoroutinefunction(subscription):
            self.__splog.debug("Added async callback %s", subscription)
            self.__cocallbacks.add(subscription)
        else:
            self.__splog.debug("Added callback %s", subscription)
            self.__callbacks.add(subscription)
        return subscription

    def _put_nowait(self, element):
        """
        Used by subclasses to add data to all subscriptions. This method internally
        calls all registered callbacks for you, so you only need to worry about
        the single function call.

        Warning:
            Only call this if you are subclassing :class:`BaseSubscriptionProducer`.
        """
        for s in self.__subscriptions:
            self.__splog.debug("put data into %s", s)
            s.put_nowait(element)
        for c in self.__callbacks:
            self.__splog.debug("calling %s", c)
            c(element)
        for c in self.__cocallbacks:
            self.__splog.debug("setting up future for %s", c)
            asyncio.ensure_future(c(element))

    def unsubscribe(self, subscription=None):
        """
        Removes the given subscription, so that it no longer gets updated::

            subs = myobj.subscribe()
            myobj.unsubscribe(subs)

        If no argument is given, removes the default subscription created by `get()`.
        If none exists, then does nothing.

        Args:
            subscription (optional):
                Anything that was passed into/returned from :func:`subscribe`.

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
            if callable(getattr(subscription, "put_nowait", None)):
                self.__splog.debug("Removing subscription %s", subscription)
                self.__subscriptions.remove(subscription)
            elif inspect.iscoroutinefunction(subscription):
                self.__splog.debug("Removing async callback %s", subscription)
                self.__cocallbacks.remove(subscription)
            else:
                self.__splog.debug("Removing callback %s", subscription)
                self.__callbacks.remove(subscription)

    def unsubscribeAll(self):
        """
        Removes all currently active subscriptions, including the default one if it was intialized.
        """
        self.__subscriptions = set()
        self.__callbacks = set()
        self.__cocallbacks = set()
        self.__defaultSubscription = None

    def __defaultSubscribe(self):
        if self.__defaultSubscription is None:
            self.__defaultSubscription = self.subscribe()
            self.__splog.debug(
                "Created default subscription %s", self.__defaultSubscription
            )

    async def get(self):
        """
        Behaves similarly to :func:`subscribe().get()`. On the first call, creates a default 
        subscription, and all subsequent calls to :func:`get()` use that subscription.

        If :func:`unsubscribe` is called, the subscription is deleted, so a subsequent call to :func:`get`
        will create a new one::

            data = await myobj.get() # Creates subscription on first call
            data = await myobj.get() # Same subscription
            myobj.unsubscribe()
            data2 = await myobj.get() # A new subscription

        The above code is equivalent to the following::

            defaultSubscription = myobj.subscribe()
            data = await defaultSubscription.get()
            data = await defaultSubscription.get()
            myobj.unsubscribe(defaultSubscription)
            newDefaultSubscription = myobj.subscribe()
            data = await newDefaultSubscription.get()
        """
        self.__defaultSubscribe()

        return await self.__defaultSubscription.get()

    def close(self):
        """
        Shuts down the data gathering, and removes all subscriptions.
        """
        self.__splog.debug("Closing")
        self._shouldClose = True
        self.unsubscribeAll()
        super().close()

    def _close(self):
        """
        This function allows closing from the handler itself. Don't call close() directly when implementing
        producers or consumers. call `_close` instead.
        """
        self.close()


class BaseSubscriptionConsumer(baseEventHandler):
    """
    A base class upon which consumers of subscriptions can be built. 

    The BaseSubscriptionConsumer class handles the logic of switching incoming subscriptions mid-stream and
    all the other annoying stuff.
    """

    def __init__(self, directPutSubscriptionType=asyncio.Queue, logger=None):

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

        super().__init__(self.__sclog)

    async def _get(self):
        """
        Warning:
            Only call this if you are subclassing :class:`BaseSubscriptionConsumer`.

        This function is to be awaited by a subclass to get the next datapoint 
        from the active subscription. It internally handles the subscription for you,
        and transparently manages the user switching a subscription during runtime::

            myobj.putSubscription(x)
            #  await self._get() waits on next datapoint from x
            myobj.putSubscription(y)
            # _get transparently switched to waiting on y

        Raises:
            :class:`SubscriptionClosed`:
                If :func:`close` was called, this error is raised, signalling your 
                data processing function to clean up and exit.

        Returns:
            The next datapoint that was put or subscribed to from the currently active
            subscription.

        
        """
        while not self._shouldClose:
            # create_task not supported on older python versions
            # self._getTask = asyncio.create_task(self._subscription.get())
            self._getTask = asyncio.ensure_future(self._subscription.get())

            try:
                self.__sclog.debug("Waiting for new data...")
                await self._getTask
                return self._getTask.result()
            except asyncio.CancelledError:
                # If the coroutine was cancelled, it means that self._subscription was replaced,
                # so we just loop back to await the new one
                self.__sclog.debug("Subscription cancelled  - checking for new tasks")
            except SubscriptionClosed:
                self.__sclog.debug(
                    "Incoming subscription closed - checking for new subscription"
                )
            except:
                self.__sclog.exception("Got unrecognized error from task. ignoring:")

        self.__sclog.debug("close() was called. raising SubscriptionClosed.")
        raise SubscriptionClosed("SubscriptionConsumer has been closed")

    def put_nowait(self, data):
        """
        This function allows you to directly send data to the object, without needing to
        go through a subscription::

            while True:
                data = get_data()
                myobj.put_nowait(data)

        The :func:`put_nowait` method is the simplest way to process a new chunk of data.

        note:
            If there is currently an active subscription initialized through :func:`putSubscription`,
            it is immediately stopped, and the object waits only for :func:`put_nowait`::

                myobj.putSubscription(s)
                myobj.put_nowait(mydata) # unsubscribes from s

                assert myobj.subscription is None
        """
        if self._subscription != self.__directPutSubscription:
            # If the subscription is not the default, stop, which will create a new default,
            # to which we can add our data
            self.stopSubscription()
        self.__sclog.debug(
            "put data with subscription %s", self.__directPutSubscription
        )
        self.__directPutSubscription.put_nowait(data)

    def putSubscription(self, subscription):
        """
        Given a subscription, such that `await subscription.get()` returns successive pieces of data,
        keeps reading the subscription forever::

            q = asyncio.Queue() # an asyncio.Queue has a get() coroutine
            myobj.putSubscription(q)

            q.put_nowait(data)

        Equivalent to doing the following in the background::

            while True:
                myobj.put_nowait(await q.get())


        You can replace a currently running subscription with a new one at any point in time::

            q1 = asyncio.Queue()
            myobj.putSubscription(q1)

            assert myobj.subscription == q1

            q2 = asyncio.Queue()
            myobj.putSubscription(q2)

            assert myobj.subscription == q2

        """
        if subscription == self._subscription:
            return
        self.__sclog.debug(
            "Changing subscription from %s to %s", self._subscription, subscription
        )
        self._subscription = subscription
        if self._getTask is not None and not self._getTask.done():
            self.__sclog.debug("Canceling currently running subscription")
            self._getTask.cancel()

    def stopSubscription(self):
        """
        Stops reading the current subscription::

            q = asyncio.Queue()
            myobj.putSubscription(q)

            assert myobj.subscription == q

            myobj.stopSubscription()

            assert myobj.subscription is None

            # You can then subscribe again (or put_nowait)
            myobj.putSubscription(q)
            assert myobj.subscription == q

        The object is not affected, other than no longer listening to the subscription, 
        and not processing new data until something is inserted.

        """
        self.__directPutSubscription = self.__directPutSubscriptionType()
        self.putSubscription(
            self.__directPutSubscription
        )  # read the empty subscription

    def close(self):
        """
        Cleans up and closes the object.
        """
        self.__sclog.debug("Closing")
        self._shouldClose = True
        if self._getTask is not None and not self._getTask.done():
            self._getTask.cancel()
        super().close()

    @property
    def subscription(self):
        """
        Returns the currently active subscription::

            q = asyncio.Queue()
            myobj.putSubscription(q)
            assert myobj.subscription == q

            myobj.stopSubscription()
            assert myobj.subscription is None

            myobj.put_nowait(data)
            assert myobj.subscription is None

        """
        if self._subscription == self.__directPutSubscription:
            return None
        return self._subscription


class SubscriptionProducer(BaseSubscriptionProducer):
    def put_nowait(self, element):
        self._put_nowait(element)


class SubscriptionConsumer(BaseSubscriptionConsumer):
    async def get(self):
        return await self._get()


class SubscriptionProducerConsumer(BaseSubscriptionConsumer, BaseSubscriptionProducer):
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
        defaultAutosubscribe=False,
    ):
        BaseSubscriptionConsumer.__init__(
            self, directPutSubscriptionType, logger=logger
        )
        BaseSubscriptionProducer.__init__(
            self,
            defaultSubscriptionType,
            logger=logger,
            defaultAutosubscribe=defaultAutosubscribe,
        )

    def close(self):
        BaseSubscriptionConsumer.close(self)
        BaseSubscriptionProducer.close(self)

    def _close(self):
        self.close()
