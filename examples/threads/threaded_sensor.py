from aiohttp import web

routes = web.RouteTableDef()

from rtcbot import RTCConnection, getRTCBotJS, CVCamera

camera = CVCamera()
# For this example, we use just one global connection
conn = RTCConnection()
conn.video.putSubscription(camera)

import time
import random
import asyncio

from rtcbot.base import ThreadedSubscriptionProducer


def get_sensor_data():
    time.sleep(0.5)  # Represents an operation that takes half a second to complete
    return random.random()


class MySensor(ThreadedSubscriptionProducer):
    def _producer(self):
        self._setReady(True)  # Notify that ready to start gathering data
        while not self._shouldClose:  # Keep gathering until close is requested
            time.sleep(1)
            data = get_sensor_data()
            # Send the data to the asyncio thread,
            # so it can be retrieved with await mysensor.get()
            self._put_nowait(data)
        self._setReady(False)  # Notify that sensor is no longer operational


mysensor = MySensor()


async def send_sensor_data():
    while True:
        data = await mysensor.get()  # we await the output of MySensor in a loop
        conn.put_nowait(data)


asyncio.ensure_future(send_sensor_data())

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
            <video autoplay playsinline controls></video> <audio autoplay></audio>
            <p>
            Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
            </p>
            <script>
                var conn = new rtcbot.RTCConnection();

                conn.video.subscribe(function(stream) {
                    document.querySelector("video").srcObject = stream;
                });

                conn.subscribe(m => console.log("Received from python:", m));

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
    mysensor.close()


conn.onClose(cleanup)

app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
