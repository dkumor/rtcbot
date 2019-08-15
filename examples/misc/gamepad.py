# import logging

# logging.basicConfig(level=logging.DEBUG)
import asyncio
from rtcbot import Gamepad

g = Gamepad()


@g.subscribe
def onkey(key):
    print(key)


try:
    asyncio.get_event_loop().run_forever()
finally:
    g.close()
