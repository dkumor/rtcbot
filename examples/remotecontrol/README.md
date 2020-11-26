# Keyboard & Xbox Controller

It is time to move towards the "bot" portion of RTCBot: robot control. With the previous tutorials, a robot's webcam can be streamed to
the browser. Now, it is time to send commands from the keyboard or Xbox controller to your robot. This will allow true remote control, with you watching a video feed on your computer, and controlling the robot with your keyboard, while the robot roams around your house.

Make sure to go through the previous tutorial before starting this one.

## Skeleton Code

Just like the previous tutorials, we start with the basic skeleton that just establishes a WebRTC connection between Python and the browser.

```python
from aiohttp import web
routes = web.RouteTableDef()

from rtcbot import RTCConnection, getRTCBotJS

conn = RTCConnection()

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
            <title>RTCBot: Skeleton</title>
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

async def cleanup(app=None):
    await conn.close()

app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
```

## Keyboard

We now add keyboard support. This is done with the `rtcbot.Keyboard` javascript class

```diff
 from aiohttp import web
 routes = web.RouteTableDef()

 from rtcbot import RTCConnection, getRTCBotJS

 conn = RTCConnection()

+@conn.subscribe
+def onMessage(m):
+    print("key press", m)


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
             <title>RTCBot: Skeleton</title>
             <script src="/rtcbot.js"></script>
         </head>
         <body style="text-align: center;padding-top: 30px;">
             <video autoplay playsinline controls></video> <audio autoplay></audio>
             <p>
             Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
             </p>
             <script>
                 var conn = new rtcbot.RTCConnection();
+                var kb = new rtcbot.Keyboard();

                 async function connect() {
                     let offer = await conn.getLocalDescription();

                     // POST the information to /connect
                     let response = await fetch("/connect", {
                         method: "POST",
                         cache: "no-cache",
                         body: JSON.stringify(offer)
                     });

                     await conn.setRemoteDescription(await response.json());

+                    kb.subscribe(conn.put_nowait);

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
 web.run_app(app)
```

This javascript code creates a `Keyboard` object in the browser, which internally uses the `onkeydown` and `onkeyup` events to
gather keyboard data. It then subscribes the `put_nowait` function of the connection to key events once the connection is set up.

Running the above code gives the following output in the Python console:

```
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
key press {'type': 'keydown', 'altKey': False, 'shiftKey': True, 'keyCode': 16, 'key': 'Shift'}
key press {'type': 'keydown', 'altKey': False, 'shiftKey': True, 'keyCode': 72, 'key': 'H'}
key press {'type': 'keyup', 'altKey': False, 'shiftKey': True, 'keyCode': 72, 'key': 'H'}
key press {'type': 'keyup', 'altKey': False, 'shiftKey': False, 'keyCode': 16, 'key': 'Shift'}
key press {'type': 'keydown', 'altKey': False, 'shiftKey': False, 'keyCode': 69, 'key': 'e'}
key press {'type': 'keyup', 'altKey': False, 'shiftKey': False, 'keyCode': 69, 'key': 'e'}
key press {'type': 'keydown', 'altKey': False, 'shiftKey': False, 'keyCode': 76, 'key': 'l'}
key press {'type': 'keyup', 'altKey': False, 'shiftKey': False, 'keyCode': 76, 'key': 'l'}
key press {'type': 'keydown', 'altKey': False, 'shiftKey': False, 'keyCode': 76, 'key': 'l'}
key press {'type': 'keyup', 'altKey': False, 'shiftKey': False, 'keyCode': 76, 'key': 'l'}
key press {'type': 'keydown', 'altKey': False, 'shiftKey': False, 'keyCode': 79, 'key': 'o'}
key press {'type': 'keyup', 'altKey': False, 'shiftKey': False, 'keyCode': 79, 'key': 'o'}
```

## Xbox Controller

The keyboard would work for controlling your robot in a pinch, but an xbox controller is more useful, since it has analog sticks and triggers.
Those will allow you fine-grained control of your robot's speed and movement.

Thankfully, RTCBot has you covered - you only need to replace a single line in the above Keyboard code to switch to an xbox controller:

```diff
-var kb = new rtcbot.Keyboard();
+var kb = new rtcbot.Gamepad();
```

Running this code gives the following Python output:

```
key press {'value': -0.2838831841945648, 'type': 'axis1'}
key press {'value': -0.009033478796482086, 'type': 'axis0'}
key press {'value': 0, 'type': 'axis1'}
key press {'value': 0.004119998775422573, 'type': 'axis3'}
key press {'value': 0.006103701889514923, 'type': 'axis3'}
key press {'value': -0.008697775192558765, 'type': 'axis0'}
key press {'value': 0, 'type': 'axis3'}
key press {'value': -0.009338663890957832, 'type': 'axis0'}
key press {'value': 0, 'type': 'axis0'}
key press {'value': True, 'type': 'btn0'}
key press {'value': False, 'type': 'btn0'}
key press {'value': 0.27201148867607117, 'type': 'axis2'}
key press {'value': 1, 'type': 'axis2'}
key press {'value': -1, 'type': 'axis2'}
key press {'value': -0.8708761930465698, 'type': 'axis2'}
key press {'value': -0.7945494055747986, 'type': 'axis2'}
```

The controller's buttons give boolean values, and the joysticks give float values between -1 and 1. By default, the controller is polled at 10Hz as not to overwhelm a Pi 3 with tons of data each time a joystick is moved.

## Remote Control

And now, we put everything together, with a video stream sent from Python, and controls sent back from the browser. This code directly
allows you to sit at your computer and remotely control a Pi placed in a different room. We combine the keyboard example above, with the video streaming example from the previous tutorial.

We use the WASD keys for movement, decoding the current controls in Python's onMessage:

```python
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
    print({
            "forward": keystates["w"] * 1 - keystates["s"] * 1,
            "leftright": keystates["d"] * 1 - keystates["a"] * 1,
        })
```

This code keeps track of which keys are currently pressed, and prints out the robot controls. Leftright is -1 on left, and 1 on right. Similarly, forward is 1 when w is pressed, and -1 when s is pressed:

```
{'forward': 1, 'leftright': -1}
{'forward': 0, 'leftright': -1}
{'forward': 0, 'leftright': 0}
{'forward': -1, 'leftright': 0}
{'forward': -1, 'leftright': 1}
{'forward': 0, 'leftright': 1}
{'forward': 0, 'leftright': 0}
{'forward': 1, 'leftright': 0}
{'forward': 1, 'leftright': -1}
{'forward': 0, 'leftright': -1}
{'forward': 0, 'leftright': 0}
```

With this, we have a fully functional remote control system! All that's left is connecting your robot's motors.

```python
# Full code for the above example

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
    print({
            "forward": keystates["w"] * 1 - keystates["s"] * 1,
            "leftright": keystates["d"] * 1 - keystates["a"] * 1,
        })

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
    """)

async def cleanup(app=None):
    await conn.close()

app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
```

## Summary

In this section, keyboard and gamepad control was introduced, culminating in a fully remote-controlled system where commands
were sent from browser, and a live video stream was sent to the browser.

This example can be directly extended to link to a robot's controls - you can link the control output with your robot's actuators and motors in just a few lines of code!

## Extra Notes

In the above examples, we used a simple event-based control scheme. For robustness, it is better to send the full state from the browser rather than the individual events. That is, rather than sending _just_ the keydown event, it is generally better to process
controls in javascript, and send the full state (ie: `{"forward":1,"leftright":0}`).
