import asyncio
import base64
from fern.identity import LocalIdentity
from fern.proto.handshake import client_handshake, server_handshake
from fern.proto.stream import RPCStream


client_id = LocalIdentity.generate()
server_id = LocalIdentity.generate()


class SockFile:
    def __init__(self, reader, writer):
        self.r = reader
        self.w = writer

    async def read(self, n):
        return await self.r.read(n)

    async def write(self, b):
        self.w.write(b)
        await self.w.drain()


async def client(server_started):
    async with server_started:
        await server_started.wait()

    reader, writer = await asyncio.open_connection('127.0.0.1', 8118)
    box = await client_handshake(
        client_id=client_id,
        server_id=server_id.to_identity(),
        conn=SockFile(reader, writer),
    )
    sn = base64.b64encode(box.send_nonce).decode('ascii')
    rn = base64.b64encode(box.recv_nonce).decode('ascii')
    print(f"client: client: {client_id.to_identity()} send_nonce: {sn}, recv_nonce: {rn}")
    rpc = RPCStream(box)
    await rpc.send({"hello": "world"}, 1)
    print(await rpc.next())


async def server(cond):
    async def handle(reader, writer):
        id, box = await server_handshake(
            server_id=server_id,
            conn=SockFile(reader, writer),
        )
        sn = base64.b64encode(box.send_nonce).decode('ascii')
        rn = base64.b64encode(box.recv_nonce).decode('ascii')
        print(f"server: client: {id} send_nonce: {sn}, recv_nonce: {rn}")
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
    asyncio.run(main())
