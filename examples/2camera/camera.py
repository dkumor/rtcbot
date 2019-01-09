from aiohttp import web
from rtcbot import RTCConnection, CVCamera, Microphone

routes = web.RouteTableDef()
import logging

# logging.basicConfig(level=logging.DEBUG)


@routes.get("/")
async def index(request):
    with open("camera.html", "r") as f:
        return web.Response(content_type="text/html", text=f.read())


@routes.post("/setupRTC")
async def setupRTC(request):
    clientOffer = await request.json()
    conn = RTCConnection()

    conn.addAudio(mic)
    conn.addVideo(cam)

    response = await conn.getLocalDescription(clientOffer)
    return web.json_response(response)


cam = CVCamera()
mic = Microphone(blocksize=960)
routes.static("/rtcbot/", path="./rtcbot")
app = web.Application()
app.add_routes(routes)
web.run_app(app, port=8000)
