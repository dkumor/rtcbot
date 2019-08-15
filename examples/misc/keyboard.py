# import logging
# logging.basicConfig(level=logging.DEBUG)
import asyncio
from rtcbot import Keyboard

kb = Keyboard()


@kb.subscribe
def onkey(key):
    print(key)


try:
    asyncio.get_event_loop().run_forever()
finally:
    kb.close()
