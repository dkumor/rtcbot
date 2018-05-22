import time

import os
import sys
import serial

import sanic

s = serial.Serial("/dev/ttyS0", 115200)

s.write("START\n".encode())

while True:
    print(s.readline(), sep="")
