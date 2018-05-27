import time
import os
import sys
import logging

import asyncio
import sanic
import json
from websockets.exceptions import ConnectionClosed

import serial.aio


app = sanic.Sanic(__name__)
app.static("/js", "./www/js")
app.static("/css", "./www/css")
app.static("/", "./www/index.html")

websocketlist = set()

defaultControls = {
    "power": 0,
    "steer": 0,
    "sleep": True
}


def prepareSensorData(data):
    return {
        "voltage": data[0] * 10 / 1024,
        "temperature": 0.78125 * data[1] - 67.84,
        "current": (data[2] - 505) * 5 / 1024 / 0.068,
        "current_motor": (data[3] * 5 / 1024 - 0.050) / 0.01,
        "accel_x": (data[4] - 338) * 1.5 / 338,
        "accel_y": (data[5] - 338) * 1.5 / 338,
        "accel_z": (data[6] - 338) * 1.5 / 338,
        "flt": 1 - data[7],
        "switch": data[8]
    }


def getControlString(data):
    pwm = int(abs(data["power"]) * 40)
    dir = int(data["power"] > 0)
    steer = int((data["steer"] + 1) / 2 * 92 + 50)
    slp = int(data["sleep"])
    return (str(pwm) + " " + str(dir) + " " + str(steer) + " " + str(slp) + "\n").encode()


serialCTRL = None


class SerialControl(asyncio.Protocol):

    def connection_made(self, transport):
        global serialCTRL
        self.transport = transport
        serialCTRL = transport
        self.currentbuffer = b""
        transport.serial.rts = False
        transport.write(getControlString(defaultControls))

    def data_received(self, data):
        self.currentbuffer += data
        if b"\r\n" in self.currentbuffer:
            s = self.currentbuffer.split(b"\r\n")
            self.currentbuffer = s[1]
            data = s[0].split(b",")
            for i in range(len(data)):
                data[i] = int(data[i])
            data = json.dumps(prepareSensorData(data))
            # Send it to all sockets

            loop = asyncio.get_event_loop()
            asyncio.ensure_future(
                asyncio.gather(*[ws.send(data) for ws in websocketlist]), loop=loop)

    def connection_lost(self, exc):
        print('port closed')
        asyncio.get_event_loop().stop()


@app.listener("before_server_start")
def init(s, loop):
    print("Startup baybee!")
    sc = serial.aio.create_serial_connection(
        loop, SerialControl, "/dev/ttyS0", 115200)
    loop.run_until_complete(sc)


@app.websocket("/ws")
async def control(request, ws):
    print("Opened ws", request, ws)
    websocketlist.add(ws)
    while True:
        try:
            serialCTRL.write(getControlString(json.loads(await ws.recv())))
        except:
            print("Websocket Closed")
            websocketlist.remove(ws)
            ws.close()
            break


app.run(host="0.0.0.0", port=8000)

# s = serial.Serial("/dev/ttyS0", 115200)

# s.write("START\n".encode())

# while True:
#   print(s.readline(), sep="")
