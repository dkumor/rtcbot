export default class Websocket {
  constructor(url) {
    this._subscription = console.log;
    this._ws = WebSocket(url);
    this._ws.onmessage = this._onMessage;
    this._ws.onopen = this._onopen;
    this._msgQueue = [];
  }

  _onMessage(msg) {
    this._subscription(msg);
  }
  _onopen() {
    console.log("opened websocket");
    for (let i = 0; i < this._msgQueue.length; i++) {
      this._ws.send(this._msgQueue[i]);
    }
    this._msgQueue = [];
  }
  put_nowait(msg) {
    if (typeof msg !== "string") {
      msg = JSON.stringify(msg);
    }
    if (this._ws.readyState != 1 || this._msgQueue.length > 0) {
      // The connection is not yet ready - add to the queue
      this._msgQueue.push(msg);
    } else {
      this._ws.send(msg);
    }
  }
  subscribe(s) {
    this._subscription = s;
  }
  close() {
    this._ws.close();
  }
}
