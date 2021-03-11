from aiohttp import web

routes = web.RouteTableDef()

from rtcbot import RTCConnection, getRTCBotJS, CVCamera

camera = CVCamera()


class ConnectionHandler:
    active_connections = []

    def __init__(self):
        self.conn = RTCConnection()

        # Subscribe to the video frames - each connection gets its own subscription
        global camera
        self.videoSubscription = camera.subscribe()
        self.conn.video.putSubscription(self.videoSubscription)

        # Perform cleanup when the connection is closed
        self.conn.onClose(self.close)

        # Add this connection to the list of active connections
        ConnectionHandler.active_connections.append(self)

    def close(self):
        # When done, unsubscribe from the video feed
        global camera
        camera.unsubscribe(self.videoSubscription)

        # Remove from list of active connections
        ConnectionHandler.active_connections.remove(self)

    async def getLocalDescription(self, clientOffer):
        # Pass the connection setup result
        return await self.conn.getLocalDescription(clientOffer)

    @staticmethod
    async def cleanup():
        # Close all active connections, making sure to use an array copy [:]
        # since closing removes the item from the array!
        for c in ConnectionHandler.active_connections[:]:
            await c.conn.close()


# This sets up the connection
@routes.post("/connect")
async def connect(request):
    clientOffer = await request.json()
    conn = ConnectionHandler()  # Our ConnectionHandler class!
    serverResponse = await conn.getLocalDescription(clientOffer)
    return web.json_response(serverResponse)


async def cleanup(app=None):
    await ConnectionHandler.cleanup()  # When the app is closed, close all connections
    camera.close()


# Serve the RTCBot javascript library at /rtcbot.js
@routes.get("/rtcbot.js")
async def rtcbotjs(request):
    return web.Response(content_type="application/javascript", text=getRTCBotJS())


# Serve the webpage!
@routes.get("/")
async def index(request):
    return web.Response(
        content_type="text/html",
        text="""
    <html>
        <head>
            <title>RTCBot: Video</title>
            <script src="/rtcbot.js"></script>
        </head>
        <body style="text-align: center;padding-top: 30px;">
            <video autoplay playsinline muted controls></video>
            <p>
            Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
            </p>
            <script>
                var conn = new rtcbot.RTCConnection();

                conn.video.subscribe(function(stream) {
                    document.querySelector("video").srcObject = stream;
                });

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

            </script>
        </body>
    </html>
    """,
    )


app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)