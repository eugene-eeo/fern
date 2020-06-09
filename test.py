import time
import multiprocessing
import socket
from fern.identity import LocalIdentity
from fern.proto.handshake import client_handshake, server_handshake


client_id = LocalIdentity.generate()
server_id = LocalIdentity.generate()


class SockFile:
    def __init__(self, sock):
        self.sock = sock

    def read(self, n):
        return self.sock.recv(n)

    def write(self, b):
        self.sock.send(b)


def client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 8118))

    box = client_handshake(
        client_id=client_id,
        server_id=server_id.to_identity(),
        conn=SockFile(sock),
    )
    print(box.shared_key())


def server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('localhost', 8118))
    sock.listen(1)

    conn, _ = sock.accept()
    box = server_handshake(
        client_id=client_id.to_identity(),
        server_id=server_id,
        conn=SockFile(conn),
    )
    print(box.shared_key())


proc1 = multiprocessing.Process(target=client)
proc2 = multiprocessing.Process(target=server)
proc2.start()
time.sleep(1)
proc1.start()
proc1.join()
proc2.join()
