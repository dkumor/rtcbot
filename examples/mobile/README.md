# Connecting over 4G

Thus far, the tutorials have all had you connect directly to the robot, which meant that it had to be on your local wifi network. In this tutorial, we will finally decouple the server and the robot.

Rather than connecting to the robot, we will have two separate Python programs. The first is a server, which will be served at a known IP address. The second will be the robot, which connects to the server with a websocket, and waits for the information necessary to initialize a WebRTC connection directly to your browser.

```eval_rst
.. note::
    The server must be accessible from the internet. Running your own server might involve a bit of configuration in your router settings or setup of a cloud server, such as a virtual machine on DigitalOcean. You can also use the provided server at https://rtcbot.dev to help establish connections (see below).
```

In a previous tutorial, we developed a connection that streamed video to the browser. This tutorial will implement exactly the same functionality,
but with the robot on a remote connection.

The browser-side code will remain unchanged - all of the work here will be in Python.

## Server Code

Most of the server code is unchanged. The only difference is that we set up a listener at `/ws`, which will establish a websocket connection with the robot:

```python
ws = None # Websocket connection to the robot
@routes.get("/ws")
async def websocket(request):
    global ws
    ws = Websocket(request)
    print("Robot Connected")
    await ws  # Wait until the websocket closes
    print("Robot disconnected")
    return ws.ws
```

The above code sets up a global `ws` variable which will hold the active connection. We then use this websocket in the `/connect` handler. Instead of establishing a WebRTC connection ourselves, the server forwards the information directly to the robot using the websocket:

```python
# Called by the browser to set up a connection
@routes.post("/connect")
async def connect(request):
    global ws
    if ws is None:
        raise web.HTTPInternalServerError("There is no robot connected")
    clientOffer = await request.json()
    # Send the offer to the robot, and receive its response
    ws.put_nowait(clientOffer)
    robotResponse = await ws.get()
    return web.json_response(robotResponse)
```

This is all that is needed from the server - its function is simply to route the information necessary to
establish the connection directly between robot and browser. The full server code is here:

```python
from aiohttp import web
routes = web.RouteTableDef()

from rtcbot import Websocket, getRTCBotJS

ws = None # Websocket connection to the robot
@routes.get("/ws")
async def websocket(request):
    global ws
    ws = Websocket(request)
    print("Robot Connected")
    await ws  # Wait until the websocket closes
    print("Robot disconnected")
    return ws.ws

# Called by the browser to set up a connection
@routes.post("/connect")
async def connect(request):
    global ws
    if ws is None:
        raise web.HTTPInternalServerError("There is no robot connected")
    clientOffer = await request.json()
    # Send the offer to the robot, and receive its response
    ws.put_nowait(clientOffer)
    robotResponse = await ws.get()
    return web.json_response(robotResponse)

# Serve the RTCBot javascript library at /rtcbot.js
@routes.get("/rtcbot.js")
async def rtcbotjs(request):
    return web.Response(content_type="application/javascript", text=getRTCBotJS())

@routes.get("/")
async def index(request):
    return web.Response(
        content_type="text/html",
        text="""
    <html>
        <head>
            <title>RTCBot: Remote Video</title>
            <script src="/rtcbot.js"></script>
        </head>
        <body style="text-align: center;padding-top: 30px;">
            <video autoplay playsinline muted controls></video>
            <p>
            Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
            </p>
            <script>
                var conn = new rtcbot.RTCConnection();

                conn.video.subscribe(function(stream) {
                    document.querySelector("video").srcObject = stream;
                });

                async function connect() {
                    let offer = await conn.getLocalDescription();

                    // POST the information to /connect
                    let response = await fetch("/connect", {
                        method: "POST",
                        cache: "no-cache",
                        body: JSON.stringify(offer)
                    });

                    await conn.setRemoteDescription(await response.json());

                    console.log("Ready!");
                }
                connect();

            </script>
        </body>
    </html>
    """)

async def cleanup(app=None):
    global ws
    if ws is not None:
        c = ws.close()
        if c is not None:
            await c

app = web.Application()
app.add_routes(routes)
app.on_shutdown.append(cleanup)
web.run_app(app)
```

## Remote Code

For simplicity, we will just run both server and robot on the local machine. The robot connects to the server with a websocket, and waits for the message that will allow it to initialize its WebRTC connection.

```python
import asyncio
from rtcbot import Websocket, RTCConnection, CVCamera

cam = CVCamera()
conn = RTCConnection()
conn.video.putSubscription(cam)

# Connect establishes a websocket connection to the server,
# and uses it to send and receive info to establish webRTC connection.
async def connect():
    ws = Websocket("http://localhost:8080/ws")
    remoteDescription = await ws.get()
    robotDescription = await conn.getLocalDescription(remoteDescription)
    ws.put_nowait(robotDescription)
    print("Started WebRTC")
    await ws.close()


asyncio.ensure_future(connect())
try:
    asyncio.get_event_loop().run_forever()
finally:
    cam.close()
    conn.close()
```

With these two pieces of code, you first start the server, then start the robot, and finally open `http://localhost:8080` in the browser to view a video stream coming directly from the robot, even if the robot has an unknown IP.

## rtcbot.dev

The above example requires you to have your own internet-accessible server at a known IP address to set up the connection, if your remote code is not on your local network. The server's only real purpose is to help _establish_ a connection - once the connection is established, it does not do anything.

For this reason, I am hosting a free testing server online at `https://rtcbot.dev` that performs the equivalent of the following operation from the above server code:

```python
@routes.get("/ws")
async def websocket(request):
    global ws
    ws = Websocket(request)
    print("Robot Connected")
    await ws  # Wait until the websocket closes
    print("Robot disconnected")
    return ws.ws

# Called by the browser to set up a connection
@routes.post("/connect")
async def connect(request):
    global ws
    if ws is None:
        raise web.HTTPInternalServerError("There is no robot connected")
    clientOffer = await request.json()
    # Send the offer to the robot, and receive its response
    ws.put_nowait(clientOffer)
    robotResponse = await ws.get()
    return web.json_response(robotResponse)
```

Since the server at `rtcbot.dev` is open to anyone, instead of `/ws` and `/connect`, you need to choose some random sequence of letters and numbers that will identify your connection, for example `myRandomSequence11`.

Once you have chosen your sequence, you can both connect your websocket and POST to `https://rtcbot.dev/myRandomSequence11`:

```eval_rst
.. note::
    If you open https://rtcbot.dev/myRandomSequence11 in your browser, you can see if your remote code is connected with a websocket, and optionally open a video connection.
```

When using `rtcbot.dev`, the remote connection code becomes:

```python
async def connect():
    ws = Websocket("https://rtcbot.dev/myRandomSequence11")
    remoteDescription = await ws.get()
    robotDescription = await conn.getLocalDescription(remoteDescription)
    ws.put_nowait(robotDescription)
    print("Started WebRTC")
    await ws.close()
```

and the local browser's connection code becomes:

```js
let response = await fetch("https://rtcbot.dev/myRandomSequence11", {
  method: "POST",
  cache: "no-cache",
  body: JSON.stringify(offer),
});
```

With `rtcbot.dev`, you no longer need your local server code to run websockets or a connection service. Its only purpose is to give the browser the html and javascript necessary to establish a connection. We will get rid of the browser entirely in the next tutorial.

## If it doesn't work over 4G

The above example should work for most people. However, some mobile network operators perform routing that disallows creating a direct WebRTC connection to a mobile device over 4G. If this is your situation, you need to use what is called a TURN server, which will forward data between the browser and robot.

```eval_rst
.. note::
    You can check if your mobile operator allows such connections by using your phone to create a wifi hotspot, to which you can connect your robot. If video streaming works with the code above, you can ignore this section!
```

```eval_rst
.. warning::
    Because a TURN server essentially serves as a proxy through which an entire WebRTC connection is routed, it can send and receive quite a bit of data - make sure that you don't
    exceed your download and upload limits!
```

There are two options through which to setup a TURN server: [coTURN](https://github.com/coturn/coturn) and [Pion](https://github.com/pion/turn). Pion is meant to be a more simple and temporary solution that's easy to setup while coTURN is recommended for more permanent setups.

### Setup with Pion

The Pion server is easy to set up on Windows,Mac and Linux - all you need to do is [download the executable](https://github.com/pion/turn/releases/tag/1.0.3), and run it from the command line as shown.

**Linux/Mac**:

```bash
chmod +x ./simple-turn-linux-amd64 # allow executing the downloaded file
export USERS='myusername=mypassword'
export REALM=my.server.ip
export UDP_PORT=3478
./simple-turn-linux-amd64 # simple-turn-darwin-amd64 if on Mac
```

**Windows**: You can run the following from powershell:

```powershell
$env:USERS = "myusername=mypassword"
$env:REALM = "my.server.ip"
$env:UDP_PORT = 3478
./simple-turn-windows-amd64.exe
```

With the Pion server running, you will need to let both Python and Javascript know about it when creating your `RTCConnection`:

```python
from aiortc import RTCConfiguration, RTCIceServer

myConnection = RTCConnection(rtcConfiguration=RTCConfiguration([
                    RTCIceServer(urls="stun:stun.l.google.com:19302"),
                    RTCIceServer(urls="turn:my.server.ip:3478",
                        username="myusername",credential="mypassword")
                ]))
```

```javascript
var conn = new rtcbot.RTCConnection(true, {
                iceServers:[
                    { urls: ["stun:stun.l.google.com:19302"] },
                    { urls: "turn:my.server.ip:3478?transport=udp",
                        username: "myusername", credential: "mypassword", },
                ]);
```

### Setup with coTURN

Setting up a coTURN server takes a bit more work and is only supported on Linux and Mac. The following steps will assume a Linux system running Ubuntu.

Install coTURN and stop the coTURN service to modify config files with

```bash
sudo apt install coturn
sudo systemctl stop coturn
```

Edit the file `/etc/default/coturn` by uncommenting the line `TURNSERVER_ENABLED=1`. This will allow coTURN to start in daemon mode on boot.

Edit another file `/etc/turnserver.conf` and add the following lines. Be sure to put your system's public facing IP address in place of `<PUBLIC_NETWORK_IP>`, your domain name in place of `<DOMAIN>`, and your own credentials in place of `<USERNAME>` and `<PASSWORD>`.

```
listening-port=3478
tls-listening-port=5349
listening-ip=<PUBLIC_NETWORK_IP>
relay-ip=<PUBLIC_NETWORK_IP>
external-ip=<PUBLIC_NETWORK_IP>
realm=<DOMAIN>
server-name=<DOMAIN>

user=<USERNAME>:<PASSWORD>
lt-cred-mech
```

```eval_rst
.. note::
    If you are running coTURN within a local network, <DOMAIN> can be whatever you want.
```

Restart the coTURN service, check that it's running, and reboot.

```bash
sudo systemctl start coturn
sudo systemctl status coturn
sudo reboot
```

With the coTURN server running, you will need to let both Python and Javascript know about it when creating your `RTCConnection`:

```python
from aiortc import RTCConfiguration, RTCIceServer

myConnection = RTCConnection(rtcConfiguration=RTCConfiguration([
                    RTCIceServer(urls="stun:stun.l.google.com:19302"),
                    RTCIceServer(urls="turn:<PUBLIC_NETWORK_IP>:3478",
                        username="myusername",credential="mypassword")
                ]))
```

```javascript
var conn = new rtcbot.RTCConnection(true, {
                iceServers:[
                    { urls: ["stun:stun.l.google.com:19302"] },
                    { urls: "turn:<PUBLIC_NETWORK_IP:3478?transport=udp",
                        username: "myusername", credential: "mypassword", },
                ]);
```

```eval_rst
.. note::
    If you are running coTURN on a local network, replace <PUBLIC_NETWORK_IP> with the public facing IP of the system running coTURN. If coTURN is running on a server with a domain, replace <PUBLIC_NETWORK_IP> with the domain/realm set in /etc/turnserver.conf.
```

With either of the options above, you should be able to stream video to your browser using 4G, even if your mobile operator disallows direct connections.

## Summary

This tutorial split up the server and robot code into distinct pieces. Also introduced was rtcbot's websocket wrapper, allowing you to easily establish a data-only connection. Finally, TURN servers were introduced, and instructions were given on how to set one up if direct connections fail.

## Extra Notes

Be aware that throughout these tutorials, all error handling and robustness was left out in the interest of
clarity in the fundamental program flow. In reality, you will probably want to make sure that the connection
did not have an error, and add the ability to connect and disconnect multiple times.
