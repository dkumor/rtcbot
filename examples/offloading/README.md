# Offloading Computation

Most hobbyists can't afford to do complex computations on their robot, because the little single-board computers (SBCs) available for a reasonable price do not have sufficient processing power for advanced functionality. While this is slowly changing with things like [Nvidia's Jetson Nano](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-nano/), there is still a large gap in power between SBCs
and an average desktop.

The ideal situation would be if you could strap an entire desktop to your robot. With RTCBot, we can do the next best thing: we can stream the robot's inputs to a desktop, which can then perform computation, and send back commands.

In this tutorial, we will go back to a single file for both server and robot for simplicitly. We set up a connection to the robot from Python, allowing you to control the robot with an xbox controller without a browser.

```eval_rst
.. note::
    While with a Raspberry Pi there might be a non-negligible delay between sending a video frame and getting back a command, this is not a limitation of the approach, since it is possible to stream `video games with barely-noticeable lag <https://arstechnica.com/gaming/2019/03/googles-multiyear-quest-to-overcome-ids-stadia-streaming-skepticism/>`_. In particular, rtcbot currently cannot take advantage of the Pi's hardware acceleration, meaning that all video encoding is done in software, which ends up adding to video delay.
```

## Python to Python Streaming

To start offloading, we get rid of the browser - we will create a connection from Python on your desktop
to Python on your robot, stream video from the robot, and stream controls from the desktop.

The robot code is identical to the code we have seen in previous tutorials. All we did was remove the browser code, since it is not needed.

```python
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

async def cleanup(app):
    await conn.close()
    cam.close()

app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
```

Then, on the desktop, we run the following:

```python
# desktop.py

import asyncio
import aiohttp
import cv2
import json
from rtcbot import RTCConnection, Gamepad, CVDisplay

disp = CVDisplay()
g = Gamepad()
conn = RTCConnection()

@conn.video.subscribe
def onFrame(frame):
    # Show a 4x larger image so that it is easy to see
    resized = cv2.resize(frame, (frame.shape[1] * 4, frame.shape[0] * 4))
    disp.put_nowait(resized)

async def connect():
    localDescription = await conn.getLocalDescription()
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8080/connect", data=json.dumps(localDescription)
        ) as resp:
            response = await resp.json()
            await conn.setRemoteDescription(response)
    # Start sending gamepad controls
    g.subscribe(conn)

asyncio.ensure_future(connect())
try:
    asyncio.get_event_loop().run_forever()
finally:
    conn.close()
    disp.close()
    g.close()
```

This code manually sends the connect request, and establishes a webrtc connection with the response.
Also introduced was the Python version of `Gamepad`. The browser version was used in a previous tutorial.

The robot code's output is now:

```
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
Control message: {'timestamp': 1553379212.684861, 'code': 'BTN_SOUTH', 'state': 1, 'event': 'Key'}
Control message: {'timestamp': 1553379212.684861, 'code': 'ABS_Y', 'state': -1, 'event': 'Absolute'}
Control message: {'timestamp': 1553379213.192862, 'code': 'BTN_SOUTH', 'state': 0, 'event': 'Key'}
Control message: {'timestamp': 1553379214.14487, 'code': 'BTN_SOUTH', 'state': 1, 'event': 'Key'}
Control message: {'timestamp': 1553379214.964878, 'code': 'BTN_SOUTH', 'state': 0, 'event': 'Key'}
Control message: {'timestamp': 1553379216.172882, 'code': 'BTN_SOUTH', 'state': 1, 'event': 'Key'}
Control message: {'timestamp': 1553379216.48489, 'code': 'BTN_SOUTH', 'state': 0, 'event': 'Key'}
Control message: {'timestamp': 1553379216.872889, 'code': 'ABS_X', 'state': -11, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.884891, 'code': 'ABS_X', 'state': -64, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.892888, 'code': 'ABS_X', 'state': -95, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.904886, 'code': 'ABS_X', 'state': -158, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.912884, 'code': 'ABS_X', 'state': -599, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.924894, 'code': 'ABS_X', 'state': -1240, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.932888, 'code': 'ABS_X', 'state': -1586, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.944887, 'code': 'ABS_X', 'state': -2080, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.952887, 'code': 'ABS_X', 'state': -2689, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.964892, 'code': 'ABS_X', 'state': -3833, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.972892, 'code': 'ABS_X', 'state': -4957, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.972892, 'code': 'ABS_Y', 'state': -53, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.984889, 'code': 'ABS_X', 'state': -7944, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.984889, 'code': 'ABS_Y', 'state': -106, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.992891, 'code': 'ABS_X', 'state': -10170, 'event': 'Absolute'}
Control message: {'timestamp': 1553379216.992891, 'code': 'ABS_Y', 'state': -137, 'event': 'Absolute'}
Control message: {'timestamp': 1553379217.004892, 'code': 'ABS_X', 'state': -12567, 'event': 'Absolute'}
```

```eval_rst
.. warning::
   The output for the `Gamepad` object is currently different in Javascript and in Python. Make sure you don't mix them up!
```
