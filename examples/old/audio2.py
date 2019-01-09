from rtcbot import Microphone, Speaker
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)
m = Microphone()
s = Speaker()
s.playStream(m)


async def testme():
    await asyncio.sleep(5)
    s.stop()
    m.unsubscribe()


asyncio.ensure_future(testme())
asyncio.get_event_loop().run_forever()
