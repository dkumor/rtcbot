import asyncio

import logging

import serial
import serial_asyncio
import struct


class SerialConnection(asyncio.Protocol):
    """
    Handles sending and receiving commands to/from an arduino using a serial port.
    
    By default, reads and writes bytes from/to the serial port, splitting incoming messages
    by newline. To return raw messages (without splitting), use :code:`readFormat=None`.

    Messages are read into an :code:`asyncio.Queue` object, which is created for you if it is not given.

    If a :code:`writeFormat` or :code:`readFormat` is given, they are interpreted as `struct format strings <https://docs.python.org/3/library/struct.html#format-strings>`_,
    and all incoming or outgoing messages are assumed to conform to the given format. Without setting :code:`readKeys` or :code:`writeKeys`,
    the messages are assumed to be tuples or lists.

    When given a list of strings for :code:`readKeys` or :code:`writeKeys`, the write or read formats are assumed to come from
    objects with the given keys. Using these, a SerialConnection can read/write python dicts to the associated structure formats.
    
    """

    def __init__(
        self,
        url="/dev/ttyS0",
        readFormat="\n",
        writeFormat=None,
        baudrate=115200,
        readQueue=None,
        writeKeys=None,
        readKeys=None,
        loop=None,
    ):
        if readQueue is None:
            readQueue = asyncio.Queue()
        self._readQueue = readQueue

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

        self.log = logging.getLogger("pirtcbot.SerialConnection")

        ser = serial.serial_for_url(url, baudrate=baudrate)

        if loop is None:
            loop = asyncio.get_event_loop()
        self.transport = serial_asyncio.SerialTransport(loop, self, ser)

    @property
    def readQueue(self):
        """
        The :code:`asyncio.Queue` holding decoded messages. Returns the passed in queue if one was given when initializing the SerialConnection. You read messages from the Arduino by getting::

            message = await conn.readQueue.get()

        If :code:`readKeys` were given, this gives a dict, and if readKeys were not given, returns a tuple containing
        the decoded values from the :code:`readFormat`. 
        
        If no read format string was given, the queue holds bytes objects
        each containing one message from the Arduino. To convert one such message to a string, call::

            message.decode('ascii')

        Finally, if the readFormat is set to None, the SerialConnection enqueues data as it is received, without processing.
        """
        return self._readQueue

    def write(self, msg):
        """
        By default, writes the given string/bytes object to the serial port. If a :code:`writeFormat` was given during initialization, it performs
        preprocessing before sending, as follows:
        
        - Given a tuple/list, encodes the elements into the struct specified by :code:`writeFormat`.
        - If :code:`writeKeys` were given, assumes a dictionary or object input, and converts the given keys in order into the struct specified by :code:`writeFormat`.

        An error is raised if the list is the wrong size or object does not contain all of the required keys. 
        An error is also raised if the given object cannot cleanly convert into the struct type.
        """
        self.log.debug("sendmsg: %s", msg)
        if self.isConnected():
            if self.writeStruct is not None:
                if self.writeKeys is not None:
                    msg = [msg[key] for key in self.writeKeys]
                packedMessage = self.writeStruct.pack(*msg)
                self.log.debug("send %s", packedMessage)
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
        return self.transport is not None

    def connection_made(self, transport):
        """
        Internal function. Notifies the SerialConnection that the underlying serial port is opened.

        Do not call this function.
        """
        self.log.debug("Serial Connection Made")

    def connection_lost(self, exc):
        """
        Internal function. Notifies the SerialConnection when the underlying serial port is closed.

        Do not call this function.
        """
        self.log.warn("Serial Connection Lost")
        self.transport = None

    def data_received(self, data):
        """
        Internal function. Is called whenever new data shows up on the serial connection.
        The function processes this raw data, and if a full message was received, 
        it is decoded and passed to the readQueue.

        Do not call this function.
        """
        self.log.debug("recv %s", data)
        self.incomingMessageBuffer += data

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
                self.log.debug("recvmsg: %s", msg)
                self._readQueue.put_nowait(msg)
        elif self.readFormat is None:
            self._readQueue.put_nowait(self.incomingMessageBuffer)
            self.incomingMessageBuffer = bytes()
        else:
            # We split by line:
            outputArray = self.incomingMessageBuffer.split(b"\n")
            self.incomingMessageBuffer = outputArray[-1]
            for i in range(len(outputArray) - 1):
                # This returns the bytes object of the line.
                # We don't convert to string, since people might be sending non-ascii characters.
                # When receiving, the user should use .decode('ascii') to get a a string.
                self.log.debug("recvmsg: %s", outputArray[i])
                self._readQueue.put_nowait(outputArray[i])

