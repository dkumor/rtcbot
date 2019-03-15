import os.path

__moduleDir = os.path.dirname(__file__)


def getRTCBotJS():
    """
    Returns the RTCBot javascript. This allows you to easily write self-contained scripts.
    You can serve it like this::

        from rtcbot import getRTCBotJS
        from aiohttp import web
        routes = web.RouteTableDef()

        @routes.get("/rtcbot.js")
        async def rtcbotJS(request):
            return web.Response(content_type="application/javascript", text=getRTCBotJS())

        app = web.Application()
        app.add_routes(routes)
        web.run_app(app, port=8000)

    If you are writing a more complex application, you might want to bundle RTCBot's javascript
    with your code using rollup or webpack instead of including it in script tags.
    To do this, you can install the js library separately with npm, and bundle it however you'd like::

        npm i rtcbot

    """
    with open(os.path.join(__moduleDir, "rtcbot.js"), "r") as f:
        return f.read()
