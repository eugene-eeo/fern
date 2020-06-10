import socket
import asyncio


class Discovery(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        pass

    def datagram_received(self, data, addr):
        print(data)
        print(addr)


def start():
    loop = asyncio.get_event_loop()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(('127.255.255.255', 8118))

    loop.run_until_complete(loop.create_datagram_endpoint(
        Discovery,
        sock=sock,
    ))
    loop.run_forever()


if __name__ == '__main__':
    start()
