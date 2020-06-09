import io
from nacl.public import PrivateKey, Box
from fern.proto.stream import BoxStream, RPCStream

box = Box(PrivateKey.generate(),
          PrivateKey.generate().public_key)

conn = io.BytesIO()
bs = BoxStream(box, conn)
rpc = RPCStream(bs)

rpc.send({"content": 1}, request_id=20)
conn.seek(0)
print(rpc.next())
