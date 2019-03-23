from inputs import devices
import logging
import asyncio

from .base import ProcessSubscriptionProducer, SubscriptionClosed

# The messages to filter by default
defaultFilter = lambda x: x["code"] != "SYN_REPORT"


class InputDevice(ProcessSubscriptionProducer):
    """
    A thin wrapper over :mod:`inputs`, which permits getting events in an asynchronous manner.

    """

    _log = logging.getLogger("rtcbot.InputDevice")

    def __init__(self, device, eventFilter=defaultFilter, loop=None):
        self._device = device
        self._eventFilter = eventFilter

        # We use a joinTimeout of 0.1, because it is very likely to be blocked
        super().__init__(asyncio.Queue, logger=self._log, loop=loop, joinTimeout=0.1)

    def _producer(self):
        """
        I really wish there were a non-blocking way to do this... As it stands,
        this code relies on the daemon property of the thread to kill a blocked read call...

        Nevertheless, it does work, on linux. It looks like inputs uses a process on macs,
        which might not exit cleanly...
        """
        self._setReady(True)
        self._log.debug("Started listening to input device events")
        while not self._shouldClose:
            events = self._device.read()
            for event in events:
                e = {
                    "timestamp": event.timestamp,
                    "code": event.code,
                    "state": event.state,
                    "event": event.ev_type,
                }
                if self._eventFilter(e):
                    self._put_nowait(e)
        self._setReady(False)


class Gamepad(InputDevice):
    def __init__(self, eventFilter=defaultFilter, loop=None):
        super().__init__(devices.gamepads[0], eventFilter=eventFilter, loop=loop)


class Mouse(InputDevice):
    def __init__(self, eventFilter=defaultFilter, loop=None):
        super().__init__(devices.mice[0], eventFilter=eventFilter, loop=loop)


class Keyboard(InputDevice):
    def __init__(self, eventFilter=defaultFilter, loop=None):
        super().__init__(devices.keyboards[0], eventFilter=eventFilter, loop=loop)
