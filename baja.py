import time

import os
import sys
import serial

import asyncio
import websockets

s = serial.Serial("/dev/ttyS0", 115200)

while True:
    print(s.readline(), sep="")
