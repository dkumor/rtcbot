"use strict";
/**
 * A class mirroring pirtcbot's RTCConnection to simplify setting up a bidirectional connection
 * between Python and the browser.
 */

class RTCConnection {
  constructor(
    onMessage = null,
    options = {
      iceServers: [{ urls: ["stun:stun.l.google.com:19302"] }]
    }
  ) {
    this._datachannels = {};

    this._rtc = new RTCPeerConnection(options);
    this._hasRemoteDescription = false;
  }

  async _waitForICECandidates() {
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
      // instead of initializing, we prepare a response
      if (!this._hasRemoteDescription) {
        await this.setRemoteDescription(description);
      }
      await this._waitForICECandidates();
      answer = await this._rtc.createAnswer();
      await this._rtc.setLocalDescription(answer);
      return {
        sdp: this._rtc.localDescription.sdp,
        type: this._rtc.localDescription.type
      };
    }

    // This means that we are the ones intializing the connection.
    // We get all the ways that the remote peer can connect to us, and return the
    // local description
    offer = await this._rtc.createOffer();
    await this._rtc.setLocalDescription(offer);
    // the python side does not support asynchronous ICE setup, so we wait until all ICE candidates are
    // ready before trying to connect
    await this._waitForICECandidates();
    return this._rtc.localDescription;
  }
  async setRemoteDescription(description) {
    await this._rtc.setRemoteDescription(description);
    this._hasRemoteDescription = true;
  }
}
