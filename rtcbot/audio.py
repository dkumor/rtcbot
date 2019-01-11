import asyncio
import logging
import numpy as np

import soundcard as sc


from .base import ThreadedSubscriptionProducer, ThreadedSubscriptionConsumer


class Microphone(ThreadedSubscriptionProducer):
    """
    Reads microphone data, and writes audio output. This class allows you to
    output sound while reading it.

    Parameters
    ----------
    samplerate: int
        The sampling rate in Hz. 
    channels: {int, list(int)}, optional
        Mirrors the SoundCard `Microphone.recorder` API. 
        By default records on all available channels.
    blocksize: int
        Records this many samples at a time. A lower block size will give lower latency,
        and lower CPU usage.
    device: soundcard._Microphone
        The `soundcard` device to record from. Uses default if not specified.
    
    
    """

    _log = logging.getLogger("rtcbot.Microphone")

    def __init__(
        self, samplerate=48000, channels=None, blocksize=1024, device=None, loop=None
    ):
        if device is None:
            device = sc.default_microphone()
        self._device = device

        self._samplerate = samplerate
        self._channels = channels
        self._blocksize = blocksize

        super().__init__(defaultSubscriptionType=asyncio.Queue, logger=self._log)

    def _producer(self):

        self._log.debug("Using microphone %s", self._device)

        with self._device.recorder(
            samplerate=self._samplerate,
            channels=self._channels,
            blocksize=self._blocksize,
        ) as recorder:
            self._ready = True  # Set ready state
            while not self._shouldClose:
                try:
                    audioData = recorder.record(self._blocksize)
                    self._put_nowait(np.transpose(audioData))
                except:
                    self._log.exception("Error while trying to record audio")
        self._ready = False
        self._log.debug("Ended audio recording")


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
        self._log.debug("Using speaker %s", self._device)
        with self._device.player(
            samplerate=self._samplerate,
            channels=self._channels,
            blocksize=self._blocksize,
        ) as player:
            self._ready = True
            while not self._shouldClose:
                try:
                    data = self._get()
                    if data.ndim > 1:
                        # we have channelxsamples but want samplesxchannels
                        data = np.transpose(data)
                    player.play(data)
                except StopIteration:
                    break
                except:
                    self._log.exception("Error while trying to play audio")

    def play(self, data):
        """
        This is a direct API for playing an array of data. Queues up the array of data
        to play, and returns without blocking.

        Calls `soundcard._Player.play` in the backend. Cannot be used at the
        same time as playStream.


        """
        self.put_nowait(data)

    def playStream(self, stream):
        """
        Given a subscription to the audio stream, such that `await stream.get()` returns the
        raw audio data, plays the stream.
        """
        self.putSubscription(stream)

    def stop(self):
        """
        Stops playing currently playing audio. Forgets the currently playing stream, 
        and waits for new audio, which is passed through `play` or `playStream`
        """
        super().stop()

    def close(self):
        """
        Shuts down the speaker. 
        """
        super().close()
