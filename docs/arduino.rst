===================
Arduino
===================

The Pi can control certain hardware directly, but a dedicated microcontroller can be better for real-time tasks like controlling servos or certain sensors.

To show the simplicity of the library, we show a full example of both Arduino and Python code:

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

    void init() {
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

The above code echoes the values sent to it, with the values switched. The python code to read it is::

    import asyncio
    from pirtcbot.arduino import SerialConnection

    loop = asyncio.get_event_loop()

    sc = SerialConnection(
        writeFormat="<HB",
        writeKeys=["value1", "value2"],
        readFormat="<BH",
        readKeys=["value1", "value2"],
        loop=loop
    )

    async def sendAndReceive(sc):
        sc.write({"value1": 1003,"value2": 2})
        msg = await sc.readQueue.get()
        print("Received:",msg)
        await asyncio.sleep(1)

    asyncio.ensure_future(sendAndReceive(sc))

    try:
        loop.run_forever()
    finally:
        print("Exiting Event Loop")
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

By default, it attempts to connect to '/dev/ttyS0', which is the hardware serial port on the Raspberry Pi.
Running this program, you get::

    Received: {"value1": 2,"value2": 1003}
    Received: {"value1": 2,"value2": 1003}
    Received: {"value1": 2,"value2": 1003}


API
++++++++++++++++

.. automodule:: pirtcbot.arduino
    :members:
    :undoc-members:
    :show-inheritance: