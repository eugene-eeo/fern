from dataclasses import dataclass
from fern.identity import LocalIdentity


@dataclass
class Config:
    log_path: str        # path to store log entries
    local_tcp_addr: str  # path to host local tcp instance
    secret_path: str     # path to secret
    sync_addr: str       # addr to host sync server
    broadcast_addr: str  # addr to broadcast discovery packets

    def get_local_identity(self):
        return LocalIdentity.from_bytes(open(self.secret_path, 'rb').read().strip())
