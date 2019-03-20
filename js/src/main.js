import RTCConnection from "./connection.js";
import { Keyboard, Gamepad, setGamepadRate } from "./inputs.js";

export { RTCConnection, Keyboard, Gamepad, setGamepadRate };

export class Queue {
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
