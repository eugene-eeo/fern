import base64
import dataclasses
import orjson
from typing import Union

from nacl.hash import sha256
from nacl.encoding import Base64Encoder
from fern.identity import Identity, LocalIdentity


def canonical_encode_json(data) -> bytes:
    return orjson.dumps(data, option=orjson.OPT_SORT_KEYS)


def build_entry(author: LocalIdentity,
                previous: str,
                sequence: int,
                timestamp: int,
                type: str,
                data: Union[dict, bytes]):
    d = {
        "prev":      previous,
        "seq":       sequence,
        "author":    str(author),
        "timestamp": timestamp,
        "type":      type,
        "data":      Entry.encode_data(data),
    }
    b = canonical_encode_json(d)
    d["sig"] = author.sign(b)
    id = sha256(canonical_encode_json(d), encoder=Base64Encoder)
    return Entry(
        id=f'%{id.decode("ascii")}',
        previous=previous,
        author=author,
        sequence=sequence,
        timestamp=timestamp,
        type=type,
        data=data,
        signature=d["sig"],
    )


@dataclasses.dataclass(frozen=True, eq=True)
class Entry:
    id: str
    previous: str
    author: Identity
    sequence: int
    timestamp: int
    type: str
    data: Union[bytes, dict]
    signature: str

    @staticmethod
    def decode_data(data: Union[dict, str]):
        return (base64.b64decode(data)
                if isinstance(data, str)
                else data)

    @staticmethod
    def encode_data(data: Union[dict, bytes]):
        return (base64.b64encode(data).decode('ascii')
                if isinstance(data, bytes)
                else data)

    def to_json(self):
        return {
            "prev": self.previous,
            "seq": self.sequence,
            "author":   str(self.author),
            "timestamp": self.timestamp,
            "type": self.type,
            "data": self.encode_data(self.data),
            "sig": self.signature,
        }

    @staticmethod
    def from_json(data):
        id = sha256(canonical_encode_json(data), encoder=Base64Encoder)
        return Entry(
            id=f'%{id.decode("ascii")}',
            previous=data["prev"],
            author=Identity.from_id(data["author"]),
            sequence=data["seq"],
            timestamp=data["timestamp"],
            type=data["type"],
            data=Entry.decode_data(data["data"]),
            signature=data["sig"],
        )

    def verify(self, author: Union[None, Identity] = None):
        d = self.to_json()
        sig = d.pop('sig')
        msg = canonical_encode_json(d)

        # Check signature against predefined author
        if author is not None:
            if not author.verify(msg, sig):
                return False

        return self.author.verify(msg, sig)
