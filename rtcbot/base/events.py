import inspect
import asyncio

from rtcbot.subscriptions import EventSubscription


class baseReadySubscription:
    # This subscription is special: it doesn't return anything. It just... fires
    def __init__(self, evt):
        self.__evt = evt

    async def get(
        self
    ):  # We want the get to be there for consistency with the rest of the API
        await self.__evt.wait()

    def __await__(self):
        return self.get().__await__()


class baseEventHandler:
    """
    This class handles base events
    """

    def __init__(self, logger):
        self.__onError = set()
        self.__onReady = set()
        self.__onClose = set()

        self.__readyEvent = asyncio.Event()
        self.__closeEvent = asyncio.Event()
        self.__error = None
        self.__logger = logger

    @property
    def ready(self):
        """
        This is `True` when the class has been fully initialized, and is ready to process data::

            if not myobject.ready:
                print("Not ready to process data")
        
        This property is offered for convenience, but if you want to be notifed when ready to process data, you will want to use the :func:`onReady`
        function, which will allow you to set up a callback/coroutine to wait until initialized.
        
        note:
            You usually don't need to check the `ready` state, since all functions for getting/putting data will work even if the class is still starting up in the background.
        """
        return self.__readyEvent.is_set()

    @property
    def error(self):
        """
        If there is an error that causes the underlying process to crash, this property will hold the actual :class:`Exception`
        that was thrown::

            if myobject.error is not None:
                print("Oh no! There was an error:",myobject.error)

        This property is offered for convenience, but usually, you will want to subscribe to the error by using :func:`onError`,
        which will notify your app when the issue happens.

        note:
            If the error is not `None`, the object is considered crashed, and no longer processing data.
        """
        return self.__error

    @property
    def closed(self):
        """
        Returns whether the object was closed. This includes both thrown exceptions, and clean exits.
        """
        return self.__closeEvent.is_set()

    def _setReady(self, value=True):
        """
        Sets the ready to `true`, and fires all subscriptions created with :func:`onReady`.
        Call this when your producer/consumer is fully initialized.

        Warning:
            Only call this if you are subclassing :class:`baseEventHandler`.
        """
        self.__logger.debug("Setting ready to %s", value)
        if value:
            self.__readyEvent.set()
            for subscription in self.__onReady:
                if callable(getattr(subscription, "put_nowait", None)):
                    subscription.put_nowait(None)
                elif inspect.iscoroutinefunction(subscription):
                    asyncio.ensure_future(subscription())
                else:
                    subscription()
        else:
            self.__readyEvent.clear()

    def _setError(self, value):
        """
        Sets the error state of the class to an error that was caught while processing data.
        
        After the error is set, the class is assumed to be in a closed state,
        meaning that any background processes either crashed or were shut down.

        Warning:
            Only call this if you are subclassing :class:`baseEventHandler`.
        """
        self.__logger.debug("Setting error to %s", value)
        if value is not None:
            self.__error = value
            for subscription in self.__onError:
                if callable(getattr(subscription, "put_nowait", None)):
                    subscription.put_nowait(value)
                elif inspect.iscoroutinefunction(subscription):
                    asyncio.ensure_future(subscription(value))
                else:
                    subscription(value)

    def onReady(self, subscription=None):
        """
        Creating the class does not mean that the object is ready to process data.
        When created, the object starts an initialization procedure in the background,
        and once this procedure is complete, and any spawned background workers
        are ready to process data, it fires a `ready` event.

        This function allows you to listen for this event::

            @myobj.onReady
            def readyCallback():
                print("Ready!)
        
        The function works in exactly the same way as a :func:`subscribe`, meaning that you can
        pass it a coroutine, or even await it directly::

            await myobj.onReady()

        note:
            The object will automatically handle any subscriptions or inserts that happen while it is initializing,
            so you generally don't need to worry about the ready event, unless you need exact control.
        """
        self.__logger.debug("Adding onReady subscription")
        if subscription is None:
            # the baseReadySubscription is a special case
            subscription = baseReadySubscription(self.__readyEvent)
        else:
            self.__onReady.add(subscription)
        return subscription

    def onError(self, subscription=None):
        """
        Since most data processing happens in the background, the object might encounter an error, and the data processing might
        crash. If there is a crash, the object is considered dead, and no longer gathering data.

        To catch these errors, when an unhandled exception happens, the `error` event is fired, with the associated :class:`Exception`.
        This function allows you to subscribe to these events::

            @myobj.onError
            def error_happened(err):
                print("Crap, stuff just crashed: ",err)

        The :func:`onError` function behaves in the same way as a :func:`subscribe`, which means that you can pass it a coroutine, or even
        directly await it::

            err = await myobj.onError()

        """
        self.__logger.debug("Adding onError subscription")
        if subscription is None:
            # we can just use an EventSubscription
            subscription = EventSubscription()
        self.__onError.add(subscription)
        return subscription

    def onClose(self, subscription=None):
        """
        This is mainly useful for connections - they can be closed remotely. This allows 
        handling the close event. ::

            @myobj.onClose
            def closeCallback():
                print("Closed!)
        
        Be aware that this is equivalent to explicitly awaiting the object::

            await myobj

        """
        self.__logger.debug("Adding onClose subscription")
        if subscription is None:
            # the baseReadySubscription is a special case
            subscription = baseReadySubscription(self.__closeEvent)
        else:
            self.__onClose.add(subscription)
        return subscription

    def __await__(self):
        return self.onClose().__await__()

    def close(self):
        """
        Fires the onClose event
        """
        if not self.__closeEvent.is_set():
            self.__logger.debug("Firing onClose")
            self.__closeEvent.set()
            for subscription in self.__onClose:
                if callable(getattr(subscription, "put_nowait", None)):
                    subscription.put_nowait(None)
                elif inspect.iscoroutinefunction(subscription):
                    asyncio.ensure_future(subscription())
                else:
                    subscription()


class threadedEventHandler(baseEventHandler):
    """
    A threadsafe version of :class:`baseEventHandler`.
    """

    def __init__(self, logger, loop=None):
        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        super().__init__(logger)

    def _setError(self, err):
        """
        Threadsafe version of :func:`baseEventHandler._setError`.
        """
        self._loop.call_soon_threadsafe(super()._setError, err)

    def _setReady(self, value):
        """
        Threadsafe version of :func:`baseEventHandler._setReady`.
        """
        self._loop.call_soon_threadsafe(super()._setReady, value)
