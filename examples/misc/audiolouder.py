
import asyncio
from rtcbot import Microphone, Speaker

microphone = Microphone()
speaker = Speaker()


@microphone.subscribe
def onData(data):
    data = data * 5
    if speaker.ready:
        speaker.put_nowait(data)


try:
    asyncio.get_event_loop().run_forever()
finally:
    microphone.close()
    speaker.close()
