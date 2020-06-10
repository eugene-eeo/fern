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


async def client_handshake(
    client_id: LocalIdentity,
    server_id: Identity,
    conn,  # Conn should have .read and .write
) -> BoxStream:
    client_priv = PrivateKey.generate()  # Ephemeral PK

    # Send eph pubkey
    msg1 = client_priv.public_key.encode()
    await conn.write(msg1)  # 32 bytes

    # Get server pubkey
    msg2 = await conn.read(32)
    server_pub = PublicKey(msg2)

    ab = crypto_scalarmult(client_priv.encode(), server_pub.encode())
    aB = crypto_scalarmult(client_priv.encode(), server_id.pub.to_curve25519_public_key().encode())

    # Send our ID
    sig = client_id.priv.sign(server_pub.encode() + sha256(ab)).signature
    msg3 = SecretBox(sha256(ab + aB)).encrypt(
        sig + client_id.pub.encode(),  # 64 + 32
        nonce=bytes(24),
    )
    await conn.write(msg3.ciphertext)  # 112 bytes

    Ab = crypto_scalarmult(
        client_id.priv.to_curve25519_private_key().encode(),
        server_pub.encode(),
    )

    sbox = SecretBox(sha256(ab + aB + Ab))
    msg4 = await conn.read(80)
    server_id.pub.verify(
        smessage=sig + client_id.pub.encode() + sha256(ab),
        signature=sbox.decrypt(msg4, nonce=bytes(24)),
    )

    return BoxStream(
        sbox,
        send_nonce=server_pub.encode()[:24],
        recv_nonce=client_priv.public_key.encode()[:24],
        conn=conn,
    )


async def server_handshake(
    server_id: LocalIdentity,
    conn,  # Conn should have .read and .write
) -> (Identity, BoxStream):
    server_priv = PrivateKey.generate()  # Ephemeral PK

    # Recv eph pubkey
    msg1 = await conn.read(32)
    client_pub = PublicKey(msg1)

    # Send our eph pubkey
    msg2 = server_priv.public_key.encode()
    await conn.write(msg2)  # 32 bytes

    ab = crypto_scalarmult(server_priv.encode(), client_pub.encode())
    aB = crypto_scalarmult(server_id.priv.to_curve25519_private_key().encode(), client_pub.encode())

    msg3 = await conn.read(112)
    msg3 = SecretBox(sha256(ab + aB)).decrypt(msg3, nonce=bytes(24))
    sig = msg3[:64]
    client_id = Identity(VerifyKey(msg3[64:]))

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
    msg4 = sbox.encrypt(
        server_id.priv.sign(sig + client_id.pub.encode() + sha256(ab)).signature,
        nonce=bytes(24),
    )
    await conn.write(msg4.ciphertext)  # 80 bytes

    return (
        client_id,
        BoxStream(
            sbox,
            send_nonce=client_pub.encode()[:24],
            recv_nonce=server_priv.public_key.encode()[:24],
            conn=conn,
        )
    )
