from aiohttp import web
import asyncio
import logging

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

logging.basicConfig(level=logging.DEBUG)


routes = web.RouteTableDef()

from rtcbot import RTCConnection, getRTCBotJS


# For this example, we use just one global connection
conn = RTCConnection(loop=loop)


@conn.subscribe
def onMessage(msg):  # Called when each message is sent
    print("Got message:", msg)


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
                    conn.put_nowait("Button Clicked!");
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
web.run_app(app,loop=loop)
