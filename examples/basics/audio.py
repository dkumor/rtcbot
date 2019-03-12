
import asyncio
from rtcbot import Microphone, Speaker

microphone = Microphone()
speaker = Speaker()

speaker.putSubscription(microphone)

try:
    asyncio.get_event_loop().run_forever()
finally:
    microphone.close()
    speaker.close()
