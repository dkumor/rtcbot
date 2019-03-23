import asyncio
import aiounittest
import threading
import time
from rtcbot.base import (
    SubscriptionConsumer,
    SubscriptionProducer,
    ThreadedSubscriptionConsumer,
    ThreadedSubscriptionProducer,
)


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
        # getTask = asyncio.create_task(c.get())
        getTask = asyncio.ensure_future(c.get())

        # Give time for the task to start
        await asyncio.sleep(0.01)

        c.put_nowait("Hi!")

        await getTask

        self.assertEqual(getTask.result(), "Hi!")

        c.put_nowait("Yo!")

        c.close()
        await c

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
        # getTask = asyncio.create_task(p.get())
        getTask = asyncio.ensure_future(p.get())

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

        p.unsubscribe()
        p.unsubscribe()

        p.close()

        await p


class TestThreadedClasses(aiounittest.AsyncTestCase):
    async def test_ThreadedConsumer(self):
        c = ThreadedSubscriptionConsumer()
        c.put_nowait("test")
        await c.onReady()
        self.assertEqual(c.ready, True)

        # Have to sleep to give asyncio time to prepare the data
        await asyncio.sleep(0.1)

        self.assertEqual(c.testQueue.get(), "test")

        # Now we test switching between subscriptions
        q = asyncio.Queue()
        q.put_nowait("heyy")

        c.putSubscription(q)

        await asyncio.sleep(0.01)
        self.assertEqual(c.testQueue.get(), "heyy")

        # Switch bask to the default
        c.put_nowait("yeehaw")
        await asyncio.sleep(0.01)
        self.assertEqual(c.testQueue.get(), "yeehaw")

        # wait 2 seconds to make sure the data timeout runs
        await asyncio.sleep(2)

        c.close()
        await asyncio.sleep(0.01)
        self.assertEqual(c.ready, False)
        self.assertEqual(c.testQueue.get(), "<<END>>")

    async def test_ThreadedProducer(self):
        p = ThreadedSubscriptionProducer()

        await p.onReady()
        self.assertEqual(p.ready, True)

        p.testQueue.put("test1")
        self.assertEqual(await p.get(), "test1")

        def pushsleep():
            # Work around the lask of a timeout in testing p
            time.sleep(0.1)
            p.testQueue.put("Ending")

        threading.Thread(target=pushsleep).run()

        p.close()
        await asyncio.sleep(0.01)

        self.assertEqual(p.ready, False)

        self.assertEqual(p.testResultQueue.get(), "<<END>>")

