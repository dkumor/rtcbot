// We want the library to work in node too, but it doesn't contain webrtc!
// We therefore conditionally require wrtc.
const _RTCPeerConnection =
  typeof RTCPeerConnection != "undefined"
    ? RTCPeerConnection
    : require("wrtc").RTCPeerConnection;

class ConnectionStreamHandler {
  constructor(rtc) {
    this._callback = null;

    // The incoming and outgoing data streams
    this.incomingStream = null;
    this.outgoingStream = null;

    this._rtc = rtc;
    this._offerToReceive = false;
  }

  subscribe(f) {
    this._callback = f;

    // Since we subscribe to a video stream, we offer to receive one.
    this.offerToReceive();
  }

  putSubscription(track) {
    this.outgoingStream = track;
    this._rtc.addTrack(track);
  }

  offerToReceive() {
    this._offerToReceive = true;
  }

  _onTrack(track) {
    // This is the internal track receiver. Right now only supports a single incoming stream.
    this.incomingStream = track.streams[0];
    if (this._callback != null) {
      this._callback(track.streams[0]);
    }
  }
}

class RTCConnection {
  /**
   * RTCConnection mirrors the Python RTCConnection in API. Whatever differences in functionality
   * that may exist can be considered bugs unless explictly documented as such.
   *
   * For detailed documentation, see the RTCConnection docs for Python.
   *
   * @param {*} defaultOrdered
   * @param {*} rtcConfiguration is the configuration given to the RTC connection
   */
  constructor(
    defaultOrdered = true,
    rtcConfiguration = {
      iceServers: [{ urls: ["stun:stun.l.google.com:19302"] }]
    }
  ) {
    this._dataChannels = {};

    this._msgcallback = msg => console.log(msg);

    this._rtc = new _RTCPeerConnection(rtcConfiguration);
    this._rtc.ondatachannel = this._onDataChannel.bind(this);
    this._rtc.ontrack = this._onTrack.bind(this);

    /**
     * Just like in the Python version, the video element allows you to directly access video streams.
     * The following functions are available:
     *
     * - `subscribe()`: Unlike in Python, this is given a callback which is called *once*, when the stream
     *  is received.
     *
     *  .. code-block:: javascript
     *
     *    conn.video.subscribe(function(stream) {
     *      document.querySelector("video").srcObject = stream;
     *    });
     *
     * - `putSubscription()`: Allows to send a video stream:
     *
     *  .. code-block:: javascript
     *
     *    let streams = await navigator.mediaDevices.getUserMedia({audio: false, video: true});
     *    conn.video.putSubscription(streams.getVideoTracks()[0]);
     *
     *
     */
    this.video = new ConnectionStreamHandler(this._rtc);
    /**
     * The audio element allows you to directly access audio streams.
     * The following functions are available:
     *
     * - `subscribe()`: Unlike in Python, this is given a callback which is called *once*, when the stream
     *  is received.
     *
     *  .. code-block:: javascript
     *
     *    conn.audio.subscribe(function(stream) {
     *      document.querySelector("audio").srcObject = stream;
     *    });
     *
     * - `putSubscription()`: Allows to send a video stream:
     *
     *  .. code-block:: javascript
     *
     *    let streams = await navigator.mediaDevices.getUserMedia({audio: true, video: false});
     *    conn.audio.putSubscription(streams.getAudioTracks()[0]);
     *
     *
     */
    this.audio = new ConnectionStreamHandler(this._rtc);

    this._hasRemoteDescription = false;
    this._defaultChannel = null;
    this._defaultOrdered = defaultOrdered;
    this.__queuedMessages = [];

    // Bind the put_nowait method
    this.put_nowait = this.put_nowait.bind(this);
  }

  async _waitForICECandidates() {
    // https://muaz-khan.blogspot.com/2015/01/disable-ice-trickling.html
    const conn = this._rtc;
    // Waits until the connection has finished gathering ICE candidates
    await new Promise(function(resolve) {
      if (conn.iceGatheringState === "complete") {
        resolve();
      } else {
        function checkState() {
          if (conn.iceGatheringState === "complete") {
            conn.removeEventListener("icegatheringstatechange", checkState);
            resolve();
          }
        }
        conn.addEventListener("icegatheringstatechange", checkState);
      }
    });
  }
  /**
   * Sets up the connection. If no description is passed in, creates an initial description.
   * If a description is given, creates a response to it.
   * @param {*} description (optional)
   */
  async getLocalDescription(description = null) {
    /**
     * Gets the description
     */

    if (this._hasRemoteDescription || description != null) {
      // This means that we received an offer - either the remote description
      // was already set, or we were passed in a description. In either case,
      // instead of initializing a new connection, we prepare a response
      if (!this._hasRemoteDescription) {
        await this.setRemoteDescription(description);
      }
      let answer = await this._rtc.createAnswer();
      await this._rtc.setLocalDescription(answer);
      await this._waitForICECandidates();
      return {
        sdp: this._rtc.localDescription.sdp,
        type: this._rtc.localDescription.type
      };
    }

    // There was no remote description, which means that we are intitializing
    // the connection.

    // Before starting init, we create a default data channel for the connection
    this._defaultChannel = this._rtc.createDataChannel("default", {
      ordered: this._defaultOrdered
    });
    this._defaultChannel.onmessage = this._onMessage.bind(
      this,
      this._defaultChannel
    );
    this._defaultChannel.onopen = this._sendQueuedMessages.bind(this);

    let offer = await this._rtc.createOffer({
      offerToReceiveVideo: this.video._offerToReceive,
      offerToReceiveAudio: this.audio._offerToReceive
    });
    await this._rtc.setLocalDescription(offer);
    // For simplicity of the API, we wait until all ICE candidates are
    // ready before trying to connect, instead of doing asynchronous signaling.
    await this._waitForICECandidates();
    return this._rtc.localDescription;
  }
  /**
   * When initializing a connection, this response reads the remote response to an initial
   * description.
   * 
   * @param {*} description
   */
  async setRemoteDescription(description) {
    await this._rtc.setRemoteDescription(description);
    this._hasRemoteDescription = true;
  }

  _sendQueuedMessages() {
    //console.log("sending queued messages", this.__queuedMessages);
    if (this.__queuedMessages.length > 0) {
      for (let i = 0; i < this.__queuedMessages.length; i++) {
        //console.log("Sending", this.__queuedMessages[i]);
        this._defaultChannel.send(this.__queuedMessages[i]);
      }
      this.__queuedMessages = [];
    }
  }

  _onDataChannel(channel) {
    console.log(channel);
    channel = channel.channel;
    channel.onmessage = this._onMessage.bind(this, channel);
    if (channel.label == "default") {
      //console.log("Got default channel");
      this._defaultChannel = channel;
      channel.onopen = () => this._sendQueuedMessages();
    } else {
      channel.onopen = () => (this._dataChannels[channel.label] = channel);
    }
  }
  _onTrack(track) {
    //console.log("got track", track);
    switch (track.track.kind) {
      case "video":
        this.video._onTrack(track);
        break;
      case "audio":
        this.audio._onTrack(track);
        break;
      default:
        console.error("Could not recognize track!");
    }
  }
  _onMessage(channel, message) {
    //console.log("got message", message);
    this._msgcallback(message.data);
  }
  /**
   * Subscribe to incoming messages. Unlike in the Python libary, which can accept
   * a wide variety of inputs, the `subscribe` function in javascript only allows simple
   * callbacks.
   *
   * @param {*} s A function to call each time a new message comes in
   */
  subscribe(callback) {
    this._msgcallback = callback;
  }
  /**
   * Send the given data over a data stream.
   *
   * @param {*} msg - Message to send
   */
  put_nowait(msg) {
    if (typeof msg !== "string") {
      msg = JSON.stringify(msg);
    }
    if (
      this._defaultChannel != null &&
      this._defaultChannel.readyState == "open" &&
      this.__queuedMessages.length == 0
    ) {
      //console.log("Sending directly");
      this._defaultChannel.send(msg);
    } else {
      //console.log("queueing");
      this.__queuedMessages.push(msg);
    }
  }
  /**
   * Close the connection
   */
  async close() {
    for (let chan in this._dataChannels) {
      chan.close();
    }
    if (this._defaultChannel != null) {
      this._defaultChannel.close();
    }
    await this._rtc.close();
  }
}

// Can't put the export above because sphinx-jsdoc does not understand it.
export default RTCConnection;
