import json
import sqlite3
from fern.entry import Entry


CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS log (
    row_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    id        CHAR(45) NOT NULL,
    prev      CHAR(45),
    seq       INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    author    CHAR(45) NOT NULL,
    type      VARCHAR NOT NULL,
    data      BLOB NOT NULL,
    sig       CHAR(88) NOT NULL,
    UNIQUE(author, seq),
    UNIQUE(id)
)
"""


class Log:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        with self.db:
            self.db.execute(CREATE_TABLES)

    def store(self, entries: [Entry]):
        with self.db:
            self.db.executemany(
                'INSERT INTO log(id,prev,seq,timestamp,author,type,data,sig) '
                'VALUES (?,?,?,?,?,?,?,?)', [(
                    entry.id,
                    entry.previous,
                    entry.sequence,
                    entry.timestamp,
                    str(entry.author),
                    entry.type,
                    json.dumps(Entry.encode_data(entry.data)),
                    entry.signature,
                ) for entry in entries])

    def get_entries(self, last_row_id: int = 0):
        rows = self.db.execute(
            'SELECT * FROM log WHERE log.row_id > ?',
            (last_row_id,),
        )
        for row in rows:
            row = dict(row)
            row["data"] = json.loads(row["data"])
            yield row["row_id"], Entry.from_json(row)
