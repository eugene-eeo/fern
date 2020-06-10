import time
import sys
import socket
import asyncio
from fern.identity import LocalIdentity, Identity
from fern.proto.handshake import client_handshake, server_handshake
from fern.proto.stream import RPCStream


local_id = LocalIdentity.generate()
active = set()


async def handle_tcp(reader, writer):
    pass


class DiscoveryResponse(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        pass

    def datagram_received(self, data, addr):

        async def main():
            parts = data.decode('ascii').split(":", 4)
            if len(parts) != 4 or parts[2] != "fern" or parts[3] == str(local_id):
                return
            tcp_addr = (parts[0], int(parts[1]))
            server_id = Identity.from_id(parts[3])
            print(parts)

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

    def udp_discovery():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            sock.sendto(f"127.0.0.1:{port2}:fern:{str(local_id)}".encode('ascii'),
                        ('127.255.255.255', port1))
            time.sleep(5)

    async def serve_tcp():
        server = await asyncio.start_server(handle_tcp, '127.0.0.1', port2)
        async with server:
            await server.serve_forever()

    loop.run_until_complete(loop.run_in_executor(None, udp_discovery))
    loop.run_until_complete(serve_tcp())
    loop.run_forever()


if __name__ == '__main__':
    port1 = int(sys.argv[1])
    port2 = int(sys.argv[2])
    start(port1, port2)
