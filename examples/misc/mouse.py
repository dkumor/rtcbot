# import logging

# logging.basicConfig(level=logging.DEBUG)
import asyncio
from rtcbot import Mouse

m = Mouse()


@m.subscribe
def onkey(key):
    print(key)


try:
    asyncio.get_event_loop().run_forever()
finally:
    m.close()
