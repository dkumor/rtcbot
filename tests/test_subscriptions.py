import aiounittest
import asyncio
from rtcbot.subscriptions import RebatchSubscription
import logging
import numpy as np


class TestSubscriptions(aiounittest.AsyncTestCase):
    async def test_Rebatch(self):
        """
        Tests RebatchSubscription
        """
        s = RebatchSubscription(samples=1024, axis=1)
        s.put_nowait(np.zeros((2, 960)))
        s.put_nowait(np.ones((2, 960)))
        rebatched = await s.get()
        self.assertEqual(rebatched.shape, (2, 1024))
        self.assertTrue(np.all(rebatched[:, :960] == 0))
        self.assertTrue(np.all(rebatched[:, 960:] == 1))

        # 960 + 960 - 1024 = 896
        # 1024 - 896 = 128
        s.put_nowait(2 * np.ones((2, 128)))

        rebatched = await s.get()
        self.assertEqual(rebatched.shape, (2, 1024))
        self.assertTrue(np.all(rebatched[:, :896] == 1))
        self.assertTrue(np.all(rebatched[:, 896:] == 2))

        # Finally, make sure that it handles large batches too

        s.put_nowait(3 * np.ones((2, 1024 * 2)))
        rebatched = await s.get()
        self.assertEqual(rebatched.shape, (2, 1024))
        self.assertTrue(np.all(rebatched == 3))

        rebatched = await s.get()
        self.assertEqual(rebatched.shape, (2, 1024))
        self.assertTrue(np.all(rebatched == 3))

        # Finally, make sure that it passes correctly sized batches without any processing
        data = np.zeros((2, 1024))
        s.put_nowait(data)
        d2 = await s.get()

        # data==d2 does not check whether they are the same object. How tf do you do that?
        # this is a workaround:
        data[0, 0] = 1306
        self.assertTrue(d2[0, 0] == 1306)

