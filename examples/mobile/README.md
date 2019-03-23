# Connecting over 4G

Thus far, the tutorials have all had you connect directly to the robot, which meant that it had to be on your local wifi network. In this tutorial, we will finally decouple the server and the robot.

Rather than connecting to the robot, we will have two separate Python programs. The first is a server, which will be served at a known IP address. The second will be the robot, which connects to the server with a websocket, and waits for the information necessary to initialize a WebRTC connection directly to your browser.

```eval_rst
.. note::
    The server must be accessible from the internet. This might involve a bit of configuration in your router settings. You can also use a server hosted by a cloud company, such as a virtual machine on DigitalOcean.
```

In a previous tutorial, we developed a connection that streamed video to the browser. This tutorial will implement exactly the same functionality,
but with a robot on a remote connection.

The browser-side code will remain unchanged - all of the work here will be in Python.

## Server Code

Most of the server code is identical. The only difference is that we set up a listener at `/ws`, which will establish a websocket connection with the robot:

```python
ws = None # Websocket connection to the robot
@routes.get("/ws")
async def websocket(request):
    global ws
    ws = Websocket(request)
    print("Robot Connected")
    await ws  # Wait until the websocket closes
    print("Robot disconnected")
    return ws.ws
```

The above code sets up a global `ws` variable which will hold the active connection. We then use this websocket in the `/connect` handler. Instead of establishing a WebRTC connection ourselves, the server forwards the information directly to the robot using the websocket:

```python
# Called by the browser to set up a connection
@routes.post("/connect")
async def connect(request):
    global ws
    if ws is None:
        raise web.HTTPInternalServerError("There is no robot connected")
    clientOffer = await request.json()
    # Send the offer to the robot, and receive its response
    ws.put_nowait(clientOffer)
    robotResponse = await ws.get()
    return web.json_response(robotResponse)
```

This is all that is needed from the server - its function is simply to route the information necessary to
establish the connection directly between robot and browser. The full server code is here:

```python
from aiohttp import web
routes = web.RouteTableDef()

from rtcbot import Websocket, getRTCBotJS

ws = None # Websocket connection to the robot
@routes.get("/ws")
async def websocket(request):
    global ws
    ws = Websocket(request)
    print("Robot Connected")
    await ws  # Wait until the websocket closes
    print("Robot disconnected")
    return ws.ws

# Called by the browser to set up a connection
@routes.post("/connect")
async def connect(request):
    global ws
    if ws is None:
        raise web.HTTPInternalServerError("There is no robot connected")
    clientOffer = await request.json()
    # Send the offer to the robot, and receive its response
    ws.put_nowait(clientOffer)
    robotResponse = await ws.get()
    return web.json_response(robotResponse)

# Serve the RTCBot javascript library at /rtcbot.js
@routes.get("/rtcbot.js")
async def rtcbotjs(request):
    return web.Response(content_type="application/javascript", text=getRTCBotJS())

@routes.get("/")
async def index(request):
    return web.Response(
        content_type="text/html",
        text="""
    <html>
        <head>
            <title>RTCBot: Remote Video</title>
            <script src="/rtcbot.js"></script>
        </head>
        <body style="text-align: center;padding-top: 30px;">
            <video autoplay playsinline></video> <audio autoplay></audio>
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
    """)

async def cleanup(app):
    global ws
    if ws is not None:
        c = ws.close()
        if c is not None:
            await c

app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
```

## Remote Code

In this tutorial, we will just run both server and robot on the local machine. The same code will work over the internet simply by setting the right IP for the robot to connect to. The robot connects to the server with a websocket, and waits for the message that will allow it to initialize its WebRTC connection.

```python
import asyncio
from rtcbot import Websocket, RTCConnection, CVCamera

cam = CVCamera()
conn = RTCConnection()
conn.video.putSubscription(cam)

# Connect establishes a websocket connection to the server,
# and uses it to send and receive info to establish webRTC connection.
async def connect():
    ws = Websocket("http://localhost:8080/ws")
    remoteDescription = await ws.get()
    robotDescription = await conn.getLocalDescription(remoteDescription)
    ws.put_nowait(robotDescription)
    print("Started WebRTC")
    await ws.close()


asyncio.ensure_future(connect())
try:
    asyncio.get_event_loop().run_forever()
finally:
    cam.close()
    conn.close()
```

With these two pieces of code, you first start the server, then start the robot, and finally open `http://localhost:8080` in the browser to view a video stream coming directly from the robot, even if the robot has an unknown IP.

## Summary

This tutorial split up the server and robot code into distinct pieces. Also introduced was rtcbot's websocket wrapper, allowing you to easily establish a data-only connection.

## Extra Notes

Be aware that throughout these tutorials, all error handling and robustness was left out in the interest of
clarity of the fundamental program flow. In reality, you will probably want to make sure that the connection
did not have an error, and add the ability to connect and disconnect multiple times.
