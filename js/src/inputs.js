/**
 * Keyboard subscribes to keypresses
 */
class Keyboard {
  constructor() {
    this._de = this._downEvent.bind(this);
    this._ue = this._upEvent.bind(this);
    window.addEventListener("keydown", this._de);
    window.addEventListener("keyup", this._ue);
    this._subscription = console.log;
  }
  _downEvent(e) {
    if (!e.repeat) {
      this._subscription({
        type: e.type,
        altKey: e.altKey,
        shiftKey: e.shiftKey,
        keyCode: e.keyCode,
        key: e.key,
        timestamp: e.timestamp
      });
    }
    e.preventDefault();
  }
  _upEvent(e) {
    this._subscription({
      type: e.type,
      altKey: e.altKey,
      shiftKey: e.shiftKey,
      keyCode: e.keyCode,
      key: e.key,
      timestamp: e.timestamp
    });
    e.preventDefault();
  }
  subscribe(s) {
    this._subscription = s;
  }
  close() {
    window.removeEventListener("keydown", this._de);
    window.removeEventListener("keyup", this._ue);
  }
}

/**
 * The gamepad API is pretty weird - we use a global handler loop to get data from all gamepads at once
 */
class GamepadHandler {
  constructor() {
    // The active gamepads
    this._gamepads = [];
    this._prev = []; // Previous gamepad state
    this._interval = null;
    this._mswait = 100;
  }
  loop() {
    let cur = navigator.getGamepads();
    let len = cur.length;
    if (this._gamepads.length < len) {
      len = this._gamepads.length;
    }
    if (this._prev.length < len) {
      len = this._prev.length;
    }
    //console.log(len, this._prev, cur, this._gamepads);
    for (let i = 0; i < len; i++) {
      if (
        this._prev[i] != null &&
        this._gamepads[i] != null &&
        cur[i] != null
      ) {
        // All 3 exist, so we can compare, and send events.

        // Set the full gamepad state
        this._gamepads[i].state = cur[i];

        for (let j = 0; j < cur[i].buttons.length; j++) {
          if (this._prev[i].buttons[j].pressed != cur[i].buttons[j].pressed) {
            this._gamepads[i]._subscription({
              value: cur[i].buttons[j].pressed,
              type: "btn" + j.toString()
            });
          }
        }
        for (let j = 0; j < cur[i].axes.length; j++) {
          if (this._prev[i].axes[j] != cur[i].axes[j]) {
            this._gamepads[i]._subscription({
              value: cur[i].axes[j],
              type: "axis" + j.toString()
            });
          }
        }
      }
    }
    this._prev = cur;
  }
  init() {
    let shouldLoop = false;
    for (let i = 0; i < this._gamepads.length; i++) {
      if (this._gamepads[i] != null) {
        shouldLoop = true;
        break;
      }
    }
    if (shouldLoop && this._interval == null) {
      //console.log("Starting gamepad loop");
      this._interval = setInterval(this.loop.bind(this), this._mswait);
    } else if (!shouldLoop && this._interval != null) {
      //console.log("Stopping gamepad loop");
      clearInterval(this._interval);
      this._interval = null;
    }
  }
  addGamepad(gp) {
    // Takes the first null spot, or adds to the end
    for (let i = 0; i < this._gamepads.length; i++) {
      if (this._gamepads[i] == null) {
        this._gamepads[i] = gp;
        this.init();
        return;
      }
    }
    this._gamepads.push(gp);
    this.init();
  }
  removeGamepad(gp) {
    for (let i = 0; i < this._gamepads.length; i++) {
      if (gp == this._gamepads[i]) {
        this._gamepads[i] = null;
        return;
      }
    }
  }
}

var gamepadHandler = new GamepadHandler();

/**
 * Gamepads are polled at 10Hz by default, so that when moving joystick axes
 * a connection is not immeidately flooded with every miniscule joystick change.
 * To modify this behavior, you can set the rate in Hz, allowing lower latency,
 * with the downside of potentially lots of data suddenly overwhelming a connection.
 *
 * @param {number} rate Rate at which gamepad is polled in Hz
 */
function setGamepadRate(rate) {
  gamepadHandler._mswait = Math.round(1000 / rate);
  if (gamepadHandler._interval != null) {
    // If it is already running, reset it
    clearInterval(gamepadHandler._interval);
    gamepadHandler._interval = null;
  }
  gamepadHandler.init();
}

/**
 * Gamepad allows you to control a game pad
 */
class Gamepad {
  constructor() {
    this._subscription = console.log;
    gamepadHandler.addGamepad(this);

    this.state = null;
  }
  subscribe(s) {
    this._subscription = s;
  }
  close() {
    gamepadHandler.removeGamepad(this);
  }
}

export { Keyboard, Gamepad, setGamepadRate };
