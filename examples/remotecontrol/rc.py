from aiohttp import web

routes = web.RouteTableDef()

from rtcbot import RTCConnection, CVCamera, getRTCBotJS

cam = CVCamera()

# For this example, we use just one global connection
conn = RTCConnection()
conn.video.putSubscription(cam)

keystates = {"w": False, "a": False, "s": False, "d": False}


@conn.subscribe
def onMessage(m):
    global keystates
    if m["keyCode"] == 87:  # W
        keystates["w"] = m["type"] == "keydown"
    elif m["keyCode"] == 83:  # S
        keystates["s"] = m["type"] == "keydown"
    elif m["keyCode"] == 65:  # A
        keystates["a"] = m["type"] == "keydown"
    elif m["keyCode"] == 68:  # D
        keystates["d"] = m["type"] == "keydown"
    print(
        {
            "forward": keystates["w"] * 1 - keystates["s"] * 1,
            "leftright": keystates["d"] * 1 - keystates["a"] * 1,
        }
    )


# Serve the RTCBot javascript library at /rtcbot.js
@routes.get("/rtcbot.js")
async def rtcbotjs(request):
    return web.Response(content_type="application/javascript", text=getRTCBotJS())


# This sets up the connection
@routes.post("/connect")
async def connect(request):
    clientOffer = await request.json()
    serverResponse = await conn.getLocalDescription(clientOffer)
    return web.json_response(serverResponse)


@routes.get("/")
async def index(request):
    return web.Response(
        content_type="text/html",
        text=r"""
    <html>
        <head>
            <title>RTCBot: Remote Control</title>
            <script src="/rtcbot.js"></script>
        </head>
        <body style="text-align: center;padding-top: 30px;">
            <video autoplay playsinline controls></video> <audio autoplay></audio>
            <p>
            Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
            </p>
            <script>
                var conn = new rtcbot.RTCConnection();
                conn.video.subscribe(function(stream) {
                    document.querySelector("video").srcObject = stream;
                });

                var kb = new rtcbot.Keyboard();

                async function connect() {
                    let offer = await conn.getLocalDescription();

                    // POST the information to /connect
                    let response = await fetch("/connect", {
                        method: "POST",
                        cache: "no-cache",
                        body: JSON.stringify(offer)
                    });

                    await conn.setRemoteDescription(await response.json());

                    kb.subscribe(conn.put_nowait);

                    console.log("Ready!");
                }
                connect();

            </script>
        </body>
    </html>
    """,
    )


async def cleanup(app=None):
    await conn.close()


app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
