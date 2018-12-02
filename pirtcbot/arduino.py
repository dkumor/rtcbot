import asyncio

import logging

import serial
import serial_asyncio
import struct


class ArduinoConnection(asyncio.Protocol):
    """
    Handles sending and receiving commands to/from an arduino using a serial port.
    Communication with the Arduino is performed through C structs: A python dict or tuple is
    directly encoded by Python, and is read by the Arduino in a way that the values are directly
    available for use.

    On the arduino, you need to create an associated struct into which messages will be received::

        #include <stdint.h>
        typedef __attribute__ ((packed)) struct {
            int16_t value1;
            uint8_t value2;
        } controlMessage;

    The packed attribute ensures that the arduino's struct is compatible with the encoding performed by python, and the message can be read in directly from the Arduino::

        controlMessage msg;
        Serial.read(&msg,sizeof(msg));

    From Python, you need to give the ArduinoConnection the structure shape in `the format expected by
    Python's structure packing library <https://docs.python.org/3/library/struct.html#format-strings>`_

    The arduino is little endian (each string should start with "<")::

        conn = ArduinoConnection(
            writeFormat="<hB",
            writeKeys=["value1","value2"],
            ...
        )
    
    The writeFormat string above tells the ArduinoConnection that the first element of the struct ("value1"),
    is of format "h", which represents an arduino integer. You can then send messages to the Arduino::
        
        conn.write({"value1": -23,"value2": 101})

    Finally, you can send structs to the ArduinoConnection from the Arduino::

        typedef __attribute__ ((packed)) struct {
            uint8_t sensorID;
            uint16_t measurement;
        } sensorMessage;

    and::

        sensorMessage msg = { .sensorID = 12, .measurement=123 };
        Serial.write(&msg,sizeof(msg));

    You can then get the message from a Queue::

        conn = ArduinoConnection(
            readFormat="<BH",
            readKeys=["sensorID","measurement"],
            writeFormat="<hB",
            writeKeys=["value1","value2"],
        )

        print(await conn.readQueue.get() )
        # {"sensorID": 12, "measurement": 123}


    """

    def __init__(
        self,
        readFormat,
        writeFormat,
        url="/dev/ttyS0",
        baudrate=115200,
        readQueue=asyncio.Queue(),
        writeKeys=None,
        readKeys=None,
        loop=None,
    ):
        self._readQueue = readQueue

        self.readStruct = struct.Struct(readFormat)
        self.readKeys = readKeys
        self.writeStruct = struct.Struct(writeFormat)
        self.writeKeys = writeKeys

        self.incomingMessageBuffer = bytes()

        self.log = logging.getLogger("pirtcbot.ArduinoConnection")

        ser = serial.serial_for_url(url, baudrate=baudrate)

        self.transport = serial_asyncio.SerialTransport(loop, self, ser)

    @property
    def readQueue(self):
        """
        The queue holding decoded messages. You get messages from the Arduino by reading from this
        asyncio queue::

            message = await conn.readQueue.get()

        If readKeys are given, this gives a dict, and if readKeys are not given, returns a tuple containing
        the decoded values from the readFormat.
        """
        return self._readQueue

    def write(self, msg):
        """
        Given a tuple/list, encodes the elements into the struct specified by writeFormat,
        and sent over the serial connection.

        If writeKeys were given, assumes a dictionary or object input, and converts
        the given keys in order into the struct specified by writeFormat, and sent over the serial connection.
        """
        if self.writeKeys is not None:
            msg = [msg[key] for key in self.writeKeys]
        if self.isConnected():
            self.transport.write(self.writeStruct.pack(*msg))
        else:
            raise ConnectionError("Serial Connection is closed")

    def isConnected(self):
        """
        Returns whether the serial port is active. 
        """
        return self.transport is not None

    def connection_made(self, transport):
        """
        Internal function. Notifies the ArduinoConnection that the underlying serial port is opened.

        Do not call this function.
        """
        self.log.debug("Serial Connection Made")

    def connection_lost(self, exc):
        """
        Internal function. Notifies the ArduinoConnection when the underlying serial port is closed.

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
        readStructSize = self.readStruct.calcsize()
        self.incomingMessageBuffer += data
        while len(self.incomingMessageBuffer) >= readStructSize:
            msg = self.readStruct.unpack(self.incomingMessageBuffer[:readStructSize])
            self.incomingMessageBuffer = self.incomingMessageBuffer[readStructSize:]

            if self.readKeys is not None:
                msg = dict(zip(self.readKeys, msg))
            self.readQueue.put(msg)

