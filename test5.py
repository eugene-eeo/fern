import asyncio
from fern.proto.rpc import Request
from fern.proto.stream import RPCStream
from fern.proto.utils import Connection


async def main():
    r, w = await asyncio.open_connection(host='localhost', port=9110)
    conn = Connection(r, w)
    with conn:
        rpc_stream = RPCStream(conn)
        for i in range(10):
            await Request(
                id=i,
                name="feed.add",
                args={"type": "msg",
                      "data": "hello world! hope you're listening, this is a box stream"}
            ).send(rpc_stream)
        for i in range(10):
            print(await rpc_stream.next())
        await Request(
            id=10,
            name="feed.digest",
            args={},
        ).send(rpc_stream)
        print(await rpc_stream.next())
        await rpc_stream.goodbye()


if __name__ == '__main__':
    asyncio.run(main())
