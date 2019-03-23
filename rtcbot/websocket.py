import asyncio
import logging
import json

import aiohttp
from aiohttp import web

from .base import SubscriptionProducerConsumer, SubscriptionClosed


class Websocket(SubscriptionProducerConsumer):
    """
    Wraps an aiohttp websocket to have an API matching RTCBot. The websocket 
    can be given either a URL to connect to::

        ws = Websocket("http://localhost:8080/ws")
        msg = await ws.get()

    It can also be used in a server context to complete the connection::

        @routes.get("/ws")
        async def websocketHandler(request):
            ws = Websocket(request)
            msg = await ws.get()

    Naturally, just like all other parts of rtcbot, you can also `subscribe` and `putSubscription`
    instead of manually calling `get` and `put_nowait`.
    """

    _log = logging.getLogger("rtcbot.Websocket")

    def __init__(self, url_or_request, json=True, loop=None):
        super().__init__(asyncio.Queue, asyncio.Queue, logger=self._log)
        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        self._json = json
        self.ws = None
        self._client = None

        asyncio.ensure_future(self._wsSender(url_or_request))

    async def _wsSender(self, url_or_request):
        if isinstance(url_or_request, str):
            # Connect to a remote websocket
            self._client = aiohttp.ClientSession(loop=self._loop)
            self.ws = await self._client.ws_connect(url_or_request)
        else:
            # Handle an incoming websocket as server software.
            self.ws = web.WebSocketResponse(autoclose=False)
            await self.ws.prepare(url_or_request)

        self._log.debug("Connection established")
        # Create a separate coroutine for sending messages
        asyncio.ensure_future(self._wsReceiver())

        # And send out messages
        while not self._shouldClose:
            try:
                msg = await self._get()
                if self._json:
                    msg = json.dumps(msg)
                self._log.debug("Sending message %s", msg)
                await self.ws.send_str(msg)
            except SubscriptionClosed:
                break
        self._log.debug("Stopping websocket sender")

    async def _wsReceiver(self):
        # Once this coroutine starts, fire the ready event
        self._setReady(True)

        async for msg in self.ws:
            self._log.debug(msg)
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = msg.data
                self._log.debug("Received '%s'", data)
                if self._json:
                    try:
                        data = json.loads(data)
                    except:
                        self._log.debug("Failed to read json data %s", data)
                try:
                    self._put_nowait(data)
                except:
                    self._log.exception("Error in message handler")

            elif msg.type == aiohttp.WSMsgType.ERROR:
                self._setError(self.ws.exception())
                break
            if self._shouldClose:
                break
        self._log.debug("Stopping websocket receiver")
        await self._clientClose()

    async def _clientClose(self):
        if self.ws is not None and not self.ws.closed:
            await self.ws.close()
        if self._client is not None and not self._client.closed:
            await self._client.close()
        super().close()

        self._log.debug("Finished closing websocket")

    def close(self):
        if self.ws is not None:
            if self._loop.is_running():
                self._log.debug("Loop is running - close will return a future!")
                return asyncio.ensure_future(self._clientClose())
            else:
                self._loop.run_until_complete(self._clientClose())
        return None
