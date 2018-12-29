from aiohttp import web
from pirtcbot import RTCConnection
routes = web.RouteTableDef()

@routes.get("/")
async def index(request):
    with open("basic.html", "r") as f:
        return web.Response(content_type="text/html", text=f.read())

@routes.post("/setupRTC")
async def setupRTC(request):
    clientOffer = await request.json()
    conn = RTCConnection(**clientOffer)

    @conn.onMessage
    def onMsg(c,m):
        print("Message:",m, "from",c.label)
        c.send(m)
    response = await conn.getDescription()
    print(response)
    return web.json_response(response)

app = web.Application()
app.add_routes(routes)
web.run_app(app,port=8000)
