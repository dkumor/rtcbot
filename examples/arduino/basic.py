import asyncio
from rtcbot import SerialConnection

import logging

logging.basicConfig(level=logging.DEBUG)


async def sendAndReceive(conn):
    conn.put_nowait("Hello world!")
    while True:
        msg = (await conn.get()).decode("ascii")
        print(msg)
        await asyncio.sleep(1)


loop = asyncio.get_event_loop()
conn = SerialConnection("/dev/ttyACM0", startByte=bytes([192, 105]))


@conn.onReady
def ready():
    print("I AM READY")


asyncio.ensure_future(sendAndReceive(conn))

loop.run_forever()
