import pprint
from fern.identity import LocalIdentity
from fern.entry import build_entry
from fern.store.log import Log

my_id = LocalIdentity.generate()
alice = LocalIdentity.generate()
bob   = LocalIdentity.generate()


log = Log(':memory:')
e1 = build_entry(author=my_id, previous=None, sequence=1, timestamp=0, type="follow", data=alice.to_bytes())
e2 = build_entry(author=my_id, previous=e1.id, sequence=2, timestamp=0, type="unfollow", data=alice.to_bytes())
e3 = build_entry(author=my_id, previous=e2.id, sequence=3, timestamp=0, type="follow", data=alice.to_bytes())
log.store([e1, e2, e3])
for row_id, entry in log.get_entries(0):
    print(row_id)
    pprint.pp(entry.to_json())
