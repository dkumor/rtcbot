
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError, AUDIO_PTIME
from av import VideoFrame, AudioFrame
from functools import partial

import numpy as np
import logging
import fractions
import time
import asyncio

from .tracks import VideoSender, AudioSender, AudioReceiver, VideoReceiver


class RTCConnection:
    """
    A very basic helper class to make initializing RTC connections easier
    """

    _log = logging.getLogger("rtcbot.RTCConnection")

    def __init__(self, onMessage=None, defaultOrdered=True):
        self._dataChannels = {}
        self._videoSubscription = None
        self._audioSubscription = None
        self._videoReceiver = None
        self._audioReceiver = None

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
        self._log.debug("Received %s track from connection", track.kind)
        if track.kind == "audio":
            self._audioReceiver = AudioReceiver(track)
            if self._audioSubscription is not None:
                self._audioSubscription(self._audioReceiver)
        elif track.kind == "video":
            self._videoReceiver = VideoReceiver(track)
            if self._videoSubscription is not None:
                self._videoSubscription(self._videoReceiver)

        else:
            self._log.error("Received unknown track type: %s", track.kind)

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

    def addVideo(self, frameSubscription=None, fps=None, canSkip=True):
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
        s = VideoSender(fps=fps, canSkip=True)
        if frameSubscription is not None:
            s.putSubscription(frameSubscription)
        self._rtc.addTrack(s.videoStreamTrack)
        return s

    def addAudio(self, audioSubscription=None, sampleRate=48000, canSkip=True):
        """
        Add audio to the connection. Just like the video subscription, `await audioSubscription.get()` should
        give a numpy array of raw audio samples, with the given sample rate, and given format.

        """
        s = AudioSender(sampleRate=sampleRate, canSkip=canSkip)
        if audioSubscription is not None:
            s.putSubscription(audioSubscription)
        self._rtc.addTrack(s.audioStreamTrack)
        return s

    def onAudio(self, callback):
        self._audioSubscription = callback

    def onVideo(self, callback):
        self._videoSubscription = callback

    # @property
    # def video(self):
    #     """
    #     Returns whether or not the connection can accept a video stream.
    #     """

