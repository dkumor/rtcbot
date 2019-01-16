import asyncio

from rtcbot import Microphone, Speaker, CVCamera, CVDisplay
import asyncio
import functools
import os
import signal
from contextlib import suppress

import logging

logging.basicConfig(level=logging.DEBUG)

s = Speaker()
m = Microphone()
c = CVCamera()
d = CVDisplay()
m.subscribe(s)
c.subscribe(d)
loop = asyncio.get_event_loop()

"""
def shutdown(signame):
    print("got signal %s: exit" % signame)
    loop = asyncio.get_event_loop()
    loop.stop()



for sig in (signal.SIGINT, signal.SIGTERM):
    loop.add_signal_handler(sig, shutdown, sig)

print("Event loop running forever, press Ctrl+C to interrupt.")
print("pid %s: send SIGINT or SIGTERM to exit." % os.getpid())
"""
try:
    loop.run_forever()
finally:
    print("CLOSING")

    m.close()
    s.close()
    c.close()
    d.close()

    with suppress(asyncio.CancelledError):
        loop.run_until_complete(asyncio.gather(*asyncio.Task.all_tasks()))

    loop.close()
