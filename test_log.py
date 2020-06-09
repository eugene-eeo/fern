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
log.store(e1)
log.store(e2)
log.store(e3)
print(log.get_followed_by(my_id.to_identity()))
