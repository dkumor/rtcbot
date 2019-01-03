import asyncio

from functools import partial


class BaseSubscriptionHandler:
    def __init__(self, defaultSubscription=None):
        self.__subscriptions = set()
        self.__defaultSubscription = defaultSubscription

    def subscribe(self, subscription=None):
        if subscription is None:
            subscription = self.__defaultSubscription
            if subscription is None:
                raise Exception("No subscription given!")
        self.__subscriptions.add(subscription)
        return subscription

    def _put_nowait(self, element):
        for s in self.__subscriptions:
            s.put_nowait(element)

    def unsubscribe(self, subscription):
        """
        Removes the given subscription, so that it no longer gets updated::
            subs = o.subscribe()
            o.unsubscribe(subs)
        """
        self.__subscriptions.remove(subscription)


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

