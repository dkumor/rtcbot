# Running Blocking Code

RTCBot uses python's asyncio event loop. This means that Python runs in a loop, handling events as they come in, all in a single thread. Any long-running operation must be specially coded to be async, so that it does not block operation of the event loop.

## A Common Issue

Suppose that you have a sensor that you want to use with RTCBot. Your goal is to retrieve values from the sensor, and then send the results to the browser.

We will use the function `get_sensor_data` to represent a sensor which takes half a second to retrieve data:

```python
import time
import random

def get_sensor_data():
    time.sleep(0.5) # Represents an operation that takes half a second to complete
    return random.random()
```

We will base this code on the original single-connection video-streaming tutorial for simplicity. We will send the sensor reading once a second:

```diff
 from aiohttp import web

 routes = web.RouteTableDef()

 from rtcbot import RTCConnection, getRTCBotJS, CVCamera

 camera = CVCamera()
 # For this example, we use just one global connection
 conn = RTCConnection()
 conn.video.putSubscription(camera)

+import time
+import random
+import asyncio
+
+
+def get_sensor_data():
+    time.sleep(0.5)  # Represents an operation that takes half a second to complete
+    return random.random()
+
+
+async def send_sensor_data():
+    while True:
+        await asyncio.sleep(1)
+        data = get_sensor_data()
+        conn.put_nowait(data)  # Send data to browser
+
+
+asyncio.ensure_future(send_sensor_data())

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

+                conn.subscribe(m => console.log("Received from python:", m));
+
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


 async def cleanup(app=None):
     await conn.close()
     camera.close()


 conn.onClose(cleanup)

 app = web.Application()
 app.add_routes(routes)
 app.on_shutdown.append(cleanup)
 web.run_app(app)
```

If you try this code, the video will freeze for half a second each second, while the sensor is being queried (i.e. while `time.sleep(0.5)` is being run).
This is because all of RTCBot's tasks happen in the same thread, and while reading the sensor, RTCBot is not sending video frames!

To fix this issue, the sensor needs to be read in a different thread, so that the event loop is not blocked. The sensor data then needs to be moved to the main thread, where it can be used by rtcbot.

## Producing Data in Another Thread

Thankfully, RTCBot has built-in helper classes that set everything up for you here. The `ThreadedSubscriptionProducer` runs in a system thread, allowing arbitrary blocking code, and has built-in mechanisms that let you queue up data for use from the asyncio event loop.

The code that blocks the connection:

```python
import time
import random
import asyncio

def get_sensor_data():
    time.sleep(0.5)  # Represents an operation that takes half a second to complete
    return random.random()

async def send_sensor_data():
    while True:
        await asyncio.sleep(1)
        data = get_sensor_data()
        conn.put_nowait(data)  # Send data to browser


asyncio.ensure_future(send_sensor_data())
```

can be fixed by moving the sensor-querying code into a `ThreadedSubscriptionProducer`:

```python
import time
import random
import asyncio

from rtcbot.base import ThreadedSubscriptionProducer

def get_sensor_data():
    time.sleep(0.5)  # Represents an operation that takes half a second to complete
    return random.random()

class MySensor(ThreadedSubscriptionProducer):
    def _producer(self):
        self._setReady(True) # Notify that ready to start gathering data
        while not self._shouldClose: # Keep gathering until close is requested
            time.sleep(1)
            data = get_sensor_data()
            # Send the data to the asyncio thread,
            # so it can be retrieved with await mysensor.get()
            self._put_nowait(data)
        self._setReady(False) # Notify that sensor is no longer operational

mysensor = MySensor()

async def send_sensor_data():
    while True:
        data = await mysensor.get() # we await the output of MySensor in a loop
        conn.put_nowait(data)

asyncio.ensure_future(send_sensor_data())

...

async def cleanup(app=None):
    await conn.close()
    camera.close()
    mysensor.close()
```

## Consuming Data in Another Thread

RTCBot has an equivalent mechanism for ingesting data - you can retrieve data, and then use it to control things with blocking code.

```python
import time

def set_output_value(value):
    time.sleep(0.5) # Represents an operation that takes half a second to complete
    print(value)

from rtcbot.base import ThreadedSubscriptionConsumer, SubscriptionClosed

class MyOutput(ThreadedSubscriptionConsumer):
    def _consumer(self):
        self._setReady(True)
        while not self._shouldClose:
            try:
                data = self._get()
                set_output_value(data)
            except SubscriptionClosed:
                break

        self._setReady(False)

myoutput = MyOutput()
```

You can now use `myoutput.put_nowait` in rtcbot to queue up data, which will be retrieved from the consumer thread.

## Summary

This tutorial introduced the `ThreadedSubscriptionProducer` and `ThreadedSubscriptionConsumer` classes, which allow you to use blocking code with the asyncio event loop. These functions allow handling the connection in the main thread, and doing all actions that might take a while in separate threads.
