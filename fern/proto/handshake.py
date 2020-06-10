import nacl.hash
from nacl.bindings.crypto_scalarmult import crypto_scalarmult
from nacl.secret import SecretBox
from nacl.public import PrivateKey, PublicKey
from nacl.signing import VerifyKey
from nacl.encoding import RawEncoder
from fern.identity import Identity, LocalIdentity
from fern.proto.stream import BoxStream


class BadHandshake(Exception):
    pass


def sha256(msg):
    return nacl.hash.sha256(msg, encoder=RawEncoder)


def client_handshake(
    client_id: LocalIdentity,
    server_id: Identity,
    conn,  # Conn should have .read and .write
) -> BoxStream:
    client_priv = PrivateKey.generate()  # Ephemeral PK

    # Send eph pubkey
    conn.write(client_priv.public_key.encode())  # 32 bytes

    # Get server pubkey
    server_pub = PublicKey(conn.read(32))

    ab = crypto_scalarmult(client_priv.encode(), server_pub.encode())
    aB = crypto_scalarmult(client_priv.encode(), server_id.pub.to_curve25519_public_key().encode())

    # Send our ID
    proof = server_pub.encode() + sha256(ab)
    sig = client_id.priv.sign(proof).signature
    msg = SecretBox(sha256(ab + aB)).encrypt(
        sig + client_id.pub.encode(),  # 64 + 32
        nonce=bytes(24),
    ).ciphertext
    conn.write(msg)  # 112 bytes

    Ab = crypto_scalarmult(
        client_id.priv.to_curve25519_private_key().encode(),
        server_pub.encode(),
    )

    sbox = SecretBox(sha256(ab + aB + Ab))
    server_sig = conn.read(80)
    server_sig = sbox.decrypt(server_sig, nonce=bytes(24))
    server_id.pub.verify(
        smessage=sig + client_id.pub.encode() + sha256(ab),
        signature=server_sig,
    )

    return BoxStream(
        sbox,
        send_nonce=server_pub.encode()[:24],
        recv_nonce=client_priv.public_key.encode()[:24],
        conn=conn,
    )


def server_handshake(
    server_id: LocalIdentity,
    conn,  # Conn should have .read and .write
) -> (Identity, BoxStream):
    server_priv = PrivateKey.generate()  # Ephemeral PK

    # Recv eph pubkey
    client_pub = PublicKey(conn.read(32))

    # Send our eph pubkey
    conn.write(server_priv.public_key.encode())  # 32 bytes

    ab = crypto_scalarmult(server_priv.encode(), client_pub.encode())
    aB = crypto_scalarmult(server_id.priv.to_curve25519_private_key().encode(), client_pub.encode())

    msg = conn.read(112)
    msg = SecretBox(sha256(ab + aB)).decrypt(msg, nonce=bytes(24))
    sig = msg[:64]
    client_id = Identity(VerifyKey(msg[64:]))

    # Verify
    client_id.pub.verify(
        smessage=server_priv.public_key.encode() + sha256(ab),
        signature=sig,
    )

    Ab = crypto_scalarmult(
        server_priv.encode(),
        client_id.pub.to_curve25519_public_key().encode(),
    )

    sbox = SecretBox(sha256(ab + aB + Ab))
    msg = sbox.encrypt(
        server_id.priv.sign(sig + client_id.pub.encode() + sha256(ab)).signature,
        nonce=bytes(24),
    )
    conn.write(msg.ciphertext)  # 80 bytes

    return (
        client_id,
        BoxStream(
            sbox,
            send_nonce=client_pub.encode()[:24],
            recv_nonce=server_priv.public_key.encode()[:24],
            conn=conn,
        )
    )
