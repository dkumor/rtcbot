import os.path

__moduleDir = os.path.dirname(__file__)


def getRTCBotJS(minified=True):
    """
    Returns the RTCBot javascript. This allows you to easily write self-contained scripts.
    You can then serve it like this::

        from aiohttp import web
        routes = web.RouteTableDef()

        @routes.get("/rtcbot.js")
        async def rtcbotJS(request):
            return web.Response(content_type="text/javascript", text=getRTCBotJS())

        app = web.Application()
        app.add_routes(routes)
        web.run_app(app, port=8000)

    
    """
    if minified:
        try:
            with open(os.path.join(__moduleDir, "rtcbot.min.js"), "r") as f:
                return f.read()
        except:
            pass
    with open(os.path.join(__moduleDir, "rtcbot.js"), "r") as f:
        return f.read()
