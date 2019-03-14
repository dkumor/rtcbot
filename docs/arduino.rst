===================
Arduino
===================

The Pi can control certain hardware directly, but a dedicated microcontroller can be better for real-time tasks like controlling servos or certain sensors.
The code here is dedicated to efficiently interfacing with microcontrollers, and was tested to work with both Arduino and ESP32,
but should work with any hardware with a serial port and C compiler.

You can connect a Pi to an Arduino using a USB cable (easiest), or, with the help of a `level shifter <https://www.sparkfun.com/products/12009>`_,
directly through the Pi's hardware serial pins (`BCM 14 and 15 <https://pinout.xyz/pinout/pin8_gpio14#>`_, see `here <https://spellfoundry.com/2016/05/29/configuring-gpio-serial-port-raspbian-jessie-including-pi-3/>`_ for details).
The SerialConnection class is provided to easily send and receive asynchronous commands as your robot is doing other processing.


Basic Communication
===========================


Assuming that you have connected the Pi to an Arduino with a USB cable, you can read and write to the serial port as follows::

    import asyncio
    from rtcbot.arduino import SerialConnection

    conn = SerialConnection("/dev/ttyAMA1")

    async def sendAndReceive(conn):
        conn.put_nowait("Hello world!")
        while True:
            msg = await conn.get().decode('ascii')
            print(msg)
            await asyncio.sleep(1)

    asyncio.ensure_future(sendAndReceive(conn))

    asyncio.get_event_loop().run_forever()

This sends a Hello World to the Arduino, and then reads the incoming serial messages line by line.
Given the corresponding Arduino code,

.. code-block:: c++

    void setup() {
        Serial.begin(115200);
    }
    void loop() {
        if (Serial.available() > 0) {
            Serial.print("I received: ");
            Serial.println(Serial.read());
        }
    }

you should get the messages::

    I received: H
    I received: e
    ...

By default, SerialConnection reads line by line. To get raw input as it comes in, you can set the readFormat to None::

    conn = SerialConnection("/dev/ttyAMA0",readFormat=None)

While reading/writing strings is useful for debugging, for speed and robustness, it is recommended that communication 
with the Arduino be performed through C structs. 

C Struct Messaging
=====================

When using a struct write format,
a Python dict or tuple is directly encoded by the SerialConnection, and is read by the Arduino in a way 
that the values are directly available for use.

As an example, we will write control messages to the Arduino. On the arduino, you need to create an associated struct into which messages will be received:

.. code-block:: c++

    #include <stdint.h>
    typedef __attribute__ ((packed)) struct {
        int16_t value1;
        uint8_t value2;
    } controlMessage;

The packed attribute ensures that the arduino's struct is compatible with the encoding performed by Python.

From Python, you need to give the SerialConnection the structure shape in `the format expected by
Python's structure packing library <https://docs.python.org/3/library/struct.html#format-strings>`_.
The arduino is little endian (each string should start with "<"). 
For example, we need to tell the SerialConnection that first element of the struct is called "value1",
and is a 16 bit integer (the default int size on a standard Arduino). 
This corresponds to the format character "h" (see structure packing `table of format values <https://docs.python.org/3/library/struct.html#format-characters>`_).
::

    conn = SerialConnection(
        url="/dev/ttyAMA1",
        writeFormat="<hB",
        writeKeys=["value1","value2"]
    )
    
With this format, you can send messages to the Arduino as dicts::
    
    conn.put_nowait({"value1": -23,"value2": 101})

To decode them on the Arduino, you can read:

.. code-block:: c++

    controlMessage msg;
    Serial.read((char*)&msg,sizeof(msg));

Similarly, you can also send structs to Python from the Arduino:

.. code-block:: c++

    typedef __attribute__ ((packed)) struct {
        uint8_t sensorID;
        uint16_t measurement;
    } sensorMessage;


and:

.. code-block:: c++

    sensorMessage msg = { .sensorID = 12, .measurement=123 };
    Serial.write((char*)&msg,sizeof(msg));

You can then get the message directly as a Python dict::

    conn = SerialConnection(
        url="/dev/ttyAMA1",
        readFormat="<BH",
        readKeys=["sensorID","measurement"]
    )

    # Run this in a coroutine
    print(await conn.get() )
    # {"sensorID": 12, "measurement": 123}


Full Example
===========================

The above can be demonstrated with a full example that sends and receives messages:

.. code-block:: c++

    // The controlMessage comes from the pi
    typedef __attribute__ ((packed)) struct {
        uint16_t value1;
        uint8_t value2;
    } controlMessage;

    // We write this back to the Pi
    typedef __attribute__ ((packed)) struct {
        uint8_t value1;
        uint16_t value2;
    } sensorMessage;

    // These are the specific message instances
    controlMessage cMsg;
    sensorMessage sMsg;

    void setup() {
        Serial.begin(115200);
    }
    void loop() {

        // Read the control message
        Serial.readBytes((char*)&cMsg,sizeof(cMsg));

        // set up the sensor message
        sMsg.value1 = cMsg.value2;
        sMsg.value2 = cMsg.value1;

        // Send it back!
        Serial.write((char*)&sMsg,sizeof(sMsg));
    }

The above code echoes the values sent to it, with value1 and value2 switched. The python code to read it is::

    import asyncio
    from rtcbot.arduino import SerialConnection

    loop = asyncio.get_event_loop()

    sc = SerialConnection(
        url="/dev/ttyAMA1",
        writeFormat="<HB",
        writeKeys=["value1", "value2"],
        readFormat="<BH",
        readKeys=["value1", "value2"],
        loop=loop
    )

    async def sendAndReceive(sc):
        while True:
            sc.put_nowait({"value1": 1003,"value2": 2})
            msg = await sc.get()
            print("Received:",msg)
            await asyncio.sleep(1)

    asyncio.ensure_future(sendAndReceive(sc))

    try:
        loop.run_forever()
    finally:
        print("Exiting Event Loop")
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

Running this program, you get::

    Received: {"value1": 2,"value2": 1003}
    Received: {"value1": 2,"value2": 1003}
    Received: {"value1": 2,"value2": 1003}


API
===========================

.. automodule:: rtcbot.arduino
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance:
