from aiohttp import web

routes = web.RouteTableDef()


@routes.get("/")
async def index(request):
    return web.Response(
        content_type="text/html",
        text="""
    <html>
        <head>
            <title>RTCBot: Basic</title>
        </head>
        <body style="text-align: center;padding-top: 30px;">
            <h1>Click the Button</h1>
            <button type="button" id="mybutton">Click me!</button>
            <p>
            Open the browser's developer tools to see console messages (CTRL+SHIFT+C)
            </p>
            <script>
                var mybutton = document.querySelector("#mybutton");
                mybutton.onclick = function() {
                    console.log("I was just clicked!");
                };
            </script>
        </body>
    </html>
    """,
    )


app = web.Application()
app.add_routes(routes)
web.run_app(app)
