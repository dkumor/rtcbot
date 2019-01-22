import aiohttp
from rtcbot import RTCConnection, CVDisplay, Speaker, Gamepad, Microphone
import asyncio
import json
import logging
import cv2

# logging.basicConfig(level=logging.DEBUG)


disp = CVDisplay()
s = Speaker()
# m = Microphone()
g = Gamepad()

conn = RTCConnection()


@conn.video.subscribe
def onFrame(frame):
    frame = cv2.flip(frame, 0)
    frame = cv2.resize(frame, (frame.shape[1] * 4, frame.shape[0] * 4))
    disp.put_nowait(frame[:, ::-1, :])


@conn.audio.subscribe
def onAudio(data):
    s.put_nowait(data * 8)  # Make it louder


# conn.audio.putSubscription(m)
# conn.putSubscription(g)

turnState = 0
gasStateZ = 0
gasStateRZ = 0
rotState = 0


def onEvent(evt):
    global turnState, gasStateRZ, gasStateZ, rotState
    changed = False
    value = evt["state"]  # / 32767
    if evt["code"] == "ABS_X":
        turnStateNew = value / 32767
        if turnStateNew != turnState:
            turnState = turnStateNew
            changed = True
    elif evt["code"] == "ABS_Z":
        gasStateZNew = value / 1024
        if gasStateZNew != gasStateZ:
            gasStateZ = gasStateZNew
            changed = True
    elif evt["code"] == "ABS_RZ":
        gasStateRZNew = value / 1024
        if gasStateRZNew != gasStateRZ:
            gasStateRZ = gasStateRZNew
            changed = True
    if evt["code"] == "ABS_RX":
        rotStateNew = value / 32767
        if rotStateNew != rotState:
            rotState = rotStateNew
            changed = True

    if changed:
        conn.put_nowait(
            {
                "turn": int(turnState * 1024),
                "rot": -int(rotState * 1024),
                "gas": int(1024 * (gasStateRZ - gasStateZ)),
            }
        )
    # conn.put_nowait(evt)


async def setupConnection():
    print("Starting")
    desc = await conn.getLocalDescription()
    desc = json.dumps(desc)
    print(desc)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://192.168.50.183:8000/setupRTC", data=desc
        ) as resp:
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
