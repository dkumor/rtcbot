# Streaming Video

In the previous tutorial, a data connection was created between your python program and a browser, allowing to send messages back and forth. This tutorial will build upon the previous one's code, culminating in a 2-way video and audio connection,
where the Python code displays the video stream it gets from your browser, and the browser displays the video stream from the server.

You should use a browser on your laptop or desktop for this one, and put the server on a Raspberry Pi if you want to try streaming from the PiCamera.

## Skeleton Code

If you have not done so yet, you should look at the previous tutorial, where the basics of an `RTCConnection` are explained. For the skeleton of this part, the button from the previous
tutorial was removed, and replaced with a video element. Also removed was all code involving messages, to keep this tutorial focused entirely on video.

```python
from aiohttp import web
routes = web.RouteTableDef()

from rtcbot import RTCConnection, getRTCBotJS

# For this example, we use just one global connection
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
            <video autoplay playsinline muted controls></video>
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

This code establishes a WebRTC connection, and nothing else. It can be seen as a minimal example for RTCBot.

## Streaming Video from Python

The first thing we'll do is send a video stream from a webcam to the browser. If on a desktop or laptop, you should use `CVCamera`, and if on a Raspberry Pi with the camera module, use `PiCamera` instead - they get their video differently, but behave identically.

All you need is to add a couple lines of code to the skeleton to get a fully-functional video stream:

```diff
 from aiohttp import web
 routes = web.RouteTableDef()

-from rtcbot import RTCConnection, getRTCBotJS
+from rtcbot import RTCConnection, getRTCBotJS, CVCamera

+# Initialize the camera
+camera = CVCamera()

 # For this example, we use just one global connection
 conn = RTCConnection()

+# Send images from the camera through the connection
+conn.video.putSubscription(camera)

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
             <video autoplay playsinline muted controls></video>
             <p>
             Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
             </p>
             <script>
                 var conn = new rtcbot.RTCConnection();

+                // When the video stream comes in, display it in the video element
+                conn.video.subscribe(function(stream) {
+                    document.querySelector("video").srcObject = stream;
+                });

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
+    camera.close() # Singletons like a camera are not awaited on close

 app = web.Application()
 app.add_routes(routes)
 app.on_shutdown.append(cleanup)
 web.run_app(app)
```

One major difference between javascript and Python, is that the audio/video `subscribe` in javascript is only called once, and returns a
video stream object. In Python, the same function would get called on each video frame.

Also, remember to subscribe/put all subscriptions into `conn` _before_ initializing the connection with `getLocalDescription`. This is because `getLocalDescription` uses knowledge of which types of streams you want to send and receive to construct its offer and response.

```eval_rst
.. note::
    In some cases you will need to click play in the browser before the video starts.
```

## Adding Audio

```eval_rst
.. warning::
    Be aware that a Pi 3 with USB microphone might struggle a bit sending both audio and video at the same time. Try the code on your desktop/laptop or a Pi 4 first to make sure it works before attempting use with the Pi 3.
```

Based on what you know of RTCBot so far, and knowing that you can use a microphone with the `Microphone` class, do you think you can figure out audio just looking at the video code above?

The modifications to add audio use exactly the same ideas:

```python
from rtcbot import RTCConnection, getRTCBotJS, CVCamera, Microphone

camera = CVCamera()
mic = Microphone()

conn = RTCConnection()
conn.video.putSubscription(camera)
conn.audio.putSubscription(mic)
```

Also, don't forget to close the microphone at the end with `mic.close()`!

On the browser side, we add an `<audio autoplay></audio>` element right after the `<video>` element, and update the javascript:

```javascript
var conn = new RTCConnection();

conn.video.subscribe(function (stream) {
  document.querySelector("video").srcObject = stream;
});
conn.audio.subscribe(function (stream) {
  document.querySelector("audio").srcObject = stream;
});
```

## Browser to Python

Thus far, we used Python to stream video and audio to the browser, which is the main use case in a robot. However, RTCBot can handle streaming both ways. Since it is assumed that you are at a single computer, we can't stream from Python and the browser at the same time (both will try to use the same webcam). We will switch the stream directions instead.

This bears repeating, so let's reiterate a bit of the basics of RTCBot's python API:

- Anything that outputs data has a `subscribe` method
- Anything that takes in data has a `putSubscription` method, which takes in a subscription: `putSubscription(x.subscribe())`
- An RTCConnection `conn` has _both_ outputs and inputs for messages sent through the connection. Furthermore, it also has video and audio streams `conn.video` and `conn.audio`, which _also_ can be used as both inputs and outputs.

With this in mind, reversing the stream direction is a simple matter:

```python
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
    """)

async def cleanup(app=None):
    await conn.close()
    display.close()
    speaker.close()

app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
```

In the above code, instead of `CVCamera` and `Microphone`, `CVDisplay` and `Speaker` are used. In the javascript, we moved
the subscribing code to the `connect` function, because `getUserMedia` is an asynchronous function, and cannot be `await`ed outside an async function (like connect).

## Summary

This tutorial introduced video and audio streaming over WebRTC. Everything here relied on the `RTCConnection` object `conn`, which
can be initialized both from browser and Python.

1. `conn.video` is both a data producer and a consumer, allowing both to subscribe to remote video and send video streams
2. `conn.audio` behaves in exactly the same way as `conn.video`

Put together with messages that can be sent directly using `conn` (see previous tutorial), this allows you to send data back and forth however you like.

## Extra Notes

While the `RTCConnection` was created globally here, but should generally be created for each connection, the camera/microphone/speaker/display objects should be used as singletons, initialized once at the beginning of the program, and closed when the program is exiting.
