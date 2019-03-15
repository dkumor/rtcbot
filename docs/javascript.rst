====================
Javascript
====================

The Javascript API for RTCBot is provided for simple interoperability of RTCBot and the browser. Wherever possible,
the Javascript API mirrors the Python API, and can be used in exactly the same way.

.. note::
    The Javascript API includes only a minimal subset of the functionality of RTCBot's Python version. While this may change in the future,
    many of the functions available in Python can't be used in javascript.

Basic Usage
++++++++++++++++

To start using the Javascript API, all you need to do is include the `RTCBot.js` file in your site, and include the following javascript:
    
.. code-block:: javascript

    // The connection object
    var conn = new RTCConnection();

    // Here we set up the connection. We put it in an async function, since we will be
    // waiting for results from the server (Promises).
    async function setupRTC() {
        // Get the information needed to connect from the server to the browser
        let offer = await conn.getLocalDescription();

        // POST the information to the server, which will respond with the corresponding remote
        // connection's description
        let response = await fetch("/setupRTC", {
            method: "POST",
            cache: "no-cache",
            body: JSON.stringify(offer)
        });

        // Set the remote server's information
        await conn.setRemoteDescription(await response.json());
    }

    setupRTC(); // Run the async function in the background.


Next, to establish the connection with Python, you include the Python counterpart::

    from aiohttp import web
    from rtcbot import RTCConnection

    routes = web.RouteTableDef()


    @routes.get("/")
    async def index(request):
        with open("camera.html", "r") as f:
            return web.Response(content_type="text/html", text=f.read())


    @routes.post("/setupRTC")
    async def setupRTC(request):
        clientOffer = await request.json()
        conn = RTCConnection()

        response = await conn.getLocalDescription(clientOffer)
        return web.json_response(response)


    routes.static("/rtcbot/", path="./rtcbot")
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=8000)


Python API
+++++++++++++++

.. automodule:: rtcbot.javascript
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance:

Javascript API
++++++++++++++++

.. js:autoclass:: RTCConnection
   :members:

.. js:autoclass:: Queue
   :members:
