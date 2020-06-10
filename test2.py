import sys
import socket
import asyncio
from anyio import create_udp_socket
from fern.identity import LocalIdentity, Identity
from fern.proto.handshake import client_handshake, server_handshake
from fern.proto.utils import Connection
from fern.proto.stream import RPCStream


local_id = LocalIdentity.generate()
active = set()


async def handle_tcp(reader, writer):
    id, box = await server_handshake(
        server_id=local_id,
        conn=Connection(reader, writer)
    )
    rpc_stream = RPCStream(box)
    await rpc_stream.send({"hi": True}, 1)
    print(await rpc_stream.next())
    print(await rpc_stream.next())
    await rpc_stream.goodbye()
    writer.close()


class DiscoveryResponse(asyncio.DatagramProtocol):
    def datagram_received(self, data, addr):
        async def main():
            parts = data.decode('ascii').split(":", 4)
            if len(parts) != 4 or parts[2] != "fern" or parts[3] == str(local_id):
                return

            tcp_addr = (parts[0], int(parts[1]))
            if tcp_addr in active:
                return

            server_id = Identity.from_id(parts[3])
            active.add(tcp_addr)
            try:
                reader, writer = await asyncio.open_connection(*tcp_addr)
                box = await client_handshake(
                    client_id=local_id,
                    server_id=server_id,
                    conn=Connection(reader, writer),
                )
                rpc_stream = RPCStream(box)
                await rpc_stream.send({"client": "hi!"}, 1)
                await rpc_stream.send({"client": "hi!"}, 2)
                print(await rpc_stream.next())
                r = await rpc_stream.next()
                print(r.alive)
                writer.close()
            finally:
                active.discard(tcp_addr)

        loop = asyncio.get_event_loop()
        loop.create_task(main())


def start(port1, port2):
    loop = asyncio.get_event_loop()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(('127.255.255.255', port1))

    loop.run_until_complete(loop.create_datagram_endpoint(
        DiscoveryResponse,
        sock=sock,
    ))

    async def udp_discovery():
        async with await create_udp_socket(interface='localhost') as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while True:
                await s.send(f"127.0.0.1:{port2}:fern:{str(local_id)}".encode('ascii'),
                             '127.255.255.255',
                             port1)
                await asyncio.sleep(5)

    async def serve_tcp():
        server = await asyncio.start_server(handle_tcp, '127.0.0.1', port2)
        async with server:
            await server.serve_forever()

    loop.create_task(serve_tcp())
    loop.create_task(udp_discovery())
    loop.run_forever()


if __name__ == '__main__':
    port1 = int(sys.argv[1])
    port2 = int(sys.argv[2])
    start(port1, port2)
