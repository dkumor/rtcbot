# robot.py

from aiohttp import web

routes = web.RouteTableDef()

from rtcbot import RTCConnection, CVCamera

cam = CVCamera()
conn = RTCConnection()
conn.video.putSubscription(cam)


@conn.subscribe
def controls(msg):
    print("Control message:", msg)


@routes.post("/connect")
async def connect(request):
    clientOffer = await request.json()
    serverResponse = await conn.getLocalDescription(clientOffer)
    return web.json_response(serverResponse)


async def cleanup(app=None):
    await conn.close()
    cam.close()


app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
