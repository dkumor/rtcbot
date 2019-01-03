# Streaming a Camera

In the previous tutorial, a basic skeleton project was set up, which created a data connection between the server and a browser.
This tutorial will start with the previous one's code, and end up with a 2-way video and audio connection, where the server displays the video stream it gets from your browser, and the browser
displays the video from the server.

You should use a browser on your laptop or desktop for this one, and put the server on a Raspberry Pi if you want to try streaming from the PiCamera.

## Skeleton Code

If you have not done so yet, you should look at the previous tutorial, where the basics of an `RTCConnection` are explained. For the skeleton of this part, we removed the button from the previous
tutorial, and replaced it with a video element. We also removed all code involving messages, to keep the tutorial focused entirely on video.

### camera.html

```html
<html>
  <head>
    <meta charset="UTF-8" />
    <title>RTCBot: Camera Streaming</title>
    <script src="rtcbot/rtcbot.js"></script>
  </head>
  <body style="text-align: center;padding-top: 30px;">
    <video autoplay playsinline></video>
    <p>
      Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
    </p>
    <script>
      // The connection object
      var conn = new RTCConnection();

      // Here we set up the connection. We put it in an async function, since we will be
      // waiting for results from the server (Promises).
      async function setupRTC() {
        console.log("Setting up a real-time connection to the server");

        // Get the information needed to connect from the server to the browser
        let offer = await conn.getLocalDescription();

        // POST the information to the server, which will respond with the corresponding remote
        // connection's description
        let response = await fetch("/setupRTC", {
          method: "POST",
          cache: "no-cache",
          body: JSON.stringify(offer)
        });

        // Set the remote server's information
        await conn.setRemoteDescription(await response.json());

        console.log("Setup Finished");
      }

      setupRTC(); // Run the async function in the background.
    </script>
  </body>
</html>
```

### camera.py

```python
from aiohttp import web
from rtcbot import RTCConnection

routes = web.RouteTableDef()

@routes.get("/")
async def index(request):
    with open("camera.html", "r") as f:
        return web.Response(content_type="text/html", text=f.read())

@routes.post("/setupRTC")
async def setupRTC(request):
    clientOffer = await request.json()
    conn = RTCConnection()
    response = await conn.getLocalDescription(clientOffer)
    return web.json_response(response)

routes.static("/rtcbot/", path="./rtcbot")
app = web.Application()
app.add_routes(routes)
web.run_app(app, port=8000)
```

## Streaming Video from Python

Sending video from Python is a trivial 2 line modification to both files.

In the Python file, we use `CVCamera` to use a camera available to OpenCV, and we subscribe the connection to the frames from the camera:

```diff
 from aiohttp import web
-from rtcbot import RTCConnection
+from rtcbot import RTCConnection, CVCamera

 routes = web.RouteTableDef()

 @routes.get("/")
 async def index(request):
     with open("camera.html", "r") as f:
         return web.Response(content_type="text/html", text=f.read())


 @routes.post("/setupRTC")
 async def setupRTC(request):
     clientOffer = await request.json()
     conn = RTCConnection()
+    conn.addVideo(cam.subscribe())
     response = await conn.getLocalDescription(clientOffer)
     return web.json_response(response)

+cam = CVCamera()
 routes.static("/rtcbot/", path="./rtcbot")
 app = web.Application()
 app.add_routes(routes)
 web.run_app(app, port=8000)
```

If on a Raspberry Pi with the Pi Camera, use `PiCamera` instead of `CVCamera`, with an otherwise identical API.

To display the video in our html document, we give:

```diff
 <html>
   <head>
     <meta charset="UTF-8" />
     <title>RTCBot: Camera Streaming</title>
     <script src="rtcbot/rtcbot.js"></script>
   </head>
   <body style="text-align: center;padding-top: 30px;">
     <video autoplay playsinline></video>
     <p>
       Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
     </p>
     <script>
       // The connection object
       var conn = new RTCConnection();

+      // If the other side sends video, onVideo is called, and returns a video stream, that can be displayed by giving it as the srcObject
+      // of the given element. Please note that onVideo must be set before calling conn.getLocalDescription(),
+      // for the RTCConnection to accept incoming video streams.
+      conn.onVideo(
+        stream => (document.querySelector("video").srcObject = stream)
+      );
+
       // Here we set up the connection. We put it in an async function, since we will be
       // waiting for results from the server (Promises).
       async function setupRTC() {
         console.log("Setting up a real-time connection to the server");

         // Get the information needed to connect from the server to the browser
         let offer = await conn.getLocalDescription();

         // POST the information to the server, which will respond with the corresponding remote
         // connection's description
         let response = await fetch("/setupRTC", {
           method: "POST",
           cache: "no-cache",
           body: JSON.stringify(offer)
         });

         // Set the remote server's information
         await conn.setRemoteDescription(await response.json());

         console.log("Setup Finished");
       }

       setupRTC(); // Run the async function in the background.
     </script>
   </body>
 </html>

```

### Full Code

```python
from aiohttp import web
from rtcbot import RTCConnection, CVCamera

routes = web.RouteTableDef()

@routes.get("/")
async def index(request):
    with open("camera.html", "r") as f:
        return web.Response(content_type="text/html", text=f.read())

@routes.post("/setupRTC")
async def setupRTC(request):
    clientOffer = await request.json()
    conn = RTCConnection()

    conn.addVideo(cam.subscribe())

    response = await conn.getLocalDescription(clientOffer)
    return web.json_response(response)

cam = CVCamera()
routes.static("/rtcbot/", path="./rtcbot")
app = web.Application()
app.add_routes(routes)
web.run_app(app, port=8000)
```

```html
<html>
  <head>
    <meta charset="UTF-8" />
    <title>RTCBot: Camera Streaming</title>
    <script src="rtcbot/rtcbot.js"></script>
  </head>
  <body style="text-align: center;padding-top: 30px;">
    <video autoplay playsinline></video>
    <p>
      Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
    </p>
    <script>
      // The connection object
      var conn = new RTCConnection();

      // If the other side sends video, onVideo is called, and returns a video stream, that can be displayed by giving it as the srcObject
      // of the given element. Please note that onVideo must be set before calling conn.getLocalDescription(),
      // for the RTCConnection to accept incoming video streams.
      conn.onVideo(
        stream => (document.querySelector("video").srcObject = stream)
      );

      // Here we set up the connection. We put it in an async function, since we will be
      // waiting for results from the server (Promises).
      async function setupRTC() {
        console.log("Setting up a real-time connection to the server");

        // Get the information needed to connect from the server to the browser
        let offer = await conn.getLocalDescription();

        // POST the information to the server, which will respond with the corresponding remote
        // connection's description
        let response = await fetch("/setupRTC", {
          method: "POST",
          cache: "no-cache",
          body: JSON.stringify(offer)
        });

        // Set the remote server's information
        await conn.setRemoteDescription(await response.json());

        console.log("Setup Finished");
      }

      setupRTC(); // Run the async function in the background.
    </script>
  </body>
</html>
```
