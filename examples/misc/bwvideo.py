
import asyncio
from rtcbot import CVCamera, CVDisplay
import cv2

camera = CVCamera()
display = CVDisplay()


@camera.subscribe
def onFrame(frame):
    bwframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    display.put_nowait(bwframe)


try:
    asyncio.get_event_loop().run_forever()
finally:
    camera.close()
    display.close()
