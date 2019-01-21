from ..base import BaseSubscriptionProducer
from ..arduino import SerialConnection
import logging
import asyncio

import pynmea2


class GPS(BaseSubscriptionProducer):

    _log = logging.getLogger("rtcbot.GPS")

    def __init__(self, url="/dev/ttyACM0", baudrate=115200, dataFilter=None):
        super().__init__(asyncio.Queue, logger=self._log)

        self._serial = SerialConnection(url=url, baudrate=baudrate)
        self._serial.subscribe(self._onData)

        @self._serial.onReady
        def sr():
            self._setReady(True)

        self._serial.onError(self._setError)

        # The GPS also has special methods that return most recent lat/long
        self._latitude = None
        self._longitude = None
        self._altitude = None

        self._dataFilter = dataFilter
        if self._dataFilter is None:
            self._dataFilter = lambda x: True

    def _onData(self, data):
        self._log.debug("NMEA: %s", data)

        data = pynmea2.parse(data.decode("ascii"))

        try:
            self._latitude = data.latitude
            self._longitude = data.longitude
        except AttributeError:
            pass
        try:
            self._altitude = data.altitude
        except:
            pass

        if self._dataFilter(data):
            self._put_nowait(data)

    def close(self):
        self._serial.close()
        super().close()

    @property
    def latitude(self):
        return self._latitude

    @property
    def longitude(self):
        return self._longitude

    @property
    def altitude(self):
        return self._altitude
