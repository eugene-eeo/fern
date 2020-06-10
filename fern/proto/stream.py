import json
from collections import namedtuple
from nacl.secret import SecretBox


MAX = 2**(24 * 8) - 1


def increment(x: bytes):
    u = int.from_bytes(x, byteorder="big")
    u += 1
    try:
        return u.to_bytes(24, byteorder="big")
    except OverflowError:
        return (u & MAX).to_bytes(24, byteorder="big")


class BoxStream:
    def __init__(self, sbox: SecretBox, send_nonce: bytes, recv_nonce: bytes, conn):
        self.conn = conn
        self.sbox = sbox
        self.send_nonce = send_nonce
        self.recv_nonce = recv_nonce
        self.buf = b''

    async def write(self, b: bytes):
        n = len(b)
        b = memoryview(b)
        while n > 0:
            m = min(n, 4096)
            # 2 byte header for length
            head = m.to_bytes(2, byteorder='big')
            body = b[:m]
            self.send_nonce = increment(self.send_nonce)
            shead = self.sbox.encrypt(head, nonce=self.send_nonce)
            self.send_nonce = increment(self.send_nonce)
            sbody = self.sbox.encrypt(body, nonce=self.send_nonce)
            await self.conn.write(shead.ciphertext + sbody.ciphertext)
            n -= m
            b = b[m:]

    async def next_frame(self):
        self.recv_nonce = increment(self.recv_nonce)
        header = self.sbox.decrypt(
            await self.conn.read(18),
            nonce=self.recv_nonce,
        )
        self.recv_nonce = increment(self.recv_nonce)
        return self.sbox.decrypt(
            await self.conn.read(16 + int.from_bytes(header, byteorder='big')),
            nonce=self.recv_nonce,
        )

    async def read(self, n):
        # Read enough information
        while len(self.buf) < n:
            self.buf += await self.next_frame()
        b = self.buf[:n]
        self.buf = self.buf[n:]
        return b


STREAM_FLAG = 0b00000001  # noqa: E221
EOS_FLAG = 0b00000010  # noqa: E221
ERROR_FLAG = 0b00000100  # noqa: E221
ALIVE_FLAG = 0b10000000  # noqa: E221


RPCFrame = namedtuple('RPCFrame', ['alive', 'request_id', 'data',
                                   'is_error', 'is_stream', 'end_of_stream'])
GOODBYE_FRAME = RPCFrame(alive=False, request_id=None, data=None,
                         is_error=False, is_stream=False, end_of_stream=False)


class RPCStream:
    def __init__(self, conn: BoxStream):
        self.conn = conn

    async def goodbye(self):
        await self.conn.write((0).to_bytes(9, byteorder="big"))

    async def send(self,
                   obj: object,
                   request_id: int,
                   is_error: bool = False,
                   is_stream: bool = False,
                   end_of_stream: bool = False):

        flags = 0
        flags |= ALIVE_FLAG
        if is_error:
            flags |= ERROR_FLAG
        if is_stream:
            flags |= STREAM_FLAG
            if end_of_stream:
                flags |= EOS_FLAG

        data = json.dumps(obj, indent=None).encode('utf-8')
        header = (
            flags.to_bytes(1, byteorder="big") +
            len(data).to_bytes(4, byteorder="big") +
            request_id.to_bytes(4, byteorder="big")
        )
        # header is 9 bytes
        await self.conn.write(header + data)

    async def next(self):
        header = await self.conn.read(9)
        flags = header[0]
        if not flags & ALIVE_FLAG:
            return GOODBYE_FRAME

        length = int.from_bytes(header[1:5], byteorder="big")
        req_id = int.from_bytes(header[5:], byteorder="big")

        data = await self.conn.read(length)
        data = json.loads(data.decode('utf-8'))

        return RPCFrame(
            alive=True,
            request_id=req_id,
            data=data,
            is_error=bool(flags & ERROR_FLAG),
            is_stream=bool(flags & STREAM_FLAG),
            end_of_stream=bool(flags & EOS_FLAG),
        )
