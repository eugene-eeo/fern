import io
from nacl.public import PrivateKey, Box
from fern.proto.stream import BoxStream, RPCStream

box = Box(PrivateKey.generate(),
          PrivateKey.generate().public_key)

conn = io.BytesIO()
rpc = RPCStream(BoxStream(box, conn))

rpc.send({"content": "你好 world"}, request_id=20)
conn.seek(0)
print(rpc.next())
