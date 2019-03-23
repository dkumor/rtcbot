# desktop.py

import asyncio
import aiohttp
import cv2
import json
from rtcbot import RTCConnection, Gamepad, CVDisplay

disp = CVDisplay()
g = Gamepad()
conn = RTCConnection()


@conn.video.subscribe
def onFrame(frame):
    # Show a 4x larger image so that it is easy to see
    resized = cv2.resize(frame, (frame.shape[1] * 4, frame.shape[0] * 4))
    disp.put_nowait(resized)


async def connect():
    localDescription = await conn.getLocalDescription()
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8080/connect", data=json.dumps(localDescription)
        ) as resp:
            response = await resp.json()
            await conn.setRemoteDescription(response)

    # Start sending gamepad controls
    g.subscribe(conn)


asyncio.ensure_future(connect())
try:
    asyncio.get_event_loop().run_forever()
finally:
    conn.close()
    disp.close()
    g.close()
