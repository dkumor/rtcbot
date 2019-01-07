import asyncio

from functools import partial


class BaseSubscriptionHandler:
    def __init__(self, defaultSubscriptionClass):
        self.__subscriptions = set()
        self.__defaultSubscriptionType = defaultSubscriptionClass
        self.__defaultSubscription = None

    def subscribe(self, subscription=None):
        """
        Subscribes to new data as it comes in. There can be multiple independent
        subscriptions active at the same time.
        """
        if subscription is None:
            subscription = self.__defaultSubscriptionClass()
            if subscription is None:
                raise Exception("No subscription given!")
        self.__subscriptions.add(subscription)
        return subscription

    def _put_nowait(self, element):
        for s in self.__subscriptions:
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
                self.unsubscribe(self.__defaultSubscription)
                self.__defaultSubscription = None
            # Otherwise, do nothing
        else:
            self.__subscriptions.remove(subscription)

    def unsubscribeAll(self):
        """
        Removes all currently active subscriptions, including the default one if it was intialized.
        """
        self.__subscriptions = set()
        self.__defaultSubscription = None

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
        if self.__defaultSubscription is None:
            self.__defaultSubscription = self.subscribe()

        return await self.__defaultSubscription.get()


class SubscriptionHandler(BaseSubscriptionHandler):
    def put_nowait(self, element):
        self._put_nowait(element)


class MostRecentSubscription:
    """
    The MostRecentSubscription always returns the most recently added element.
    If you get an element and immediately call get again, it will wait until the next element is received,
    it will not return elements that were already processed.

    It is not threadsafe.
    """

    def __init__(self):
        self._putEvent = asyncio.Event()
        self._element = None

    def put_nowait(self, element):
        """
        Adds the given element to the subscription.
        """
        self._element = element
        self._putEvent.set()

    async def get(self):
        """
        Gets the most recently added element
        """
        # Wait for the event marking a new element received
        await self._putEvent.wait()

        # Reset the event so we can wait for the next element
        self._putEvent.clear()

        return self._element


class CallbackSubscription:
    """
    Sometimes you don't want to await anything, you just want to run a callback upon an event.
    The CallbackSubscription allows you to do precisely that::

        @CallbackSubscription
        async def mycallback(value):
            print(value)

        cam = CVCamera()
        cam.subscribe(mycallback)


    """

    def __init__(self, callback, loop=None):
        self._callback = callback
        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

    def put_nowait(self, element):
        # We don't want to stall the event loop at this moment - we call it soon enough.
        self._loop.call_soon(partial(self._callback, element))

