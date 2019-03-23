import asyncio
import logging
import json

import aiohttp
from aiohttp import web

from .base import SubscriptionProducerConsumer, SubscriptionClosed


class Websocket(SubscriptionProducerConsumer):
    """
    Wraps an aiohttp websocket to have an API matching RTCBot
    """

    _log = logging.getLogger("rtcbot.Websocket")

    def __init__(self, url_or_request, json=True, loop=None):
        super().__init__(asyncio.Queue, asyncio.Queue, logger=self._log)
        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        self._json = json
        self._ws = None
        self._client = None

        asyncio.ensure_future(self._wsSender(url_or_request))

    async def _wsSender(self, url_or_request):
        if isinstance(url_or_request, str):
            # Connect to a remote websocket
            self._client = aiohttp.ClientSession(loop=self._loop)
            self._ws = await self._client.ws_connect(url_or_request)
        else:
            # Handle an incoming websocket as server software.
            self._ws = web.WebSocketResponse(autoclose=False)
            await self._ws.prepare(url_or_request)

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
                await self._ws.send_str(msg)
            except SubscriptionClosed:
                break
        self._log.debug("Stopping websocket sender")

    async def _wsReceiver(self):
        # Once this coroutine starts, fire the ready event
        self._setReady(True)

        async for msg in self._ws:
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
                self._setError(self._ws.exception())
                break
            if self._shouldClose:
                break
        self._log.debug("Stopping websocket receiver")
        await self._clientClose()

    async def _clientClose(self):
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
            if self._client is not None:
                await self._client.close()
        super().close()

        self._log.debug("Finished closing websocket")

    def close(self):
        if self._ws is not None:
            if self._loop.is_running():
                self._log.debug("Loop is running - close will return a future!")
                return asyncio.ensure_future(self._clientClose())
            else:
                self._loop.run_until_complete(self._clientClose())
        return None
