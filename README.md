# RTCBot

[![PyPI](https://img.shields.io/pypi/v/rtcbot.svg?style=flat-square)](https://pypi.org/project/rtcbot/)
[![npm](https://img.shields.io/npm/v/rtcbot.svg?style=flat-square)](https://www.npmjs.com/package/rtcbot)
[![Documentation Status](https://readthedocs.org/projects/rtcbot/badge/?version=latest&style=flat-square)](https://rtcbot.readthedocs.io/en/latest/?badge=latest)
[![Join the chat at https://gitter.im/rtcbot/community](https://img.shields.io/gitter/room/dkumor/rtcbot.svg?style=flat-square)](https://gitter.im/rtcbot/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![CircleCI](https://circleci.com/gh/dkumor/rtcbot.svg?style=svg)](https://circleci.com/gh/dkumor/rtcbot)

RTCBot's purpose is to provide a set of simple modules that help in developing remote-controlled robots in Python, with a focus on the Raspberry Pi.

The documentation includes tutorials that guide in developing your robot, starting from a basic connection between a Raspberry Pi and Browser, and encompass
creating a video-streaming robot controlled entirely over a 4G mobile connection, all the way to a powerful system that offloads complex computation to a desktop PC in real-time.

All communication happens through [WebRTC](https://en.wikipedia.org/wiki/WebRTC),
using Python 3's asyncio and the wonderful [aiortc](https://github.com/jlaine/aiortc) library,
meaning that your robot can be controlled with low latency both from the browser and through Python,
even when it is not connected to your local network.

The library is explained piece by piece in [the documentation](https://rtcbot.readthedocs.io/en/latest/index.html).

### [See Documentation & Tutorials](https://rtcbot.readthedocs.io/en/latest/index.html)

## Example

This example uses RTCBot to live stream a webcam to the browser. For details, please look at [the tutorials](https://rtcbot.readthedocs.io/en/latest/examples/index.html).

Python code that streams video to the browser:

```python
from aiohttp import web
routes = web.RouteTableDef()

from rtcbot import RTCConnection, getRTCBotJS, CVCamera

camera = CVCamera()
# For this example, we use just one global connection
conn = RTCConnection()
conn.video.putSubscription(camera)

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
    with open("index.html", "r") as f:
        return web.Response(content_type="text/html", text=f.read())

async def cleanup(app):
    await conn.close()
    camera.close()

app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
```

Browser code (index.html) that displays the video stream:

```html
<html>
  <head>
    <title>RTCBot: Video</title>
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
```
