# Multiple Connections & Reconnecting

Thus far, all of the tutorials included a single `RTCConnection` object for simplicity. While it makes the code easy to understand, it also means that refreshing the browser page, or connecting from another tab at the same time will not work, since each `RTCConnection` object can only be used once.

This tutorial will show how to set up your server to handle multiple connections.

## Video Streaming Template

We will build upon the video-streaming tutorial. The basic template code is copied over to this tutorial, with all references to the global `RTCConnection` removed:

```python
from aiohttp import web
routes = web.RouteTableDef()

from rtcbot import RTCConnection, getRTCBotJS, CVCamera
camera = CVCamera()

# This sets up the connection
@routes.post("/connect")
async def connect(request):
    clientOffer = await request.json()

    ## WHAT GOES HERE? ##

    return web.json_response(serverResponse)

async def cleanup(app=None):
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
            <video autoplay playsinline controls muted></video>
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
```

## The Connection Handler

Most of the template above is code to display the video box in a browser. We therefore focus only on the parts relevant to this tutorial:

```python
camera = CVCamera()

# This sets up the connection
@routes.post("/connect")
async def connect(request):
    clientOffer = await request.json()

    ## WHAT GOES HERE? ##

    return web.json_response(serverResponse)

async def cleanup(app=None):
    camera.close()
```

Remember that thus far, all tutorials used a single global connection:

```python
camera = CVCamera()

# For this example, we use just one global connection
conn = RTCConnection()
# Subscribe to the video feed
conn.video.putSubscription(camera)

# This sets up the connection
@routes.post("/connect")
async def connect(request):
    clientOffer = await request.json()
    # Set up the connection
    serverResponse = await conn.getLocalDescription(clientOffer)
    return web.json_response(serverResponse)

async def cleanup(app=None):
    await conn.close()
    camera.close()
```

This global connection can only be initialized once, so once the `connect` function is run, it will not work again. The solution is to create a new `RTCConnection` each time `connect` is called. We also need to keep track of the active connections, and subscriptions to video frames, since it is now possible for there to be multiple streams at once!

The most robust way to achieve this is to create a class wrapping the connection object, which handles preparation of the connection as well as cleanup. The code we will use is shown here:

```python
camera = CVCamera()

class ConnectionHandler:
    active_connections = [] # This array keeps track of all current connections

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
    conn = ConnectionHandler() # Our ConnectionHandler class!
    serverResponse = await conn.getLocalDescription(clientOffer)
    return web.json_response(serverResponse)

async def cleanup(app=None):
    await ConnectionHandler.cleanup() # When the app is closed, close all connections
    camera.close()
```

```eval_rst
.. warning::
    Each video stream is encoded separately, so a Raspberry Pi might struggle with multiple simultaneous connections.
```

When building a robot, you might want to allow only a single active connection at a time (which will control the bot!), which can be achieved by checking the number of active connections before creating a new `ConnectionHandler`.

The class-based approach allows easy extension. For example, to receive control messages from the browser, an `onMessage` function can be added:

```python
class ConnectionHandler:
    def __init__(self):
        # ...

        self.conn.subscribe(self.onMessage)

        # ---
    def onMessage(self,msg):
        print(msg)
```

## Summary

This tutorial showed how to allow multiple connections and reconnecting with RTCBot. If using RTCBot to build a robot, it is recommended that you use a similar approach, rather than a single global connection.
