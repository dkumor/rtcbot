
import asyncio
from rtcbot import CVCamera, CVDisplay, Microphone, Speaker

camera = CVCamera()
display = CVDisplay()
microphone = Microphone()
speaker = Speaker()

display.putSubscription(camera)
speaker.putSubscription(microphone)

try:
    asyncio.get_event_loop().run_forever()
finally:
    camera.close()
    display.close()
    microphone.close()
    speaker.close()
