import json
import asyncio
import datetime
import contextvars
import itertools
import sys


from aiohttp import web
import attr


START_TIME = None
counter = itertools.count()
ID = contextvars.ContextVar("id")


@attr.s
class Handler:
    async def handle(self, request):
        global START_TIME
        if START_TIME is None:
            START_TIME = datetime.datetime.utcnow()

        ID.set(next(counter))
        delay = request.rel_url.query["delay"]

        elapsed = (datetime.datetime.utcnow() - START_TIME).seconds
        print(
            json.dumps(
                dict(message="receive", id=ID.get(), elapsed=elapsed, delay=delay)
            ), file=sys.stderr
        )
        await asyncio.sleep(int(delay))
        elapsed = (datetime.datetime.utcnow() - START_TIME).seconds
        response = json.dumps(
            dict(message="respond", id=ID.get(), elapsed=elapsed, delay=delay)
        )
        print(response, file=sys.stderr)

        return web.Response(text=response)


app = web.Application()
handler = Handler()
handle = handler.handle
app.add_routes([web.get("/", handle), web.get("/delay/{delay}", handle)])

web.run_app(app)
