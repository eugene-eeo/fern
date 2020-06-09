import base64
from nacl.signing import VerifyKey, SigningKey
from nacl.encoding import Base64Encoder
from nacl.exceptions import BadSignatureError


class Identity:
    __slots__ = ('pub',)

    def __init__(self, pub: VerifyKey):
        self.pub = pub

    def __hash__(self):
        return hash(self.pub)

    @classmethod
    def from_id(cls, pub_b64: str):
        if len(pub_b64) != 45 or not pub_b64.startswith('@'):
            raise ValueError("Invalid id string")
        return cls(pub=VerifyKey(
            pub_b64[1:],
            encoder=Base64Encoder,
        ))

    def to_bytes(self):
        return b'@' + self.pub.encode(Base64Encoder)

    def __str__(self):
        return self.to_bytes().decode('ascii')

    def __repr__(self):
        return f'<{self.__class__.__name__} [{str(self)}]>'

    def __eq__(self, other):
        return isinstance(other, Identity) and self.pub == other.pub

    def verify(self, data: bytes, signature: str) -> bool:
        sig = base64.b64decode(signature)
        try:
            self.pub.verify(data, sig)
            return True
        except BadSignatureError:
            return False


class LocalIdentity(Identity):
    __slots__ = ('pub', 'priv')

    def __init__(self, priv: SigningKey):
        self.priv = priv
        self.pub = priv.verify_key

    @classmethod
    def from_id(cls, pub_b64: str):
        raise NotImplementedError

    @classmethod
    def from_bytes(cls, priv_b64: bytes):
        return cls(SigningKey(priv_b64, encoder=Base64Encoder))

    @classmethod
    def generate(cls):
        return cls(priv=SigningKey.generate())

    def to_priv_bytes(self):
        return self.priv.encode(Base64Encoder)

    def sign(self, data: bytes) -> str:
        return (self.priv.sign(data, encoder=Base64Encoder)
                .signature
                .decode('ascii'))

    def to_identity(self) -> Identity:
        return Identity(self.pub)
