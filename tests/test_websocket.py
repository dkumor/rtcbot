from aiohttp import web
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

from rtcbot import Websocket


async def wsping(request):
    ws = Websocket(request)
    print("Got websocket")
    await ws.onReady()
    print("WS READY")
    while ws.ready:
        print("MSG")
        ws.put_nowait(await ws.get())
    print("DONE")
    return


def create_ws_server(loop):
    app = web.Application(loop=loop)
    app.router.add_route("GET", "/", wsping)
    return app


async def test_websocket(aiohttp_client, aiohttp_unused_port):
    port = aiohttp_unused_port()
    client = await aiohttp_client(create_ws_server, server_kwargs={"port": port})
    ws = Websocket("http://localhost:{}/".format(port))
    ws.put_nowait("Hello")
    assert await ws.get() == "Hello"
    ws.put_nowait({"foo": "bar"})
    resp = await ws.get()
    assert "foo" in resp
    assert resp["foo"] == "bar"
    s = ws.onClose()
    await ws.close()
    await s
    await asyncio.sleep(0.1)

