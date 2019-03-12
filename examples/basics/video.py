
import asyncio
from rtcbot import CVCamera, CVDisplay

camera = CVCamera()
display = CVDisplay()

display.putSubscription(camera)

try:
    asyncio.get_event_loop().run_forever()
finally:
    camera.close()
    display.close()
