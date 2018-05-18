import time

import os
import sys
import serial

import sanic

s = serial.Serial("/dev/ttyS0", 115200)

while True:
    print(s.readline(), sep="")
