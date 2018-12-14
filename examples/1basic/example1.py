import asyncio
from aiohttp import web
import pirtcbot

from aiortc import RTCPeerConnection, RTCSessionDescription

routes = web.RouteTableDef()
dchannel = None


def on_message(m):
    print("Got message", m)
    dchannel.send(m)


def on_datachannel(channel):
    global dchannel
    dchannel = channel
    print("Got data channel")
    channel.on("message", on_message)


@routes.get("/")
async def index(request):
    with open("example1.html", "r") as f:
        return web.Response(content_type="text/html", text=f.read())


@routes.post("/setupRTC")
async def setupRTC(request):

    # Set up the connection
    pc = RTCPeerConnection()
    pc.on("datachannel", on_datachannel)

    clientOffer = await request.json()
    offer = RTCSessionDescription(**clientOffer)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )


app = web.Application()
app.add_routes(routes)
web.run_app(app)
