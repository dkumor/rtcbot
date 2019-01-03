from aiohttp import web
from rtcbot import RTCConnection, CVCamera

routes = web.RouteTableDef()


@routes.get("/")
async def index(request):
    with open("camera.html", "r") as f:
        return web.Response(content_type="text/html", text=f.read())


@routes.post("/setupRTC")
async def setupRTC(request):
    clientOffer = await request.json()
    conn = RTCConnection()

    conn.addVideo(cam.subscribe())

    response = await conn.getLocalDescription(clientOffer)
    return web.json_response(response)


cam = CVCamera()
routes.static("/rtcbot/", path="./rtcbot")
app = web.Application()
app.add_routes(routes)
web.run_app(app, port=8000)
