import orjson
from aiosqlite import Connection, connect

from contextlib import asynccontextmanager
from typing import Tuple
from fern.entry import Entry
from fern.identity import Identity


SCHEMA = '''
CREATE TABLE IF NOT EXISTS log (
    id        CHAR(45) NOT NULL,
    prev      CHAR(45),
    author    CHAR(45) NOT NULL,
    seq       INTEGER,
    timestamp INTEGER NOT NULL,
    type      VARCHAR NOT NULL,
    data      BLOB,
    sig       CHAR(88),
    UNIQUE(author, seq)
)
'''


def get_db(path: str) -> Connection:
    return connect(path)


async def init_db(db: Connection):
    await db.execute(SCHEMA)
    await db.commit()


@asynccontextmanager
async def transaction(db: Connection):
    try:
        yield db
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise exc


async def get_last_entry_info(
    db: Connection,
    id: Identity,
) -> Tuple[str, int]:
    cursor = await db.execute(
        'SELECT id, MAX(seq) FROM log WHERE author = ?',
        (str(id),),
    )
    rows = await cursor.fetchall()
    if len(rows) == 0 or rows[0][0] is None:
        return None, 0
    id, seq = rows[0]
    return id, seq


async def store_entry(db: Connection, entry: Entry):
    # assume that entry is verified
    await db.execute(
        'INSERT INTO log (id, prev, author, seq, timestamp, type, data, sig) VALUES '
        '(?,?,?,?,?,?,?,?)',
        (entry.id,
         entry.previous,
         str(entry.author),
         entry.sequence,
         entry.timestamp,
         entry.type,
         orjson.dumps(Entry.encode_data(entry.data)),
         entry.signature),
    )
