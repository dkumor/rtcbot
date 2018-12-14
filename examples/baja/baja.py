import asyncio
import serial_asyncio
from functools import partial

import RPi.GPIO as GPIO
import time

from pirtcbot.arduino import SerialConnection

GPIO.setmode(GPIO.BCM)
resetpin = 17

import logging

logging.basicConfig(level=logging.DEBUG)


def reset_arduino():
    # Toggles the reset pin - this makes sure that the serial connection is restarted
    # Honestly have no clue why it behaves so weird... but it does,so whatever.
    # I think the cleanup() is actually performing double duty: it makes the pin float, which
    # makes reset go to high across the voltage converter.
    print("Arduino RESET")
    GPIO.setup(resetpin, GPIO.OUT)

    GPIO.output(resetpin, GPIO.LOW)
    # time.sleep(0.12)
    # GPIO.output(resetpin, GPIO.HIGH)
    # No idea why, but need to wait these 2 seconds for GPIO.cleanup not to kill the arduino
    time.sleep(2)
    GPIO.cleanup()
    # time.sleep(0.5)
    print("Arduino RESET complete")


# # The controlMessage is sent over the wire, however, we also
# controlMessage = struct.Struct("<hB")
# sensorMessage = struct.Struct("<hB")

# class ArduinoConnection(asyncio.Protocol):
#     """
#     This class takes care of communication with the Arduino - it sends down all servo and motor commands,
#     and it receives all sensor values.
#     """

#     def __init__(self, sensor_queue, command_queue):
#         super().__init__()
#         self.transport = None
#         self.sensor_queue = sensor_queue
#         self.command_queue = command_queue
#         self.current_message = bytes()

#         # Need to reset
#         reset_arduino()

#         asyncio.ensure_future(self.sender())

#     def connection_made(self, transport):
#         print("Arduino connection made")
#         # Write
#         # transport.serial.rts = False
#         # transport.write(b"CINIT")
#         transport.write((1002).to_bytes(2, byteorder="little"))
#         self.transport = transport

#     def connection_lost(self, exc):
#         if self.transport is not None:
#             self.transport.close()
#         self.transport = None
#         print("Arduino connection lost")

#     def data_received(self, data):
#         print("RECEIVED", data)
#         self.current_message += data
#         while len(self.current_message) >= 2:
#             curint = int.from_bytes(self.current_message[:2], "little")
#             self.sensor_queue.put_nowait(curint)
#             self.current_message = self.current_message[2:]

#     def empty_command_queue(self, cmd):
#         # Just pass through cmd, or update it to the most recent command
#         while not self.command_queue.empty():
#             cmd = self.command_queue.get_nowait()
#         return cmd

#     async def sender(self):
#         """
#         This function sends the servo and motor control commands to the arduino once they appear in
#         the command queue
#         """
#         while True:  # keep looping forever

#             # Get the next command
#             cmd = await self.command_queue.get()

#             # Empty the queue of all commands
#             cmd = self.empty_command_queue(cmd)

#             while self.transport is None:
#                 await asyncio.sleep(0.1)  # Wait until we get a serial connection
#                 # Empty the quu
#                 cmd = self.empty_command_queue(cmd)

#             # PREPROCESS DATA HERE
#             self.transport.write(cmd)


async def processMessages(sensor_queue):
    while True:
        print("Running message Processing")
        msg = await sensor_queue.get()
        print("Got msg:", msg)


async def writeMessage(w):
    await asyncio.sleep(1)
    print("Writing")
    w.write("Hello World!")  # {"value": 1003, "checksum": 2})


# def initBasic(loop):
#     sensor_queue = asyncio.Queue()
#     command_queue = asyncio.Queue()
#     ac = partial(ArduinoConnection, sensor_queue, command_queue)
#     arduinoConnection = serial_asyncio.create_serial_connection(
#         loop, ac, "/dev/ttyS0", baudrate=115200
#     )
#     asyncio.ensure_future(arduinoConnection)

#     asyncio.ensure_future(processMessages(sensor_queue))

reset_arduino()

loop = asyncio.get_event_loop()

ac = SerialConnection(
    # readFormat=None,  # "<BH",
    # writeFormat="<HB",
    # writeKeys=["value", "checksum"],
    # readKeys=["checksum", "value2"],
    # loop=loop,
)


asyncio.ensure_future(processMessages(ac.readQueue))
asyncio.ensure_future(writeMessage(ac))


try:
    loop.run_forever()
finally:
    print("Exiting Event Loop")
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
