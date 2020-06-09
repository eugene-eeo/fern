from fern.identity import LocalIdentity
from fern.entry import build_entry
from fern.store.log import Log

my_id = LocalIdentity.generate()
alice = LocalIdentity.generate()
bob   = LocalIdentity.generate()


log = Log(':memory:')
entry = build_entry(author=my_id, previous=None, sequence=1, timestamp=0, type="msg", data=b"hello world!")
log.store(entry)
log.store(build_entry(author=my_id, previous=entry.id, sequence=2, timestamp=0, type="msg", data={"yo": "hey! 中文"}))
