import asyncio
import uvloop
from fern.identity import LocalIdentity
from fern.proto.handshake import client_handshake, server_handshake
from fern.proto.stream import RPCStream
from fern.proto.utils import Connection


client_id = LocalIdentity.generate()
server_id = LocalIdentity.generate()


async def client(server_started):
    async with server_started:
        await server_started.wait()

    reader, writer = await asyncio.open_connection('127.0.0.1', 8118)
    box = await client_handshake(
        client_id=client_id,
        server_id=server_id.to_identity(),
        conn=Connection(reader, writer),
    )
    rpc = RPCStream(box)
    await rpc.send({"hello": "world"}, 1)
    print(await rpc.next())


async def server(cond):
    async def handle(reader, writer):
        id, box = await server_handshake(
            server_id=server_id,
            conn=Connection(reader, writer),
        )
        rpc = RPCStream(box)
        await rpc.send({"response": "1"}, 1)
        print(await rpc.next())
        writer.close()
        asyncio.get_event_loop().stop()

    server = await asyncio.start_server(handle, '127.0.0.1', 8118)
    async with server:
        async with cond:
            cond.notify()
        await server.serve_forever()


async def main():
    server_started = asyncio.Condition()
    await asyncio.gather(
        server(server_started),
        client(server_started),
    )


if __name__ == '__main__':
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(main())
