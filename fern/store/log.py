import json
import sqlite3
from fern.entry import Entry


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
