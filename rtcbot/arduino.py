import asyncio

import logging

import serial
import serial_asyncio
import struct

from .base import SubscriptionProducerConsumer, SubscriptionClosed


class _serialProtocol(asyncio.Protocol):
    _log = logging.getLogger("rtcbot.SerialConnection")

    def __init__(
        self,
        putter,
        url="/dev/ttyS0",
        readFormat="\n",
        writeFormat=None,
        baudrate=115200,
        writeKeys=None,
        readKeys=None,
        startByte=None,
        onReady=lambda x: 0,
        loop=None,
    ):
        self.putter = putter
        self.onReady = onReady

        # The startByte is actually a byte array
        self.startByte = startByte
        self.started = startByte is None  # if not started, wait

        if self.startByte is not None:
            # We want it to be a bytes object
            try:
                len(self.startByte)
            except:
                self.startByte = bytes([self.startByte])

        self.readFormat = readFormat
        self.readStruct = None
        if readFormat is not None and readFormat != "\n":
            self.readStruct = struct.Struct(readFormat)
        self.readKeys = readKeys

        self.writeStruct = None
        if writeFormat is not None:
            self.writeStruct = struct.Struct(writeFormat)
        self.writeKeys = writeKeys

        self.incomingMessageBuffer = bytes()

        ser = serial.serial_for_url(url, baudrate=baudrate)
        ser.rts = False

        if loop is None:
            loop = asyncio.get_event_loop()
        self.transport = serial_asyncio.SerialTransport(loop, self, ser)

    def write(self, msg):
        """
        By default, writes the given string/bytes object to the serial port. If a :code:`writeFormat` was given during initialization, it performs
        preprocessing before sending, as follows:
        
        - Given a tuple/list, encodes the elements into the struct specified by :code:`writeFormat`.
        - If :code:`writeKeys` were given, assumes a dictionary or object input, and converts the given keys in order into the struct specified by :code:`writeFormat`.

        An error is raised if the list is the wrong size or object does not contain all of the required keys. 
        An error is also raised if the given object cannot cleanly convert into the struct type.
        """
        self._log.debug("sendmsg: %s", msg)
        if self.isConnected():
            if self.writeStruct is not None:
                if self.writeKeys is not None:
                    msg = [msg[key] for key in self.writeKeys]
                packedMessage = self.writeStruct.pack(*msg)
                self._log.debug("send %s", packedMessage)
                self.transport.write(packedMessage)
            else:
                try:
                    # Encode strings to bytes, because we can only send bytes
                    msg = msg.encode()
                except:
                    pass
                self.transport.write(msg)
        else:
            raise ConnectionError("Serial Connection is closed")

    def isConnected(self):
        """
        Returns whether the serial port is active. 
        """
        return self.transport is not None and self.started

    def connection_made(self, transport):
        """
        Internal function. Notifies the SerialConnection that the underlying serial port is opened.

        Do not call this function.
        """
        self._log.debug("Serial Connection Made")
        if self.startByte is None:
            self.onReady(True)

    def connection_lost(self, exc):
        """
        Internal function. Notifies the SerialConnection when the underlying serial port is closed.

        Do not call this function.
        """
        self._log.warn("Serial Connection Lost")
        self.transport = None
        self.onReady(False)

    def data_received(self, data):
        """
        Internal function. Is called whenever new data shows up on the serial connection.
        The function processes this raw data, and if a full message was received, 
        it is decoded and passed to the readQueue.

        Do not call this function.
        """
        self._log.debug("recv %s", data)
        self.incomingMessageBuffer += data

        if not self.started:
            # Need to check the startByte to see if we can receive
            if not self.startByte in self.incomingMessageBuffer:
                # We cut the buffer to size, removing data that can't be part of start byte
                if len(self.startByte) < len(self.incomingMessageBuffer):
                    self.incomingMessageBuffer = self.incomingMessageBuffer[
                        -len(self.startByte) :
                    ]
                self._log.debug("Ignoring: start byte %s not found", self.startByte)
                return
            else:
                self._log.debug("startBytes %s found - starting read", self.startByte)
                _, self.incomingMessageBuffer = self.incomingMessageBuffer.split(
                    self.startByte, 1
                )
                self.started = True
                self.onReady(True)

        if self.readStruct is not None:
            while len(self.incomingMessageBuffer) >= self.readStruct.size:
                msg = self.readStruct.unpack(
                    self.incomingMessageBuffer[: self.readStruct.size]
                )
                self.incomingMessageBuffer = self.incomingMessageBuffer[
                    self.readStruct.size :
                ]

                if self.readKeys is not None:
                    msg = dict(zip(self.readKeys, msg))
                self._log.debug("recvmsg: %s", msg)
                self.putter(msg)
        elif self.readFormat is None:
            self.putter(self.incomingMessageBuffer)
            self.incomingMessageBuffer = bytes()
        else:
            # We split by line:
            outputArray = self.incomingMessageBuffer.split(b"\n")
            self.incomingMessageBuffer = outputArray[-1]
            for i in range(len(outputArray) - 1):
                # This returns the bytes object of the line.
                # We don't convert to string, since people might be sending non-ascii characters.
                # When receiving, the user should use .decode('ascii') to get a a string.
                self._log.debug("recvmsg: %s", outputArray[i])
                self.putter(outputArray[i])


class SerialConnection(SubscriptionProducerConsumer):
    """
    Handles sending and receiving commands to/from a a serial port. Has built-in support
    for sending structs to/from Arduinos.
    
    By default, reads and writes bytes from/to the serial port, splitting incoming messages
    by newline. To return raw messages (without splitting), use :code:`readFormat=None`.

    If a :code:`writeFormat` or :code:`readFormat` is given, they are interpreted as `struct format strings <https://docs.python.org/3/library/struct.html#format-strings>`_,
    and all incoming or outgoing messages are assumed to conform to the given format. Without setting :code:`readKeys` or :code:`writeKeys`,
    the messages are assumed to be tuples or lists.

    When given a list of strings for :code:`readKeys` or :code:`writeKeys`, the write or read formats are assumed to come from
    objects with the given keys. Using these, a SerialConnection can read/write python dicts to the associated structure formats.
    
    """

    _log = logging.getLogger("rtcbot.SerialConnection")

    def __init__(
        self,
        url="/dev/ttyS0",
        readFormat="\n",
        writeFormat=None,
        baudrate=115200,
        writeKeys=None,
        readKeys=None,
        startByte=None,
        delayWriteStart=0,
        loop=None,
    ):
        super().__init__(
            directPutSubscriptionType=asyncio.Queue,
            defaultSubscriptionType=asyncio.Queue,
            logger=self._log,
            defaultAutosubscribe=False,
        )

        self._protocol = _serialProtocol(
            self._put_nowait,
            url=url,
            readFormat=readFormat,
            writeFormat=writeFormat,
            baudrate=baudrate,
            writeKeys=writeKeys,
            readKeys=readKeys,
            startByte=startByte,
            onReady=self._setReady,
            loop=loop,
        )

        # If we toggle DTR, it waits for an arduino reset
        # https://stackoverflow.com/questions/21073086/wait-on-arduino-auto-reset-using-pyserial
        self._delayStart = delayWriteStart

        # and now we create an async task which loops putting data into the serial connection.
        asyncio.ensure_future(self._dataWriter())

    async def _dataWriter(self):
        await self.onReady()
        self._log.debug("Connection opened")
        if self._delayStart > 0:
            self._log.debug("Delaying write start by %f seconds", self._delayStart)
            await asyncio.sleep(self._delayStart)
        self._log.debug("Starting connection data writer")

        while not self._shouldClose:
            try:
                data = await self._get()
                self._protocol.write(data)
            except SubscriptionClosed:
                pass
        self._log("Shutting down serial connection")
        self._protocol.transport.close()
