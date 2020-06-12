import asyncio
from functools import wraps
from contextlib import asynccontextmanager

from fern.config import Config
from fern.proto.utils import Connection, Deadline
from fern.proto.stream import RPCStream
from fern.proto.rpc import decode_frame, Request, Response
from fern.store.log import get_db, init_db


def expose(method):

    @wraps(method)
    async def meth(self, s, req):
        try:
            await method(self, s, req)
        except Exception as exc:
            await Response(id=req.id, is_error=True, content={"err": True}).send(s)
            raise exc

    meth.__expose__ = True
    return meth


class Handler:
    prefix = ''

    def __init__(self, config):
        self.config = config

    @asynccontextmanager
    async def get_db(self):
        async with get_db(self.config.log_path) as db:
            await init_db(db)
            yield db

    def register(self, handlers):
        for name in dir(self):
            fn = getattr(self, name)
            if getattr(fn, '__expose__', False):
                if self.prefix:
                    name = f'{self.prefix}.{name}'
                handlers[name] = fn


class LocalRPC:
    def __init__(self, config: Config, handlers=[]):
        self.config = config
        self.handlers = {}
        for handler in handlers:
            handler(self.config).register(self.handlers)

    async def no_handler(self, s: RPCStream, req: Request):
        r = Response(id=req.id,
                     content={"err": "no handler for '%s'" % req.name},
                     is_error=True)
        await r.send(s)

    async def serve_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        conn = Connection(reader, writer)
        rpc_stream = RPCStream(Deadline(conn))
        with conn:
            while True:
                frame = await rpc_stream.next()
                if not frame.alive:
                    break

                # find the appropriate handler
                req = decode_frame(frame, is_server=True)
                f = self.handlers.get(req.name, self.no_handler)
                await f(rpc_stream, req)

    async def serve(self):
        host, port = self.config.local_tcp_addr.rsplit(':', 1)
        server = await asyncio.start_server(
            self.serve_client,
            host=host,
            port=int(port),
        )
        await server.serve_forever()
