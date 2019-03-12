import aiounittest
import asyncio
from rtcbot import RTCConnection
import logging


class TestRTCConnection(aiounittest.AsyncTestCase):
    async def test_basic(self):
        """
        Creates a connection, and ensures that multiple messages go through
        in both directions.
        """
        testmsg1 = "Testy mc test-test"
        testmsg2 = "Hai wrld"

        c1 = RTCConnection()
        c2 = RTCConnection()

        q1 = c1.subscribe()
        q2 = c2.subscribe()

        offer = await c1.getLocalDescription()
        response = await c2.getLocalDescription(offer)
        await c1.setRemoteDescription(response)

        c1.put_nowait(testmsg1)
        c2.put_nowait(testmsg2)

        c1.send("OMG")  # Just to check
        c2.put_nowait("OMG2")

        msg1 = await asyncio.wait_for(q1.get(), 5)
        msg2 = await asyncio.wait_for(q2.get(), 5)

        self.assertEqual(msg1, testmsg2)
        self.assertEqual(msg2, testmsg1)

        msg1 = await asyncio.wait_for(q1.get(), 5)
        msg2 = await asyncio.wait_for(q2.get(), 5)

        self.assertEqual(msg1, "OMG2")
        self.assertEqual(msg2, "OMG")

        await c1.close()
        await c2.close()

    async def test_multipleDataChannels(self):
        c1 = RTCConnection()
        c2 = RTCConnection()

        dcs1 = c1.onDataChannel()
        dcs2 = c2.onDataChannel()

        # CONTINUE...
        await c1.close()
        await c2.close()
