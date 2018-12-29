import aiounittest
import asyncio
from pirtcbot import RTCConnection
import logging


class TestRTCConnection(aiounittest.AsyncTestCase):
    async def test_basics(self):
        testmsg = "Testy mc test-test"
        c1 = RTCConnection()
        c2 = RTCConnection()

        q = asyncio.Queue()
        c2.onMessage(lambda c, m: q.put_nowait(m))

        offer = await c1.getLocalDescription()
        response = await c2.getLocalDescription(offer)
        await c1.setRemoteDescription(response)

        c1.send(testmsg)
        msg = await asyncio.wait_for(q.get(), 2)

        await c1.close()
        await c2.close()
        self.assertEqual(msg, testmsg)

