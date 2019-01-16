import asyncio
from rtcbot import (
    RTCConnection,
    Microphone,
    Speaker,
    CVDisplay,
    CVCamera,
    SubscriptionClosed,
)
import logging
from contextlib import suppress
import signal

logging.basicConfig(level=logging.DEBUG)

m = Microphone()
s = Speaker()
d = CVDisplay()
cam = CVCamera()

# cam.subscribe(d)

c1 = RTCConnection()
c2 = RTCConnection()

c1.video.putSubscription(cam)
c1.audio.putSubscription(m)

c2.video.subscribe(d)
c2.audio.subscribe(s)


async def testMe():
    offer = await c1.getLocalDescription()
    response = await c2.getLocalDescription(offer)
    await c1.setRemoteDescription(response)


asyncio.ensure_future(testMe())


loop = asyncio.get_event_loop()


async def closer(signal):
    print("CLOSER")
    await asyncio.gather(c1.close(), c2.close())
    print("STOP")
    loop.stop()


loop.add_signal_handler(
    signal.SIGINT, lambda x=signal.SIGINT: asyncio.ensure_future(closer(x))
)
loop.set_debug(True)
try:
    loop.run_forever()
finally:
    m.close()
    s.close()
    cam.close()
    d.close()
    print("DONE")
    with suppress(asyncio.CancelledError, SubscriptionClosed):
        loop.run_until_complete(asyncio.gather(*asyncio.Task.all_tasks()))
    loop.close()
