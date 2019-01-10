
from aiortc import VideoStreamTrack, AudioStreamTrack

from aiortc.mediastreams import MediaStreamError, AUDIO_PTIME
from av import VideoFrame, AudioFrame

import logging
import fractions
import time
import asyncio

import numpy as np
from .subscriptions import RebatchSubscription
from .base import BaseSubscriptionProducer


class AudioReceiver(BaseSubscriptionProducer):
    def __init__(self, stream, sampleRate=48000):
        super().__init__(asyncio.Queue)


class _VideoSender(VideoStreamTrack):
    # https://en.wikipedia.org/wiki/Presentation_timestamp
    # It appears that 90k is a standard clock rate for video frames.
    __VIDEO_CLOCKRATE = 90000
    __VIDEO_TIME_BASE = fractions.Fraction(1, __VIDEO_CLOCKRATE)

    def __init__(self, frameSubscription, fps=None, canSkip=True):
        super().__init__()
        self._log = logging.getLogger("VideoSender")
        self._frameSubscription = frameSubscription

        self._startTime = None
        self._frameNumber = 0
        self._fps = fps
        self._canSkip = canSkip

    async def recv(self):
        img = await self._frameSubscription.get()
        self._log.info("VIDEO")

        if self._startTime is None:
            self._startTime = time.time()

        new_frame = VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.time_base = self.__VIDEO_TIME_BASE

        # https://en.wikipedia.org/wiki/Presentation_timestamp
        if self._fps is None:
            # We assume that the frames arrive as fast as they are created.
            new_frame.pts = int(
                (time.time() - self._startTime) * self.__VIDEO_CLOCKRATE
            )
        else:
            # We have a target frame rate. Here, we do something similar to the audioSubscription
            self._frameNumber += 1

            perfectFrameNumber = int((time.time() - self._startTime) * self._fps)

            if self._canSkip:
                if perfectFrameNumber - self._fps * 1 > self._frameNumber:
                    self._log.warn(
                        "Received video frame is over 1 second behind optimal timestamp! Skipping frame forward! Use canSkip=False to disable this correction"
                    )
                self._frameNumber = perfectFrameNumber

            new_frame.pts = int(self._frameNumber * self.__VIDEO_CLOCKRATE / self._fps)

            if perfectFrameNumber + self._fps * 2 < self._frameNumber:
                # If the audio stream is over 2 seconds ahead, we wait 1 second before continuing
                self._log.debug(
                    "Stream is over 2 seconds ahead. Sleeping for 1 second."
                )
                await asyncio.sleep(1)

        return new_frame


class _AudioSender(AudioStreamTrack):
    """
    The AudioSender is unfortunately fairly complex, due to the packetization requirements of the
    audio stream. The underlying issue is that we are taking a very generic stream of data, where
    frames are of an arbitrary size, and come in whenever convenient, and converting it into a stream
    of data at 960 samples per frame.

    
    https://datatracker.ietf.org/doc/rfc7587/?include_text=1

    """

    def __init__(self, audioSubscription, sampleRate=48000, canSkip=True):
        super().__init__()
        self._log = logging.getLogger("AudioSender")
        self._audioSubscription = RebatchSubscription(
            int(AUDIO_PTIME * sampleRate), axis=-1, subscription=audioSubscription
        )
        self._sampleRate = sampleRate
        self._startTime = None
        self._sampleNumber = 0
        self._canSkip = canSkip
        self._sampleBuffer = None
        self._sampleBufferSamples = 0

    async def recv(self):
        self._log.info("IM AUDIOOOOOO")

        try:
            data = await self._audioSubscription.get()
        except:
            self._log.exception("Failed to get audio data")

        # self._log.info("GOT AUDIO %d,%d", data.shape[0], data.shape[1])

        # self._log.info("Creating FRAME")
        # https://trac.ffmpeg.org/wiki/audio%20types
        # https://github.com/mikeboers/PyAV/blob/develop/av/audio/frame.pyx
        # https://ffmpeg.org/doxygen/3.0/group__channel__mask__c.html
        #
        # It looks like at the time of writing, audio samples are only accepted as s16,
        # and not as float (flt) in aiortc. We therefore use s16 as format instead of flt,
        # and convert the data:
        # https://github.com/jlaine/aiortc/blob/master/aiortc/codecs/opus.py
        # We therefore force a conversion to 16 bit integer:

        data = (np.clip(data, -1, 1) * 32768).astype(np.int16)

        new_frame = AudioFrame.from_ndarray(
            data, format="s16", layout=str(data.shape[0]) + "c"
        )

        # Use the sample rate for the base clock
        new_frame.sample_rate = self._sampleRate
        new_frame.time_base = fractions.Fraction(1, self._sampleRate)

        if self._startTime is None:
            self._startTime = time.time()
        # We need to compute the timestamp of the frame.
        # We want to handle audio without skips, where we simply increase the clock according
        # to the samples. However, sometimes the data might come in a bit late, which would
        # mean that we still want to get it correctly.
        # However, we have no guarantee that the data is actually coming without skipped
        # points. We try to detect if the data coming seems to be way behind the current
        # perfect timestamp, and in that situation, we can decide to skip forward if canSkip is True
        # https://en.wikipedia.org/wiki/Presentation_timestamp
        # Since our clock rate is simply our sample rate, the timestamp is the number of samples
        # we should have seen so far

        new_frame.pts = self._sampleNumber
        self._sampleNumber += data.shape[1]

        perfectSampleNumber = (
            int((time.time() - self._startTime) * self._sampleRate) + data.shape[1]
        )
        print(perfectSampleNumber - self._sampleNumber)
        if self._canSkip:

            if perfectSampleNumber - self._sampleRate * 1 > self._sampleNumber:
                # The audio is over 1 second behind where it is supposed to be.
                # Adjust the sample number to the ``corrected" version
                self._log.warn(
                    "Received audio is over 1 second behind optimal timestamp! Skipping audio forward! Use canSkip=False to disable this correction"
                )
                new_frame.pts = perfectSampleNumber - data.shape[1]

        if perfectSampleNumber + self._sampleRate * 2 < self._sampleNumber:
            # If the audio stream is over 2 seconds ahead, we wait 1 second before continuing
            self._log.debug("Stream is over 2 seconds ahead. Sleeping for 1 second.")
            await asyncio.sleep(1)

        # self._log.info("RETURNING FRAMMEEE")
        print("\n\nSENDING DATA", new_frame, new_frame.time_base)
        return new_frame


async def trackEater(track):
    print("got track, and started looop!!", track.kind)
    while True:
        try:
            data = await track.recv()
        except MediaStreamError:
            logging.exception("FUUCK MEEEEEEEEE\n\n\n")
        print("\n\nRECEIVED TRACK DATA:", data, data.time_base)


class AudioSender:
    def __init__(self):
        pass
