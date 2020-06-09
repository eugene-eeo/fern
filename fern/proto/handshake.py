from nacl.bindings.utils import sodium_memcmp
from nacl.public import PrivateKey, Box, PublicKey
from nacl.utils import random
from fern.identity import Identity, LocalIdentity


class BadHandshake(Exception):
    pass


def client_handshake(
    client_id: LocalIdentity,
    server_id: Identity,
    conn,  # Conn should have .read and .write
) -> Box:

    client_pk = PrivateKey.generate()  # ephemeral client-side key
    nonce = random(size=64)

    msg = nonce + client_pk.public_key.encode()  # 64 + 32 = 96
    msg = client_id.priv.sign(msg)

    # send ( N_c || P_c || s_c(N_c || P_c) )
    conn.write(msg)

    # receive ( N_c || P_s || s_s(N_c || P_s) )
    res = conn.read(160)  # type: bytes
    res = server_id.pub.verify(res)

    res_nonce = res[:64]
    if not sodium_memcmp(nonce, res_nonce):
        raise BadHandshake

    server_pubkey = PublicKey(res[64:])
    box = Box(client_pk, server_pubkey)

    conn.write(box.encrypt(b"box"))
    txt = conn.read(43)
    if not sodium_memcmp(box.decrypt(txt), b"box"):
        raise BadHandshake

    return box


def server_handshake(
    server_id: LocalIdentity,
    client_id: Identity,
    conn,
) -> Box:

    server_pk = PrivateKey.generate()

    # receive ( N_c || P_c || s_c(N_c || P_c) )
    req = conn.read(160)  # type: bytes
    req = client_id.pub.verify(req)

    nonce = req[:64]
    client_pubkey = PublicKey(req[64:])

    res = nonce + server_pk.public_key.encode()  # 128 + 32 = 160
    res = server_id.priv.sign(res)

    # send ( N_c || P_s || s_c(N_c || P_s) )
    conn.write(res)
    box = Box(server_pk, client_pubkey)

    conn.write(box.encrypt(b"box"))
    txt = conn.read(43)
    if not sodium_memcmp(box.decrypt(txt), b"box"):
        raise BadHandshake

    return box
