from aiortc import RTCPeerConnection, RTCSessionDescription
import asyncio
import logging
import json

from .base import (
    SubscriptionProducerConsumer,
    SubscriptionProducer,
    SubscriptionClosed,
    NoClosedSubscription,
)
from .tracks import VideoSender, AudioSender, AudioReceiver, VideoReceiver
from .subscriptions import MostRecentSubscription


class DataChannel(SubscriptionProducerConsumer):
    """
    Represents a data channel. You can put_nowait messages into it, 
    and subscribe to messages coming from it.

    """

    _log = logging.getLogger("rtcbot.RTCConnection.DataChannel")

    def __init__(self, rtcDataChannel, json=True):
        super().__init__(asyncio.Queue, asyncio.Queue, logger=self._log)
        self._rtcDataChannel = rtcDataChannel

        # Directly put messages
        self._rtcDataChannel.on("message", self._put_preprocess)
        self._json = json

        self._log.debug("READY STATE %s", self._rtcDataChannel.readyState)
        if self._rtcDataChannel.readyState == "open":
            # Make sure we pass messages forward
            asyncio.ensure_future(self._messageSender())
        else:
            self._log.debug("Waiting for channel to open")
            self._rtcDataChannel.on(
                "open", lambda: asyncio.ensure_future(self._messageSender())
            )

    async def _messageSender(self):
        self._log.debug("Channel open, ready to send")
        self._setReady(True)
        while not self._shouldClose:
            try:
                msg = await self._get()
                if self._json:
                    msg = json.dumps(msg)
                self._log.debug("Sending message %s", msg)
                self._rtcDataChannel.send(msg)
            except SubscriptionClosed:
                pass
                # The while loop should exit here
        self._log.debug("Stopping message sender")

    def _put_preprocess(self, data):
        self._log.debug("Received '%s'", data)
        if self._json:
            try:
                data = json.loads(data)
            except:
                self._log.debug("Failed to read json data %s", data)
        try:
            self._put_nowait(data)
        except:
            self._log.exception("Error in message handler")

    @property
    def name(self):
        return self._rtcDataChannel.label

    def close(self):
        # self._rtcDataChannel.close()
        super().close()


class ConnectionVideoHandler(SubscriptionProducerConsumer):
    """

    :Example:
        Allows usage of RTCConnection as follows::

            r = RTCConnection()
            frameSubscription = r.video.subscribe()

            r.video.putSubscription(frameSubscription)

    It uses the first incoming video stream for subscribe(),
    and creates a single outgoing video stream.

    Subscribing to the tracks can be done
    """

    _log = logging.getLogger("rtcbot.RTCConnection.ConnectionVideoHandler")

    def __init__(self, rtc):
        super().__init__(
            directPutSubscriptionType=MostRecentSubscription,
            defaultSubscriptionType=MostRecentSubscription,
            logger=self._log,
        )
        self._senders = set()
        self._receivers = set()

        self._defaultSender = None
        self._defaultReceiver = None

        # The defaultSender subscribes to this
        self._defaultSenderSubscription = NoClosedSubscription(self._get)

        self._trackSubscriber = SubscriptionProducer(
            logger=self._log.getChild("trackSubscriber")
        )

        self._rtc = rtc

        self._offerToReceive = False

    def onTrack(self, callback=None):
        """
        Callback that gets called each time a video track is received::

            @r.video.onTrack
            def onTrack(track):
                print(track)

        The callback actually works exactly as a subscribe(), so you can do::

            subscription = r.video.onTrack()
            await subscription.get()

        """
        return self._trackSubscriber.subscribe(callback)

    def addTrack(self, frameSubscription=None, fps=None, canSkip=True):
        """
        Allows to send multiple video tracks in a single connection.
        Each call to putTrack *adds* the track to the connection.
        For simple usage, where you only have a single video stream,
        just use `putSubscription` - it automatically calls putTrack for you.
        """
        self._log.debug("Adding video track to connection")
        s = VideoSender(fps=fps, canSkip=True)
        if frameSubscription is not None:
            s.putSubscription(frameSubscription)
        elif self._defaultSender is None:
            s.putSubscription(self._defaultSenderSubscription)
        if self._defaultSender is None:
            self._defaultSender = s
        self._rtc.addTrack(s.videoStreamTrack)
        self._senders.add(s)
        return s

    def putSubscription(self, subscription):

        # We need to make sure that when we put:
        # 1) there is an actual video track to put to!
        # 2) the track is subscribed to the VideoHandler
        super().putSubscription(subscription)
        if self._defaultSender is None:
            self.addTrack()
        # Make sure that this subscription is active on the default track
        self._defaultSender.putSubscription(self._defaultSenderSubscription)

    def _onTrack(self, track):
        """
        Internal raw track receiver
        """
        self._log.debug("Received video track from connection")
        track = VideoReceiver(track)
        if self._defaultReceiver is None:  # The default receiver track is the first one
            self._defaultReceiver = track
            self._defaultReceiver.subscribe(self._put_nowait)
        self._receivers.add(track)
        self._trackSubscriber._put_nowait(track)

    def close(self):
        for t in self._senders:
            t.close()
        for t in self._receivers:
            t.close()
        self._trackSubscriber.close()
        super().close()

    def offerToReceive(self):
        """
        This is called automatically on subscribe, but is also available
        just in case you want delay subscribing until later.
        """
        self._offerToReceive = True

    def subscribe(self, subscription=None):

        self.offerToReceive()
        return super().subscribe(subscription)


class ConnectionAudioHandler(SubscriptionProducerConsumer):
    """
    Allows usage of RTCConnection as follows::

        r = RTCConnection()
        audioSubscription = r.audio.subscribe()

        r.audio.putSubscription(audioSubscription)

    It uses the first incoming audio stream for subscribe(),
    and creates a single outgoing audio stream.

    Subscribing to the tracks can be done
    """

    _log = logging.getLogger("rtcbot.RTCConnection.ConnectionAudioHandler")

    def __init__(self, rtc):
        super().__init__(
            directPutSubscriptionType=asyncio.Queue,
            defaultSubscriptionType=asyncio.Queue,
            logger=self._log,
        )
        self._senders = set()
        self._receivers = set()

        self._defaultSender = None
        self._defaultReceiver = None

        # The defaultSender subscribes to this
        self._defaultSenderSubscription = NoClosedSubscription(self._get)

        self._trackSubscriber = SubscriptionProducer(
            logger=self._log.getChild("trackSubscriber")
        )

        self._rtc = rtc

        self._offerToReceive = False

    def onTrack(self, callback=None):
        """
        Callback that gets called each time a video track is received::

            @r.video.onTrack
            def onTrack(track):
                print(track)

        The callback actually works exactly as a subscribe(), so you can do::

            subscription = r.video.onTrack()
            await subscription.get()

        """
        return self._trackSubscriber.subscribe(callback)

    def addTrack(self, subscription=None, sampleRate=48000, canSkip=True):
        """
        Allows to send multiple video tracks in a single connection.
        Each call to putTrack *adds* the track to the connection.
        For simple usage, where you only have a single video stream,
        just use `putSubscription` - it automatically calls putTrack for you.
        """
        self._log.debug("Adding audio track to connection")
        s = AudioSender(sampleRate=sampleRate, canSkip=True)
        if subscription is not None:
            s.putSubscription(subscription)
        elif self._defaultSender is None:
            s.putSubscription(self._defaultSenderSubscription)
        if self._defaultSender is None:
            self._defaultSender = s

        self._rtc.addTrack(s.audioStreamTrack)
        self._senders.add(s)
        return s

    def putSubscription(self, subscription):

        # We need to make sure that when we put:
        # 1) there is an actual track to put to!
        # 2) the track is subscribed to the handler
        super().putSubscription(subscription)
        if self._defaultSender is None:
            self.addTrack()
        # Make sure that this subscription is active on the default track
        self._defaultSender.putSubscription(self._defaultSenderSubscription)

    def _onTrack(self, track):
        """
        Internal raw track receiver
        """
        self._log.debug("Received audio track from connection")
        track = AudioReceiver(track)
        if self._defaultReceiver is None:  # The default receiver track is the first one
            self._defaultReceiver = track
            self._defaultReceiver.subscribe(self._put_nowait)
        self._receivers.add(track)
        self._trackSubscriber._put_nowait(track)

    def close(self):
        for t in self._senders:
            t.close()
        for t in self._receivers:
            t.close()
        self._trackSubscriber.close()
        super().close()

    def offerToReceive(self):
        """
        This is called automatically on subscribe, but is also available
        just in case you want delay subscribing until later.
        """
        self._offerToReceive = True

    def subscribe(self, subscription=None):

        self.offerToReceive()
        return super().subscribe(subscription)


class RTCConnection(SubscriptionProducerConsumer):
    _log = logging.getLogger("rtcbot.RTCConnection")

    def __init__(self, defaultChannelOrdered=True, loop=None):
        super().__init__(
            directPutSubscriptionType=asyncio.Queue,
            defaultSubscriptionType=asyncio.Queue,
            logger=self._log,
        )
        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        self._dataChannels = {}

        # These allow us to easily signal when the given events happen
        self._dataChannelSubscriber = SubscriptionProducer(
            logger=self._log.getChild("dataChannelSubscriber")
        )

        self._rtc = RTCPeerConnection()
        self._rtc.on("datachannel", self._onDatachannel)
        # self._rtc.on("iceconnectionstatechange", self._onIceConnectionStateChange)
        self._rtc.on("track", self._onTrack)

        self._hasRemoteDescription = False
        self._defaultChannelOrdered = defaultChannelOrdered

        self._videoHandler = ConnectionVideoHandler(self._rtc)
        self._audioHandler = ConnectionAudioHandler(self._rtc)

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
            try:
                answer = await self._rtc.createAnswer()
            except AttributeError:
                self._log.exception(
                    "\n>>> Looks like the offer didn't include the necessary info to set up audio/video. See RTCConnection.video.offerToReceive(). <<<\n\n"
                )
                raise
            await self._rtc.setLocalDescription(answer)
            return {
                "sdp": self._rtc.localDescription.sdp,
                "type": self._rtc.localDescription.type,
            }

        # There was no remote description, which means that we are initializing the
        # connection.

        # Before starting init, we create a default data channel for the connection
        self._log.debug("Setting up default data channel")
        channel = DataChannel(
            self._rtc.createDataChannel("default", ordered=self._defaultChannelOrdered)
        )
        # Subscribe the default channel directly to our own inputs and outputs.
        # We have it listen to our own self._get, and write to our self._put_nowait
        channel.putSubscription(NoClosedSubscription(self._get))
        channel.subscribe(self._put_nowait)
        self._dataChannels[channel.name] = channel

        # Make sure we offer to receive video and audio if if isn't set up yet
        if len(self.video._senders) == 0 and self.video._offerToReceive:
            self._log.debug("Offering to receive video")
            self._rtc.addTransceiver("video", "recvonly")
        if len(self.audio._senders) == 0 and self.audio._offerToReceive:
            self._log.debug("Offering to receive audio")
            self._rtc.addTransceiver("audio", "recvonly")

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
        When a data channel comes in, adds it to the data channels, and sets up its messaging and stuff.

        """
        channel = DataChannel(channel)
        self._log.debug("Got channel: %s", channel.name)
        if channel.name == "default":
            # Subscribe the default channel directly to our own inputs and outputs.
            # We have it listen to our own self._get, and write to our self._put_nowait
            channel.putSubscription(NoClosedSubscription(self._get))
            channel.subscribe(self._put_nowait)

            # Set the default channel
            self._defaultChannel = channel

        else:
            self._dataChannelSubscriber.put_nowait(channel)
        self._dataChannels[channel.name] = channel

    def _onTrack(self, track):
        self._log.debug("Received %s track from connection", track.kind)
        if track.kind == "audio":
            self._audioHandler._onTrack(track)
        elif track.kind == "video":
            self._videoHandler._onTrack(track)

    def onDataChannel(self, callback=None):
        """
        Acts as a subscriber...
        """
        return self._dataChannelSubscriber.subscribe(callback)

    def addDataChannel(self, name, ordered=True):
        """
        Adds a data channel to the connection. Note that the RTCConnection adds a "default" channel
        automatically, which you can subscribe to directly.
        """
        self._log.debug("Adding data channel to connection")

        if name in self._dataChannels or name == "default":
            raise KeyError("Data channel %s already exists", name)

        dc = DataChannel(self._rtc.createDataChannel(name, ordered=ordered))
        self._dataChannels[name] = dc
        return dc

    def getDataChannel(self, name):
        """
        Returns the data channel with the given name. Please note that the "default" channel is considered special,
        and is not returned.
        """
        if name == "default":
            raise KeyError(
                "Default channel not available for 'get'. Use the RTCConnection's subscribe and put_nowait methods for access to it."
            )
        return self._dataChannels[name]

    @property
    def video(self):
        """
        Convenience function - you can subscribe to it to get video frames once they show up
        """
        return self._videoHandler

    @property
    def audio(self):
        """
        Convenience function - you can subscribe to it to get video frames once they show up
        """
        return self._audioHandler

    def close(self):
        """
        If the loop is running, returns a future that will close the connection. Otherwise, runs
        the loop temporarily to complete closing.
        """
        super().close()
        # And closes all tracks
        self.video.close()
        self.audio.close()

        for dc in self._dataChannels:
            self._dataChannels[dc].close()

        self._dataChannelSubscriber.close()

        if self._loop.is_running():
            self._log.debug("Loop is running - close will return a future!")
            return asyncio.ensure_future(self._rtc.close())
        else:
            self._loop.run_until_complete(self._rtc.close())
        return None

    def send(self, msg):
        """
        Send is an alias for put_nowait - makes it easier for people new to rtcbot to understand
        what is going on
        """
        self.put_nowait(msg)

