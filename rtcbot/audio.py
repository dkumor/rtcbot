import threading
import asyncio
import logging
import numpy as np

import soundcard as sc

from .subscriptions import BaseSubscriptionHandler


class Microphone(BaseSubscriptionHandler):
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
        super().__init__(asyncio.Queue, self._log)

        if device is None:
            device = sc.default_microphone()
        self._device = device

        self._samplerate = samplerate
        self._channels = channels
        self._blocksize = blocksize

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        self._workerThread = threading.Thread(target=self._recordingWorker)
        self._workerThread.daemon = True
        self._workerThread.start()
        self._shouldCloseWorkerThread = False

    def _recordingWorker(self):

        self._log.debug("Using microphone %s", self._device)

        with self._device.recorder(
            samplerate=self._samplerate,
            channels=self._channels,
            blocksize=self._blocksize,
        ) as recorder:
            while not self._shouldCloseWorkerThread:
                audioData = recorder.record(self._blocksize)
                self._loop.call_soon_threadsafe(
                    self._put_nowait, np.transpose(audioData)
                )
        self._log.debug("Ended audio recording")

    def close(self):
        """
        Closes microphone recording
        """
        self._shouldCloseWorkerThread = True
        self._workerThread.join()


class Speaker:
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

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        # This is the stream used when play() is called
        self._directPlayStream = asyncio.Queue()
        # This is the general stream that is currently being played.
        self._stream = self._directPlayStream  # Start out with the play stream active

        self._futureLock = threading.Lock()
        self._dataFuture = None

        self._workerThread = threading.Thread(target=self._playingWorker)
        self._workerThread.daemon = True
        self._workerThread.start()
        self._shouldCloseWorkerThread = False

    def _playingWorker(self):
        log = logging.getLogger("rtcbot.Speaker")

        log.debug("Using speaker %s", self._device)
        with self._device.player(
            samplerate=self._samplerate,
            channels=self._channels,
            blocksize=self._blocksize,
        ) as player:
            while not self._shouldCloseWorkerThread:
                # get data
                with self._futureLock:
                    self._dataFuture = asyncio.run_coroutine_threadsafe(
                        self._stream.get(), self._loop
                    )
                try:
                    data = self._dataFuture.result(timeout=5)
                except asyncio.TimeoutError:
                    log.debug("Did not get audio for 5 seconds...")
                except asyncio.CancelledError:
                    log.debug("Subscription existing data stream cancelled.")
                else:
                    if data is not None:
                        if data.ndim > 1:
                            data = np.transpose(
                                data
                            )  # we have channelxsamples but want samplesxchannels
                        player.play(data)

    def play(self, data):
        """
        This is a direct API for playing an array of data. Queues up the array of data
        to play, and returns without blocking.

        Calls `soundcard._Player.play` in the backend. Cannot be used at the
        same time as playStream.
        """
        self._log.debug("Playing given data using stream %s", self._directPlayStream)
        self._directPlayStream.put_nowait(data)
        if self._stream != self._directPlayStream:
            self.playStream(self._directPlayStream)

    def playStream(self, stream):
        """
        Given a subscription to the audio stream, such that `await stream.get()` returns the
        raw audio data, plays the stream.
        """
        self._log.debug("Playing new stream: %s", stream)
        with self._futureLock:
            self._stream = stream
            if self._dataFuture is not None and not self._dataFuture.done():
                self._dataFuture.cancel()

    def stop(self):
        """
        Stops playing currently playing audio. Forgets the currently playing stream, 
        and waits for new audio, which is passed through `play` or `playStream`
        """
        # Clear the queue by creating a new one
        self._directPlayStream = asyncio.Queue()
        self._log.debug("stop: Created new empty stream %s", self._directPlayStream)
        self.playStream(self._directPlayStream)  # Play the empty queue

    def close(self):
        """
        Shuts down the speaker. 
        """
        self._shouldCloseWorkerThread = True
        with self._futureLock:
            if self._dataFuture is not None and not self._dataFuture.done():
                self._dataFuture.cancel()
        self._workerThread.join()
