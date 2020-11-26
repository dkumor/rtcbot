from aiohttp import web

routes = web.RouteTableDef()

from rtcbot import RTCConnection, getRTCBotJS, CVDisplay, Speaker

display = CVDisplay()
speaker = Speaker()

# For this example, we use just one global connection
conn = RTCConnection()
display.putSubscription(conn.video.subscribe())
speaker.putSubscription(conn.audio.subscribe())


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
            <title>RTCBot: Browser Audio & Video</title>
            <script src="/rtcbot.js"></script>
        </head>
        <body style="text-align: center;padding-top: 30px;">
            <video autoplay playsinline controls></video> <audio autoplay></audio>
            <p>
            Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
            </p>
            <script>
                var conn = new rtcbot.RTCConnection();

                async function connect() {

                    let streams = await navigator.mediaDevices.getUserMedia({audio: true, video: true});
                    conn.video.putSubscription(streams.getVideoTracks()[0]);
                    conn.audio.putSubscription(streams.getAudioTracks()[0]);

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

            </script>
        </body>
    </html>
    """,
    )


async def cleanup(app=None):
    await conn.close()
    display.close()
    speaker.close()


conn.onClose(cleanup)

app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
