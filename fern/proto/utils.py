import asyncio


class Connection:
    def __init__(self,
                 reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.r = reader
        self.w = writer

    async def read(self, n):
        return await self.r.readexactly(n)

    async def write(self, b):
        self.w.write(b)
        await self.w.drain()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.w.close()


class Deadline:
    def __init__(self, conn, timeout=2):
        self.conn = conn
        self.timeout = timeout

    async def read(self, n):
        return await asyncio.wait_for(self.conn.read(n), self.timeout)

    async def write(self, b):
        await asyncio.wait_for(self.conn.write(b), self.timeout)


class ProtocolError(Exception):
    pass
