import asyncio
import aiounittest
from rtcbot.base import SubscriptionConsumer, SubscriptionProducer


class TestBaseClasses(aiounittest.AsyncTestCase):
    async def test_SubscriptionConsumer(self):
        c = SubscriptionConsumer(asyncio.Queue)

        c.put_nowait("test")

        self.assertEqual(await c.get(), "test")

        q = asyncio.Queue()
        q.put_nowait("yay")
        c.putSubscription(q)

        self.assertEqual(await c.get(), "yay")

        # Now test cancellation - the current subscription is q.
        # we will switch to the default one
        getTask = asyncio.create_task(c.get())

        c.put_nowait("Hi!")

        await getTask

        self.assertEqual(getTask.result(), "Hi!")

        c.put_nowait("Yo!")

        c.close()

    async def test_SubscriptionProducer(self):
        p = SubscriptionProducer(asyncio.Queue, defaultAutosubscribe=True)

        # Nothing subscribed
        p.put_nowait("1")

        # DefaultAutosubscribe subscribes default during creation
        self.assertEqual(await p.get(), "1")

        q1 = p.subscribe()
        q2 = p.subscribe()

        p.put_nowait("2")

        self.assertEqual(await p.get(), "2")
        self.assertEqual(await q1.get(), "2")
        self.assertEqual(await q2.get(), "2")

        # Unsubscribe should stop it receiving updates
        p.unsubscribe(q2)

        p.put_nowait("3")

        q2.put_nowait(12)

        self.assertEqual(await p.get(), "3")
        self.assertEqual(await q1.get(), "3")
        self.assertEqual(await q2.get(), 12)

        p.unsubscribe()

        p.put_nowait("4")

        # The default is recreated here
        getTask = asyncio.create_task(p.get())

        # Give time for the task to start
        await asyncio.sleep(0.01)
        p.put_nowait("5")

        await getTask
        self.assertEqual(getTask.result(), "5")
        self.assertEqual(await q1.get(), "4")
        self.assertEqual(await q1.get(), "5")

        p.unsubscribeAll()
        p.put_nowait("6")
        q1.put_nowait(8)

        self.assertEqual(await q1.get(), 8)

        p.close()

