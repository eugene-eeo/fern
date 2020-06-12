import os
import uvloop
import asyncio
from fern.config import Config
from fern.local.server import LocalRPC
from fern.local.feed import FeedHandler
from fern.local.sync import SyncHandler

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

if os.path.exists('./log.sqlite'):
    os.remove('./log.sqlite')

local = LocalRPC(Config(
    secret_path="./priv",
    log_path="./log.sqlite",
    local_tcp_addr="localhost:9110",
    sync_addr=":8998",
    broadcast_addr="127.255.255.255:9219",
), handlers=[
    FeedHandler,
    SyncHandler,
])
print(local.handlers)
asyncio.run(local.serve())
