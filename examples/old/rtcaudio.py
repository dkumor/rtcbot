import asyncio
from rtcbot import RTCConnection, Microphone, Speaker
import logging

logging.basicConfig(level=logging.DEBUG)

m = Microphone()

s = Speaker()


async def testMe():

    c1 = RTCConnection()
    c2 = RTCConnection()

    c1.addAudio(m)

    offer = await c1.getLocalDescription()
    response = await c2.getLocalDescription(offer)
    await c1.setRemoteDescription(response)


asyncio.ensure_future(testMe())

asyncio.get_event_loop().run_forever()
