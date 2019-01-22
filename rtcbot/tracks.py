
from aiortc import VideoStreamTrack, AudioStreamTrack

from aiortc.mediastreams import (
    MediaStreamError,
    AUDIO_PTIME,
    VIDEO_CLOCK_RATE,
    VIDEO_TIME_BASE,
)
from av import VideoFrame, AudioFrame

import logging
import fractions
import time
import asyncio

import numpy as np
from .subscriptions import (
    RebatchSubscription,
    GetterSubscription,
    MostRecentSubscription,
)
from .base import BaseSubscriptionProducer, BaseSubscriptionConsumer, SubscriptionClosed


class _audioSenderTrack(AudioStreamTrack):
    """
    The AudioSender is unfortunately fairly complex, due to the packetization requirements of the
    audio stream. The underlying issue is that we are taking a very generic stream of data, where
    frames are of an arbitrary size, and come in whenever convenient, and converting it into a stream
    of data at 960 samples per frame.

    
    https://datatracker.ietf.org/doc/rfc7587/?include_text=1

    """

    _log = logging.getLogger("rtcbot.RTCConnection.AudioSender")

    def __init__(
        self, audioSubscription, sampleRate=48000, canSkip=True, startedCallback=None
    ):
        super().__init__()
        self._audioSubscription = RebatchSubscription(
            int(AUDIO_PTIME * sampleRate), axis=-1, subscription=audioSubscription
        )
        self._sampleRate = sampleRate
        self._startTime = None
        self._sampleNumber = 0
        self._canSkip = canSkip
        self._startedCallback = startedCallback

    async def recv(self):
        if self._startTime is None and self._startedCallback is not None:
            self._startedCallback()
        try:
            data = await self._audioSubscription.get()
        except SubscriptionClosed:
            self._log.debug(
                "Audio track finished. raising MediaStreamError to shut down connection"
            )
            self.stop()
            raise MediaStreamError
        except:
            self._log.exception("Got unknown error. Crashing video stream")
            self.stop()
            raise MediaStreamError

        # self._log.exception("FAIL")

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
        # print(perfectSampleNumber - self._sampleNumber)
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

        # print("\n\nSENDING DATA", new_frame, new_frame.time_base)
        self._log.debug("Writing frame %s", new_frame)
        return new_frame


class AudioSender(BaseSubscriptionConsumer):
    _log = logging.getLogger("rtcbot.RTCConnection.AudioSender")

    def __init__(self, sampleRate=48000, canSkip=True):
        super().__init__(logger=self._log)

        def readySetter():
            self._setReady(True)

        # The RTCConnection will take this object, and aiortc
        # will take it from here.
        self.audioStreamTrack = _audioSenderTrack(
            GetterSubscription(self._get),
            sampleRate=sampleRate,
            canSkip=canSkip,
            startedCallback=readySetter,
        )

    def close(self):
        # self.audioStreamTrack.stop()
        super().close()


class _videoSenderTrack(VideoStreamTrack):

    _log = logging.getLogger("rtcbot.RTCConnection.VideoSender")

    def __init__(self, frameSubscription, fps=None, canSkip=True, startedCallback=None):
        super().__init__()
        self._frameSubscription = frameSubscription

        self._startTime = None
        self._frameNumber = 0
        self._fps = fps
        self._canSkip = canSkip
        self._startedCallback = startedCallback

    async def recv(self):
        if self._startTime is None and self._startedCallback is not None:
            self._startedCallback()

        try:
            img = await self._frameSubscription.get()
        except SubscriptionClosed:
            self._log.debug(
                "Video track finished. raising MediaStreamError to shut down connection"
            )
            self.stop()
            raise MediaStreamError
        except:
            self._log.exception("Got unknown error. Crashing video stream")
            self.stop()
            raise MediaStreamError

        if self._startTime is None:
            self._startTime = time.time()

        new_frame = VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.time_base = VIDEO_TIME_BASE

        # https://en.wikipedia.org/wiki/Presentation_timestamp
        if self._fps is None:
            # We assume that the frames arrive as fast as they are created.
            new_frame.pts = int((time.time() - self._startTime) * VIDEO_CLOCK_RATE)
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

            new_frame.pts = int(self._frameNumber * VIDEO_CLOCK_RATE / self._fps)

            if perfectFrameNumber + self._fps * 2 < self._frameNumber:
                # If the audio stream is over 2 seconds ahead, we wait 1 second before continuing
                self._log.debug(
                    "Stream is over 2 seconds ahead. Sleeping for 1 second."
                )
                await asyncio.sleep(1)
        self._log.debug("Writing frame %s", new_frame)
        return new_frame


class VideoSender(BaseSubscriptionConsumer):
    _log = logging.getLogger("rtcbot.RTCConnection.VideoSender")

    def __init__(self, fps=None, canSkip=True):
        super().__init__(MostRecentSubscription, logger=self._log)

        def readySetter():
            self._setReady(True)

        # The RTCConnection will take this object, and aiortc
        # will take it from here.
        self.videoStreamTrack = _videoSenderTrack(
            GetterSubscription(self._get),
            fps=fps,
            canSkip=canSkip,
            startedCallback=readySetter,
        )

    def close(self):
        # self.videoStreamTrack.stop()
        super().close()


class AudioReceiver(BaseSubscriptionProducer):
    _log = logging.getLogger("rtcbot.RTCConnection.AudioReceiver")

    def __init__(self, track):
        super().__init__(asyncio.Queue, logger=self._log)
        self._track = track
        self._sampleRate = None

        asyncio.ensure_future(self._trackReceiver())

    async def _trackReceiver(self):
        try:
            audioFrame = await self._track.recv()
        except MediaStreamError:
            logging.exception("Error in the audio stream")
            self._track.stop()
            self.close()
            return

        self._sampleRate = audioFrame.sample_rate

        # Once we receive the first audio frame, we are ready
        self._setReady(True)
        while not self._shouldClose:
            # Decode the frame

            data = audioFrame.to_ndarray()

            # Now we reshape to get samples per channel, since to_ndarray returns one big array,
            # transpose to get channels*samples, and divide by 32768 to convert to float
            if data.dtype != np.int16:
                self._log.error(
                    "Incoming audio frame's data type unsupported: %s", audioFrame
                )
            else:
                data = (
                    np.transpose(np.reshape(data, (audioFrame.samples, -1))).astype(
                        np.float
                    )
                    / 32768
                )
                self._put_nowait(data)

            # Get the next frame
            try:
                audioFrame = await self._track.recv()
            except MediaStreamError:
                self._log.debug("Audio stream finished")
                self.close()
        self._log.info("Ending audio receiving")
        self._track.stop()


class VideoReceiver(BaseSubscriptionProducer):
    _log = logging.getLogger("rtcbot.RTCConnection.VideoReceiver")

    def __init__(self, track):
        super().__init__(MostRecentSubscription, logger=self._log)
        self._track = track

        asyncio.ensure_future(self._trackReceiver())

    async def _trackReceiver(self):
        try:
            videoFrame = await self._track.recv()
        except MediaStreamError:
            logging.exception("Error in the video stream")
            self._track.stop()
            self.close()
            return

        # Once we receive the first frame, we are ready
        self._setReady(True)
        while not self._shouldClose:

            # Decode the frame
            data = videoFrame.to_rgb().to_ndarray()
            data = data[..., ::-1]  # cv2.cvtColor(data, cv2.COLOR_RGB2BGR)
            self._log.debug("Received %s frame", data.shape)
            self._put_nowait(data)

            # Get the next frame
            try:
                videoFrame = await self._track.recv()
            except MediaStreamError:
                self._log.debug("Video stream finished")
                self.close()
        self._log.info("Ending video receiving")
        self._track.stop()
