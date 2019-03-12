"use strict";

// We want the library to work in node too, but it doesn't contain webrtc!
// We therefore conditionally require wrtc.
const _RTCPeerConnection =
  typeof RTCPeerConnection != "undefined"
    ? RTCPeerConnection
    : require("wrtc").RTCPeerConnection;

class RTCConnection {
  /**
   * RTCConnection mirrors the Python RTCConnection in API. Whatever differences in functionality
   * that may exist can be considered bugs unless explictly documented as such.
   *
   * For detailed documentation, see the RTCConnection docs for Python.
   *
   * @param {*} defaultOrdered
   * @param {*} options
   */
  constructor(
    defaultOrdered = true,
    options = {
      iceServers: [{ urls: ["stun:stun.l.google.com:19302"] }]
    }
  ) {
    this._dataChannels = {};

    this._msgcallback = msg => console.log(msg);

    this._videocallback = null;
    this._audiocallback = null;

    this._rtc = new _RTCPeerConnection(options);
    this._rtc.ondatachannel = this._onDataChannel.bind(this);
    this._rtc.ontrack = this._onTrack.bind(this);

    this._hasRemoteDescription = false;
    this._defaultChannel = null;
    this._defaultOrdered = defaultOrdered;
    this.__queuedMessages = [];
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
      offerToReceiveVideo: this._videocallback != null,
      offerToReceiveAudio: this._audiocallback != null
    });
    await this._rtc.setLocalDescription(offer);
    // For simplicity of the API, we wait until all ICE candidates are
    // ready before trying to connect, instead of doing asynchronous signaling.
    await this._waitForICECandidates();
    return this._rtc.localDescription;
  }
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
    console.log("got track", track);
    switch (track.track.kind) {
      case "video":
        this._videocallback(track.streams[0]);
        break;
      case "audio":
        this._audiocallback(track.streams[0]);
        break;
      default:
        console.error("Could not recognize track!");
    }
  }
  _onMessage(channel, message) {
    //console.log("got message", message);
    this._msgcallback(message.data);
  }
  subscribe(callback) {
    this._msgcallback = callback;
  }
  onVideo(callback) {
    this._videocallback = callback;
  }
  onAudio(callback) {
    this._audiocallback = callback;
  }
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

class Queue {
  /**
   * A simple async queue. Useful for converting callbacks into async operations.
   * The API imitates Python's asyncio.Queue, making it easy to avoid callback hell
   */
  constructor() {
    this._waiting = [];
    this._enqueued = [];
  }
  put_nowait(elem) {
    this._enqueued.push(elem);
    if (this._waiting.length > 0) {
      this._waiting.shift()(this._enqueued.shift());
    }
  }

  async get() {
    if (this._enqueued.length > 0) {
      return this._enqueued.shift();
    }
    let tempthis = this;
    return new Promise(function(resolve, reject) {
      tempthis._waiting.push(resolve);
    });
  }
}

if (typeof module != "undefined") {
  // Make it a module for use in node.
  module.exports = { RTCConnection, Queue };
}
