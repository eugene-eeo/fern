import json
import sqlite3
import base64
from fern.entry import Entry
from fern.identity import Identity


CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS log (
    id        CHAR(45) PRIMARY KEY,
    previous  CHAR(45),
    sequence  INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    author    CHAR(45),
    type      VARCHAR,
    data      BLOB,
    signature CHAR(88),
    UNIQUE(author, sequence)
)
"""


class Log:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        with self.db:
            self.db.execute(CREATE_TABLES)

    def store(self, entry: Entry):
        with self.db:
            self.db.execute(
                'INSERT INTO log(id,previous,sequence,timestamp,'
                'author,type,data,signature) VALUES (?,?,?,?,?,?,?,?)', (
                    entry.id,
                    entry.previous,
                    entry.sequence,
                    entry.timestamp,
                    str(entry.author),
                    entry.type,
                    json.dumps(entry.encode_data()),
                    entry.signature,
                ))

    def get_followed_by(self, author: Identity):
        rows = self.db.execute(
            'SELECT data, type FROM log '
            'WHERE log.author = ? AND (log.type = "follow" OR log.type = "unfollow") '
            'ORDER BY log.sequence',
            (str(author),))
        followed = set()
        for (id, type) in rows:
            id = base64.b64decode(id)
            if type == "follow":
                followed.add(id)
            else:
                followed.discard(id)
        return {Identity.from_id(b.decode('ascii')) for b in followed}
