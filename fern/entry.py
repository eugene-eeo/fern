import base64
import dataclasses
import json
from typing import Union

from nacl.hash import sha256
from nacl.encoding import Base64Encoder
from fern.identity import Identity, LocalIdentity


def canonical_encode_json(data):
    return json.dumps(data, indent=2, sort_keys=True)


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
    b = canonical_encode_json(d).encode('utf-8')
    d["sig"] = author.sign(b)
    id = sha256(canonical_encode_json(d).encode('utf-8'),
                encoder=Base64Encoder)
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
        id = sha256(canonical_encode_json(data).encode('ascii'),
                    encoder=Base64Encoder)
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

    def verify(self):
        d = self.to_json()
        sig = d.pop('sig')
        msg = canonical_encode_json(d).encode('utf-8')
        return self.author.verify(msg, sig)
