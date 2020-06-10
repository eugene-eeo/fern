import base64
import time
import multiprocessing
import socket
from fern.identity import LocalIdentity
from fern.proto.handshake import client_handshake, server_handshake
from fern.proto.stream import RPCStream


client_id = LocalIdentity.generate()
server_id = LocalIdentity.generate()


class SockFile:
    def __init__(self, sock):
        self.sock = sock
        self.buff = b''

    def read(self, n):
        while len(self.buff) < n:
            r = self.sock.recv(4096)
            self.buff += r
            if r == b'':
                raise EOFError
        b = self.buff[:n]
        self.buff = self.buff[n:]
        return b

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
    sn = base64.b64encode(box.send_nonce).decode('ascii')
    rn = base64.b64encode(box.recv_nonce).decode('ascii')
    print(f"client: client: {client_id.to_identity()} send_nonce: {sn}, recv_nonce: {rn}")
    rpc = RPCStream(box)
    rpc.send({"hello": "world"}, 1)
    print(rpc.next())


def server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('localhost', 8118))
    sock.listen(1)

    conn, _ = sock.accept()
    id, box = server_handshake(
        server_id=server_id,
        conn=SockFile(conn),
    )
    sn = base64.b64encode(box.send_nonce).decode('ascii')
    rn = base64.b64encode(box.recv_nonce).decode('ascii')
    print(f"server: client: {id} send_nonce: {sn}, recv_nonce: {rn}")
    rpc = RPCStream(box)
    rpc.send({"response": "1"}, 1)
    print(rpc.next())


proc1 = multiprocessing.Process(target=client)
proc2 = multiprocessing.Process(target=server)
proc2.start()
time.sleep(0.1)
proc1.start()
proc1.join()
proc2.join()
