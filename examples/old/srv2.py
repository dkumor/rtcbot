import asyncio

import os
from aiohttp import web
from av import VideoFrame
import json

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder

from pirtcbot import camera

ROOT = os.path.dirname(__file__)


class VideoSender(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        global cam
        self.framereader = cam.frameSubscribe()

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        # Send a new frame
        img = await self.framereader.getFrame()

        new_frame = VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.pts = pts
        new_frame.time_base = time_base
        return new_frame


async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)
    web.run_app(app, port=args.port)


pcs = set()


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()
    cam.close()


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            channel.send("pong")

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        print("ICE connection state is %s" % pc.iceConnectionState)
        if pc.iceConnectionState == "failed":
            await pc.close()

    cameravideo = VideoSender()
    pc.addTrack(cameravideo)

    # handle offer
    await pc.setRemoteDescription(offer)

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


import logging

logging.basicConfig(level=logging.DEBUG)

app = web.Application()

try:
    import picamera

    cam = camera.PiCamera()
except ImportError:
    cam = camera.CVCamera()

app.on_shutdown.append(on_shutdown)
app.router.add_get("/", index)
app.router.add_get("/client.js", javascript)
app.router.add_post("/offer", offer)
web.run_app(app, port=8080)
