import asyncio

import numpy as np
from functools import partial
import logging
from collections import deque


class EventSubscription:
    """
    This is a subscription that is fired once - upon the first insert.
    """

    def __init__(self):
        self.__evt = asyncio.Event()
        self.__value = None

    def put_nowait(self, value):
        self.__value = value
        self.__evt.set()

    async def get(self):
        await self.__evt
        return self.__value

    def __await__(self):
        return self.get().__await__()


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


class GetterSubscription:
    """
    You might have a function which behaves like a get(), but it is just a function.
    The GetterSubscription is a wrapper that calls your function on get()::

        @GetterSubscription
        async def myfunction():
            asyncio.sleep(1)
            return "hello!"

        await myfunction.get()
        # returns "hello!"
    """

    def __init__(self, callback):
        self._callback = callback

    async def get(self):
        return await self._callback()


class CallbackSubscription:
    """
    Sometimes you don't want to await anything, you just want to run a callback upon an event.
    The CallbackSubscription allows you to do precisely that::

        @CallbackSubscription
        async def mycallback(value):
            print(value)

        cam = CVCamera()
        cam.subscribe(mycallback)

    Note: 
        This is no longer necessary: you can just pass a function to `subscribe`, and it will automatically
        be wrapped in a `CallbackSubscription`.
    """

    def __init__(self, callback, loop=None, runDirect=False):
        self._callback = callback
        self._loop = loop
        self._runDirect = runDirect
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

    def put_nowait(self, element):
        # We don't want to stall the event loop at this moment - we call it soon enough.
        if self._runDirect:
            self._callback(element)
        else:
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
        conn.audio.putSubscription(s) # Big audio delay!

    Instead, what you want to do is delay subscribing until `get` is called the first time, which would
    wait until the connection is ready to start sending data::

        s = DelayedSubscription(Microphone())
        conn = RTCConnection()
        conn.audio.putSubscription(s) # Calls Microphone.subscribe() on first get()

    One caveat is that calling `unsubscribe` will not work on the DelayedSubscription - you must use
    unsubscribe as given in the DelayedSubscription! That means::

        m = Microphone()
        s = DelayedSubscription(m)
        m.unsubscribe(s) # ERROR!

        s.unsubscribe() # correct!

    Parameters
    ----------
    
        SubscriptionWriter: BaseSubscriptionWriter
            An object with a subscribe method
        subscription: (optional)
            The subscription to subscribe. If given, calls `SubscriptionWriter.subscribe(subscription)`
    
    """

    def __init__(self, SubscriptionWriter, subscription=None):
        self.SubscriptionWriter = SubscriptionWriter
        self.subscription = subscription
        self._wasInitialized = False

    def unsubscribe(self):
        if self.subscription is not None:
            self.SubscriptionWriter.unsubscribe(self.subscription)
        self._wasInitialized = True

    async def get(self):
        if not self._wasInitialized:
            self.subscription = self.SubscriptionWriter.subscribe(self.subscription)
            self._wasInitialized = True
        if self.subscription is None:
            raise AttributeError(
                "DelayedSubscription.subscription is None - this means that you did not pass a subscription object, and unsubscribed before one was created!"
            )
        return await self.subscription.get()


class RebatchSubscription:
    """
    In certain cases, data comes with a suboptimal batch size. For example,
    audio coming from an `RTCConnection` is always of shape `(2,960)`, with 2 channels,
    and 960 samples per batch. This subscription allows you to change the frame size
    by mixing and matching batches. For example::

        s = RebatchSubscription(samples=1024,axis=1)
        s.put_nowait(np.zeros((2,960)))

        # asyncio.TimeoutError - the RebatchSubscription does 
        # not have enough data to create a batch of size 1024
        rebatched = await asyncio.wait_for(s.get(),timeout=5)

        # After adding another batch of 960, get returns a frame of goal shape
        s.put_nowait(np.zeros((2,960)))
        rebatched = await s.get()
        print(rebatched.shape) # (2,1024)

    The RebatchSubscription takes samples from the second data frame's dimension 1
    to create a new batch of the correct size.
    """

    def __init__(self, samples, axis=0, subscription=None):
        assert samples > 0
        if subscription is None:
            subscription = asyncio.Queue()
        self.subscription = subscription
        self._sampleQueue = deque()
        self._samples = samples
        self._axis = axis
        self._partialBatch = None

        # https://stackoverflow.com/questions/12116830/numpy-slice-of-arbitrary-dimensions
        if self._axis > 0:
            self._idxa = tuple([slice(None)] * (self._axis) + [slice(0, self._samples)])
            self._idxb = tuple(
                [slice(None)] * (self._axis) + [slice(self._samples, None)]
            )
        elif self._axis == -1:
            self._idxa = (Ellipsis, slice(self._samples))
            self._idxb = (Ellipsis, slice(self._samples, None))
        else:
            self._idxa = slice(self._samples)
            self._idxb = slice(self._samples, None)

    def put_nowait(self, data):
        self.subscription.put_nowait(data)

    async def get(self):
        while len(self._sampleQueue) == 0:
            data = await self.subscription.get()

            if self._partialBatch is not None:
                data = np.concatenate((self._partialBatch, data), axis=self._axis)

            while data.shape[self._axis] >= self._samples:
                self._sampleQueue.append(data[self._idxa])
                data = data[self._idxb]

            if data.shape[self._axis] > 0:
                self._partialBatch = data
            else:
                self._partialBatch = None

        return self._sampleQueue.popleft()
