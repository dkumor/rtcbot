from rtcbot import Microphone, Speaker, CVCamera, CVDisplay
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

m = Microphone()
s = Speaker()
c = CVCamera()
d = CVDisplay()

s.putSubscription(m)
d.putSubscription(c)


@c.onReady
def ready():
    print("LOL READY")


@d.onError
def err(e):
    print("ERR", e)


asyncio.get_event_loop().run_forever()
