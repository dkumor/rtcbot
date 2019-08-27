import RTCConnection from "./connection.js";
import Websocket from "./websocket.js";
import { Keyboard, Gamepad, setGamepadRate } from "./inputs.js";

export { RTCConnection, Websocket, Keyboard, Gamepad, setGamepadRate };

export class Queue {
  /**
   * A simple async queue. Useful for converting callbacks into async operations.
   * The API imitates Python's asyncio.Queue, making it easy to avoid callback hell
   */
  constructor() {
    this._waiting = [];
    this._enqueued = [];
  }
  /**
   * Works just like in Python - you put an element on here, and await get to retrieve it
   * @param {*} elem
   */
  put_nowait(elem) {
    this._enqueued.push(elem);
    if (this._waiting.length > 0) {
      this._waiting.shift()(this._enqueued.shift());
    }
  }
  /**
   * get is a coroutine, to be used with await - it returns elements one at a time.
   */
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
