import asyncio
from rtcbot import GPS

import logging

# logging.basicConfig(level=logging.DEBUG)

g = GPS("/dev/ttyACM1")


@g.subscribe
def onData(d):
    print(d)


loop = asyncio.get_event_loop()
# asyncio.ensure_future(sendAndReceive(conn))

loop.run_forever()
