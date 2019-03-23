import asyncio
from rtcbot import Websocket, RTCConnection, CVCamera

cam = CVCamera()
conn = RTCConnection()
conn.video.putSubscription(cam)

# Connect establishes a websocket connection to the server,
# and uses it to send and receive info to establish webRTC connection.
async def connect():
    ws = Websocket("http://localhost:8080/ws")
    msg = await ws.get()
    robotDescription = await conn.getLocalDescription(msg)
    ws.put_nowait(robotDescription)
    print("Started WebRTC")
    await ws.close()


asyncio.ensure_future(connect())
try:
    asyncio.get_event_loop().run_forever()
finally:
    cam.close()
    conn.close()
