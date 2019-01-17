"""
from inputs import devices
import time

print(devices.gamepads)
gp = devices.gamepads[0]

while True:
    evt = gp.read()
    print(len(evt))
    for event in evt:
        print(event.timestamp, event.ev_type, event.code, event.state)
    # time.sleep(5)
"""
from rtcbot.inputs import Gamepad
import asyncio
from contextlib import suppress
import logging


logging.basicConfig(level=logging.DEBUG)

g = Gamepad()


@g.subscribe
def result(data):
    print(data)


loop = asyncio.get_event_loop()
try:
    loop.run_forever()
finally:
    g.close()
    with suppress(asyncio.CancelledError):
        loop.run_until_complete(asyncio.gather(*asyncio.Task.all_tasks()))
    loop.close()
