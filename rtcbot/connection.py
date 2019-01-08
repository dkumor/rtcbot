
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
    AudioStreamTrack,
)
from av import VideoFrame, AudioFrame
from functools import partial

import numpy as np
import logging
import fractions
import time
import asyncio


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

            new_frame.pts = int(self._frameNumber * __VIDEO_CLOCKRATE / self._fps)

            if perfectFrameNumber + self._fps * 2 < self._frameNumber:
                # If the audio stream is over 2 seconds ahead, we wait 1 second before continuing
                self._log.debug(
                    "Stream is over 2 seconds ahead. Sleeping for 1 second."
                )
                await asyncio.sleep(1)

        return new_frame


class _AudioSender(AudioStreamTrack):
    def __init__(self, audioSubscription, sampleRate=48000, canSkip=True):
        super().__init__()
        self._log = logging.getLogger("AudioSender")
        self._audioSubscription = audioSubscription
        self._sampleRate = sampleRate
        self._startTime = None
        self._sampleNumber = 0
        self._canSkip = canSkip

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

        self._sampleNumber += data.shape[1]

        perfectSampleNumber = int((time.time() - self._startTime) * self._sampleRate)
        print(perfectSampleNumber - self._sampleNumber)
        if self._canSkip:

            if perfectSampleNumber - self._sampleRate * 1 > self._sampleNumber:
                # The audio is over 1 second behind where it is supposed to be.
                # Adjust the sample number to the ``corrected" version
                self._log.warn(
                    "Received audio is over 1 second behind optimal timestamp! Skipping audio forward! Use canSkip=False to disable this correction"
                )
                self._sampleNumber = perfectSampleNumber

        new_frame.pts = self._sampleNumber
        # print("SAMPLE NUMBER", self._sampleNumber, new_frame.samples, new_frame.layout)

        if perfectSampleNumber + self._sampleRate * 2 < self._sampleNumber:
            # If the audio stream is over 2 seconds ahead, we wait 1 second before continuing
            self._log.debug("Stream is over 2 seconds ahead. Sleeping for 1 second.")
            await asyncio.sleep(1)

        # self._log.info("RETURNING FRAMMEEE")
        return new_frame


class RTCConnection:
    """
    A very basic helper class to make initializing RTC connections easier
    """

    _log = logging.getLogger("rtcbot.RTCConnection")

    def __init__(self, onMessage=None, defaultOrdered=True):
        self._dataChannels = {}
        self._videoSubscription = None
        self._audioSubscription = None

        if onMessage:
            self._msgcallback = onMessage
        else:
            self._msgcallback = lambda channel, msg: None

        self._rtc = RTCPeerConnection()
        self._rtc.on("datachannel", self._onDatachannel)
        self._rtc.on("iceconnectionstatechange", self._onIceConnectionStateChange)
        self._rtc.on("track", self._onTrack)

        self._hasRemoteDescription = False
        self._defaultChannel = None
        self._defaultOrdered = defaultOrdered
        self.__queuedMessages = []

    async def getLocalDescription(self, description=None):
        """
        Gets the description to send on. Creates an initial description
        if no remote description was passed, and creates a response if
        a remote was given,
        """
        if self._hasRemoteDescription or description is not None:
            # This means that we received an offer - either the remote description
            # was already set, or we passed in a description. In either case,
            # instead of initializing a new connection, we prepare a response
            if not self._hasRemoteDescription:
                await self.setRemoteDescription(description)
            self._log.debug("Creating response to connection offer")
            answer = await self._rtc.createAnswer()
            await self._rtc.setLocalDescription(answer)
            return {
                "sdp": self._rtc.localDescription.sdp,
                "type": self._rtc.localDescription.type,
            }

        # There was no remote description, which means that we are initializing the
        # connection.

        # Before starting init, we create a default data channel for the connection
        self._log.debug("Setting up default data channel")
        self._defaultChannel = self._rtc.createDataChannel(
            "default", ordered=self._defaultOrdered
        )
        self._defaultChannel.on(
            "message", partial(self._onMessage, self._defaultChannel)
        )

        self._log.debug("Creating new connection offer")
        offer = await self._rtc.createOffer()
        await self._rtc.setLocalDescription(offer)
        return {
            "sdp": self._rtc.localDescription.sdp,
            "type": self._rtc.localDescription.type,
        }

    async def setRemoteDescription(self, description):
        self._log.debug("Setting remote connection description")
        await self._rtc.setRemoteDescription(RTCSessionDescription(**description))
        self._hasRemoteDescription = True

    def _onDatachannel(self, channel):
        """
        When a data channel comes in, adds it to the data channels, and sets up its messaging and stuff
        """
        self._log.debug("Got channel: %s", channel.label)
        channel.on("message", partial(self._onMessage, channel))

        if channel.label == "default":
            # Send any queued messages
            if len(self.__queuedMessages) > 0:
                self._log.debug("Sending queued messages")
                for m in self.__queuedMessages:
                    channel.send(m)
                self.__queuedMessages = []

            # Set the default channel
            self._defaultChannel = channel

        else:
            self._dataChannels[channel.label] = channel

    def _onIceConnectionStateChange(self):
        self._log.debug("RTC Connection State %s", self._rtc.iceConnectionState)

    def _onTrack(self, track):
        self._log.debug("Got track!")

    def _onMessage(self, channel, message):
        self._log.debug("Received message: (%s) %s", channel.label, message)
        self._msgcallback(channel, message)

    def onMessage(self, msgcallback):
        self._msgcallback = msgcallback

    def send(self, msg):
        self._log.debug("Sending message: %s", msg)
        if self._defaultChannel is not None:
            self._defaultChannel.send(msg)
        else:
            self._log.debug("Waiting for data channel before sending message")
            self.__queuedMessages.append(msg)

    async def close(self):
        self._log.debug("Closing connection")
        for chan in self._dataChannels:
            self._dataChannels[chan].close()
        if self._defaultChannel is not None:
            self._defaultChannel.close()
        await self._rtc.close()

    def addVideo(self, frameSubscription):
        """
        Add video to the connection. This should be called before `getLocalDescription` is
        called, so that the video stream is set up correctly.

        Accepts any object where `await frameSubscription.get()` returns a bgr opencv frame::
        
            cam = CVCamera()
            conn = RTCConnection()
            conn.addVideo(cam.subscribe())

        Note that if adding video when receiving a remote offer, the RTCConnection only adds the video
        stream if the remote connection explicitly requests a video stream. 

        The `get()` function will only be called if the video stream is requested, so it is possible to only start
        video capture on first call of `get()`.
        """
        self._rtc.addTrack(_VideoSender(frameSubscription))

    def addAudio(self, audioSubscription, sampleRate=48000):
        """
        Add audio to the connection. Just like the video subscription, `await audioSubscription.get()` should
        give a numpy array of raw audio samples, with the given sample rate, and given format.

        """
        self._rtc.addTrack(_AudioSender(audioSubscription, sampleRate=sampleRate))

    # @property
    # def video(self):
    #     """
    #     Returns whether or not the connection can accept a video stream.
    #     """

