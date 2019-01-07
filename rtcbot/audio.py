import threading
import asyncio
import logging

import soundcard as sc

from .subscriptions import BaseSubscriptionHandler


def listMicrophones():
    return [device for device in sd.query_devices() if device["max_input_channels"] > 0]


def listSpeakers():
    return [
        device for device in sd.query_devices() if device["max_output_channels"] > 0
    ]


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

    def __init__(
        self, samplerate=48000, channels=None, blocksize=1024, device=None, loop=None
    ):
        super().__init__(asyncio.Queue)

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

    def _recordingWorker(self):
        log = logging.getLogger("rtcbot.Microphone")

        log.debug("Using microphone %s", self._device)

        with self._device.recorder(
            samplerate=self._samplerate,
            channels=self._channels,
            blocksize=self._blocksize,
        ) as recorder:
            while not self._shouldCloseWorkerThread:
                audioData = recorder.record(self._blocksize)
                self._loop.call_soon_threadsafe(self._put_nowait, audioData)
        log.debug("Ended audio recording")

    def close(self):
        """
        Closes microphone recording
        """
        self._shouldCloseWorkerThread = True
        self._workerThread.join()


class Speaker:
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

        self._stream = None
        self._directPlayStream = asyncio.Queue()

        self._futureLock = threading.Lock()
        self._dataFuture = None

        self._workerThread = threading.Thread(target=self._recordingWorker)
        self._workerThread.daemon = True
        self._workerThread.start()

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
                    data = self._dataFuture.result(timeout=1)
                except asyncio.concurrent.futures.TimeoutError:
                    log.debug("Did not get audio for 1 second...")
                except asyncio.concurrent.futures.CancelledError:
                    log.debug("Subscription data stream cancelled.")
                else:
                    if data is not None:
                        player.play(data)

    def play(self, data):
        """
        This is a direct API for playing an array of data. Queues up the array of data
        to play, and returns without blocking.

        Calls `soundcard._Player.play` in the backend. Cannot be used at the
        same time as playStream.
        """

        self._directPlayStream.put_nowait(data)
        if self._stream != self._directPlayStream:
            self.playStream(self._directPlayStream)

    def playStream(self, stream):
        """
        Given a subscription to the audio stream, such that `await stream.get()` returns the
        raw audio data, plays the stream.
        """
        with self._futureLock:
            self._stream = stream
            if not self._dataFuture.done():
                self._dataFuture.cancel()

    def close(self):
        """
        Stops playing audio.
        """
        self._shouldCloseWorkerThread = True
        self._workerThread.join()
