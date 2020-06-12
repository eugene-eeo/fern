import orjson
from collections import namedtuple
from nacl.secret import SecretBox
from fern.proto.utils import ProtocolError


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

    def increment_send(self):
        self.send_nonce = increment(self.send_nonce)
        return self.send_nonce

    def increment_recv(self):
        self.recv_nonce = increment(self.recv_nonce)
        return self.recv_nonce

    async def write(self, b: bytes):
        n = len(b)
        b = memoryview(b)
        while n > 0:
            m = min(n, 4096)
            # 2 byte header for length
            head = m.to_bytes(2, byteorder='big')
            body = b[:m]
            shead = self.sbox.encrypt(head, nonce=self.increment_send())
            sbody = self.sbox.encrypt(body, nonce=self.increment_send())
            await self.conn.write(shead.ciphertext + sbody.ciphertext)
            n -= m
            b = b[m:]

    async def next_frame(self):
        header = self.sbox.decrypt(
            await self.conn.read(18),
            nonce=self.increment_recv(),
        )
        length = int.from_bytes(header, byteorder='big')
        return self.sbox.decrypt(
            await self.conn.read(16 + length),
            nonce=self.increment_recv(),
        )

    async def read(self, n):
        # Read enough information
        while len(self.buf) < n:
            self.buf += await self.next_frame()
        b = self.buf[:n]
        self.buf = self.buf[n:]
        return b


FLAG_JSON = 0b00001000
FLAG_STREAM = 0b00000100
FLAG_ERR = 0b00000010
FLAG_EOS = 0b00000001


RPCFrame = namedtuple('RPCFrame', ('alive', 'request_id', 'data', 'is_error', 'is_eos', 'is_stream'))
GOODBYE_FRAME = RPCFrame(alive=False, request_id=None, data=None, is_error=False, is_eos=False, is_stream=False)


class RPCStream:
    def __init__(self, conn):
        self.conn = conn

    async def goodbye(self):
        await self.conn.write((0).to_bytes(9, byteorder="big"))

    async def send(self,
                   request_id: int,
                   data: object,
                   is_error: bool = False,
                   is_eos: bool = False,
                   is_stream: bool = False):

        is_json = False
        if not isinstance(data, bytes):
            is_json = True
            data = orjson.dumps(data)

        if len(data) > 2**32 - 1:
            raise ProtocolError("length is too long")

        flags = 0
        flags |= FLAG_ERR if is_error else 0
        flags |= FLAG_EOS if is_eos else 0
        flags |= FLAG_JSON if is_json else 0
        flags |= FLAG_STREAM if is_stream else 0

        header = (
            flags.to_bytes(1, byteorder="big") +
            len(data).to_bytes(4, byteorder="big") +
            request_id.to_bytes(4, byteorder="big")
        )
        # header is 9 bytes
        await self.conn.write(header + data)

    async def next(self) -> RPCFrame:
        header = await self.conn.read(9)
        flags = header[0]
        length = int.from_bytes(header[1:5], byteorder="big")
        req_id = int.from_bytes(header[5:], byteorder="big")

        if length == 0:
            return GOODBYE_FRAME

        data = await self.conn.read(length)
        data = orjson.loads(data) if flags & FLAG_JSON else data

        return RPCFrame(alive=True,
                        request_id=req_id,
                        data=data,
                        is_error=bool(flags & FLAG_ERR),
                        is_stream=bool(flags & FLAG_STREAM),
                        is_eos=bool(flags & FLAG_EOS))
