from aiohttp import web

routes = web.RouteTableDef()

from rtcbot import RTCConnection, getRTCBotJS

conn = RTCConnection()  # For this example, we use just one global connection


@conn.subscribe
def onMessage(msg):  # Called when messages received from browser
    print("Got message:", msg["data"])
    conn.put_nowait({"data": "pong"})


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
        text="""
    <html>
        <head>
            <title>RTCBot: Data Channel</title>
            <script src="/rtcbot.js"></script>
        </head>
        <body style="text-align: center;padding-top: 30px;">
            <h1>Click the Button</h1>
            <button type="button" id="mybutton">Click me!</button>
            <p>
            Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
            </p>
            <script>
                var conn = new rtcbot.RTCConnection();

                conn.subscribe(m => console.log("Received from python:", m));

                async function connect() {
                    let offer = await conn.getLocalDescription();

                    // POST the information to /connect
                    let response = await fetch("/connect", {
                        method: "POST",
                        cache: "no-cache",
                        body: JSON.stringify(offer)
                    });

                    await conn.setRemoteDescription(await response.json());

                    console.log("Ready!");
                }
                connect();


                var mybutton = document.querySelector("#mybutton");
                mybutton.onclick = function() {
                    conn.put_nowait({ data: "ping" });
                };
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
