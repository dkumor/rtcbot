import pynmea2

from .arduino import SerialConnection

class GPSConnection:
    def __init__(self,url="/dev/ttyACM0",baudrate=9600,subscription=None):
        self.serial = SerialConnection(url=url,baudrate=baudrate)
    async def get(self):
        data = await self.serial.readQueue.get()
        return pynmea2.parse(data.decode('ascii'))

if __name__=="__main__":
    import asyncio
    c = GPSConnection()
    async def getData(conn):
        while True:
            msg = await conn.get()
            print(msg.latitude,msg.longitude)

    asyncio.ensure_future(getData(c))

    asyncio.get_event_loop().run_forever()

