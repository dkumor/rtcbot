import asyncio

from functools import partial
import logging


class BaseSubscriptionHandler:
    def __init__(self, defaultSubscriptionClass, logger=None):
        self.__subscriptions = set()
        self.__defaultSubscriptionClass = defaultSubscriptionClass
        self.__defaultSubscription = None

        if logger is None:
            self.__shlog = logging.getLogger(self.__class__.__name__).getChild(
                "SubscriptionHandler"
            )
        else:
            self.__shlog = logger.getChild("SubscriptionHandler")

    def subscribe(self, subscription=None):
        """
        Subscribes to new data as it comes in. There can be multiple independent
        subscriptions active at the same time.
        """
        if subscription is None:
            subscription = self.__defaultSubscriptionClass()
            if subscription is None:
                raise Exception("No subscription given!")
        self.__shlog.debug("Added subscription %s", subscription)
        self.__subscriptions.add(subscription)
        return subscription

    def _put_nowait(self, element):
        for s in self.__subscriptions:
            self.__shlog.debug("Inserted Data")
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
                self.__shlog.debug("Removing default subscription")
                self.unsubscribe(self.__defaultSubscription)
                self.__defaultSubscription = None
            else:
                # Otherwise, do nothing
                self.__shlog.debug(
                    "Unsubscribe called, but no default subscription is active. Doing nothing."
                )
        else:
            self.__shlog.debug("Removing subscription %s", subscription)
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
            self.__shlog.debug(
                "Created default subscription %s", self.__defaultSubscription
            )

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


class DelayedSubscription:
    """
    In some instances, you want to subscribe to something, but don't actually want to start
    gathering the data until the data is needed.

    This is especially common in something like audio streaming: if you were to subscribe
    to an audio stream right now, and get() the data only after a certain time, then there would be a
    large audio delay, because by default the audio subscription queues data. 
    
    This is common in the audio of an RTCConnection, where `get` is called only
    once the connection is established::

        s = Microphone().subscribe()
        conn = RTCConnection()
        conn.addAudio(s) # Big audio delay!

    Instead, what you want to do is delay subscribing until `get` is called the first time, which would
    wait until the connection is ready to start sending data::

        s = DelayedSubscription(Microphone())
        conn = RTCConnection()
        conn.addAudio(s) # Calls Microphone.subscribe() on first get()

    One caveat is that calling `unsubscribe` will not work on the DelayedSubscription - you must use
    unsubscribe as given in the DelayedSubscription! That means::

        m = Microphone()
        s = DelayedSubscription(m)
        m.unsubscribe(s) # ERROR!

        s.unsubscribe() # correct!

    Parameters
    ----------
        subscriptionHandler: BaseSubscriptionHandler
            An object with a subscribe method
        subscription: (optional)
            The subscription to subscribe. If given, calls `subscriptionHandler.subscribe(subscription)`
    
    """

    def __init__(self, subscriptionHandler, subscription=None):
        self.subscriptionHandler = subscriptionHandler
        self.subscription = subscription
        self._wasInitialized = False

    def unsubscribe(self):
        if self.subscription is not None:
            self.subscriptionHandler.unsubscribe(self.subscription)
        self._wasInitialized = True

    async def get(self):
        if not self._wasInitialized:
            self.subscription = self.subscriptionHandler.subscribe(self.subscription)
            self._wasInitialized = True
        if self.subscription is None:
            raise AttributeError(
                "DelayedSubscription.subscription is None - this means that you did not pass a subscription object, and unsubscribed before one was created!"
            )
        await self.subscription.get()
