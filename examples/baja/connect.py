import aiohttp
from rtcbot import RTCConnection, CVDisplay, Speaker, Gamepad
import asyncio
import json
import logging

logging.basicConfig(level=logging.DEBUG)


disp = CVDisplay()
s = Speaker()
g = Gamepad()

conn = RTCConnection()
conn.video.subscribe(disp)
conn.audio.subscribe(s)
# conn.putSubscription(g)


def onEvent(evt):
    conn.put_nowait(json.dumps(evt))


async def setupConnection():
    print("Starting")
    desc = await conn.getLocalDescription()
    desc = json.dumps(desc)
    print(desc)
    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/setupRTC", data=desc) as resp:
            print(resp.status)
            response = await resp.json()
            print(response)
            await conn.setRemoteDescription(response)

    g.subscribe(onEvent)
    print("Should be set up...")


loop = asyncio.get_event_loop()
asyncio.ensure_future(setupConnection())
try:
    loop.run_forever()
finally:
    disp.close()
    g.close()
    s.close()
