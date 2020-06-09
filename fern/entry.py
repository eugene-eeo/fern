import base64
import dataclasses
import json

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
                data: bytes):
    d = {
        "previous":  previous,
        "sequence":  sequence,
        "author":    str(author),
        "timestamp": timestamp,
        "type":      type,
        "data":      base64.b64encode(data).decode('ascii'),
    }
    b = canonical_encode_json(d).encode('ascii')
    d["signature"] = author.sign(b)
    id = sha256(canonical_encode_json(d).encode('ascii'),
                encoder=Base64Encoder)
    return Entry(
        id=f'%{id.decode("ascii")}',
        previous=previous,
        author=author,
        sequence=sequence,
        timestamp=timestamp,
        type=type,
        data=data,
        signature=d["signature"],
    )


@dataclasses.dataclass(frozen=True, eq=True)
class Entry:
    id: str
    previous: str
    author: Identity
    sequence: int
    timestamp: int
    type: str
    data: bytes
    signature: str

    def to_json(self):
        return {
            "previous": self.previous,
            "author":   str(self.author),
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "type": self.type,
            "data": base64.b64encode(self.data).decode('ascii'),
            "signature": self.signature,
        }

    @staticmethod
    def from_json(data):
        id = sha256(canonical_encode_json(data).encode('ascii'),
                    encoder=Base64Encoder)
        return Entry(
            id=f'%{id.decode("ascii")}',
            previous=(
                None if data["previous"] is None
                else data["previous"]
            ),
            author=Identity.from_id(data["author"]),
            sequence=data["sequence"],
            timestamp=data["timestamp"],
            type=data["type"],
            data=base64.b64decode(data["data"]),
            signature=data["signature"],
        )

    def verify(self):
        d = self.to_json()
        sig = d.pop('signature')
        msg = canonical_encode_json(d).encode('ascii')
        return self.author.verify(msg, sig)
