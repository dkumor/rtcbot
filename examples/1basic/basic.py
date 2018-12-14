from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

routes = web.RouteTableDef()


@routes.get("/")
async def index(request):
    with open("basic.html", "r") as f:
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


mychannel = None


def on_datachannel(channel):
    global mychannel
    mychannel = channel
    print("Got data channel")
    mychannel.on("message", on_message)


def on_message(m):
    print("Got message", m)
    mychannel.send(m)  # Send it back


app = web.Application()
app.add_routes(routes)
web.run_app(app)
