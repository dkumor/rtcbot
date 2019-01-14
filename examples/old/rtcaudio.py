import asyncio
from rtcbot import RTCConnection, Microphone, Speaker, CVDisplay, CVCamera
import logging

logging.basicConfig(level=logging.DEBUG)

m = Microphone()

s = Speaker()
d = CVDisplay()
cam = CVCamera()

# cam.subscribe(d)


async def test2():
    while True:
        await asyncio.sleep(1)


async def testMe():

    c1 = RTCConnection()
    c2 = RTCConnection()

    c1.addVideo(cam)
    c1.addAudio(m)

    @c2.onAudio
    def getAudioStream(st):
        s.putSubscription(st)

    @c2.onVideo
    def getVideoStream(st):
        d.putSubscription(st)

    offer = await c1.getLocalDescription()
    response = await c2.getLocalDescription(offer)
    await c1.setRemoteDescription(response)


asyncio.ensure_future(testMe())

asyncio.get_event_loop().run_forever()
