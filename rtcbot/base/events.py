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

        self.__readyEvent = asyncio.Event()
        self.__error = None
        self.__logger = logger

    @property
    def ready(self):
        """
        This is `True` when the class has been fully initialized. You usually don't need to use this,
        since :func:`put_nowait` and func:`putSubscription` will work even if the class is still starting up in the background.
        """
        return self.__readyEvent.is_set()

    @property
    def error(self):
        return self.__error

    def _setReady(self, value):
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
        self.__logger.debug("Adding onReady subscription")
        if subscription is None:
            # the baseReadySubscription is a special case
            subscription = baseReadySubscription(self.__readyEvent)
        else:
            self.__onReady.add(subscription)
        return subscription

    def onError(self, subscription=None):
        self.__logger.debug("Adding onError subscription")
        if subscription is None:
            # we can just use an EventSubscription
            subscription = EventSubscription()
        self.__onError.add(subscription)
        return subscription


class threadedEventHandler(baseEventHandler):
    def __init__(self, logger, loop=None):
        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        super().__init__(logger)

    def _setError(self, err):
        self._loop.call_soon_threadsafe(super()._setError, err)

    def _setReady(self, value):
        self._loop.call_soon_threadsafe(super()._setReady, value)
