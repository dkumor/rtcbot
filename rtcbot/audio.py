import asyncio
import logging
import numpy as np

import soundcard as sc


from .base import (
    ThreadedSubscriptionProducer,
    ThreadedSubscriptionConsumer,
    SubscriptionClosed,
)
from typing import Union, List


class Microphone(ThreadedSubscriptionProducer):
    """
    Reads microphone data, and writes audio output. This class allows you to
    output sound while reading it.

    Args:
        samplerate (int,optional): 
            The sampling rate in Hz. Default is 48000.
        channels (int,list(int),optional):
            The index of channel to record. 
            Allows a list of indices. Records on all available channels by default.
        blocksize (int,optional): 
            Records this many samples at a time. A lower block size will give lower latency,
            but higher CPU usage.
        device (:class:`soundcard._Microphone`):
            The :mod:`soundcard` device to record from. Uses default if not specified.
    
    
    """

    _log = logging.getLogger("rtcbot.Microphone")

    def __init__(
        self,
        samplerate: int = 48000,
        channels: Union[int, List[int]] = None,
        blocksize: int = 1024,
        device=None,
        loop=None,
    ):
        if device is None:
            device = sc.default_microphone()
        self._device = device

        self._samplerate = samplerate
        self._channels = channels
        self._blocksize = blocksize

        super().__init__(defaultSubscriptionType=asyncio.Queue, logger=self._log)

    def _producer(self):

        self._log.info("Using microphone %s", self._device)

        with self._device.recorder(
            samplerate=self._samplerate,
            channels=self._channels,
            blocksize=self._blocksize,
        ) as recorder:
            self._setReady(True)  # Set ready state
            while not self._shouldClose:
                try:
                    # TODO: Perhaps some way to time out this command if something froze?
                    audioData = recorder.record(self._blocksize)
                    self._put_nowait(np.transpose(audioData))
                except:
                    self._log.exception("Error while trying to record audio")
        self._setReady(False)
        self._log.info("Ended audio recording")


class Speaker(ThreadedSubscriptionConsumer):
    _log = logging.getLogger("rtcbot.Speaker")

    def __init__(
        self, samplerate=48000, channels=None, blocksize=1024, device=None, loop=None
    ):
        if device is None:
            device = sc.default_speaker()
        self._device = device

        self._samplerate = samplerate
        self._channels = channels
        self._blocksize = blocksize

        super().__init__(asyncio.Queue, logger=self._log)

    def _consumer(self):
        self._log.info("Using speaker %s", self._device)
        with self._device.player(
            samplerate=self._samplerate,
            channels=self._channels,
            blocksize=self._blocksize,
        ) as player:
            self._setReady(True)
            while not self._shouldClose:
                try:
                    data = self._get()
                    self._log.debug("Received sample shape %s", data.shape)
                    if data.ndim > 1:
                        # we have channelxsamples but want samplesxchannels
                        data = np.transpose(data)
                    player.play(data)
                except SubscriptionClosed:
                    break
                except:
                    self._log.exception("Error while trying to play audio")
        self._setReady(False)
        self._log.info("Ended audio playback")
