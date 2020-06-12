from datetime import datetime
from fern.proto.rpc import Response, Request
from fern.local.server import expose, Handler
from fern.store.log import get_last_entry_info, transaction, store_entry
from fern.entry import build_entry


async def store_entry_prefill(db, id, type, data):
    previous, seq = await get_last_entry_info(db, id.to_identity())
    async with transaction(db):
        entry = build_entry(
            author=id,
            previous=previous,
            sequence=seq + 1,
            timestamp=int(datetime.utcnow().timestamp()),
            type=type,
            data=data,
        )
        await store_entry(db, entry)
    return entry


class FeedHandler(Handler):
    prefix = 'feed'

    @expose
    async def follow(self, stream, req):
        assert isinstance(req.args['id'], str)

        id = self.config.get_local_identity()
        async with self.get_db() as db:
            entry = await store_entry_prefill(
                db=db,
                id=id,
                type='follow',
                data=req.args['id'].encode('utf-8'),
            )

        res = Response(id=req.id, content={"id": entry.id})
        await res.send(stream)

    @expose
    async def unfollow(self, stream, req):
        assert isinstance(req.args['id'], str)

        id = self.config.get_local_identity()
        async with self.get_db() as db:
            entry = await store_entry_prefill(
                db=db,
                id=id,
                type='unfollow',
                data=req.args['id'].encode('utf-8'),
            )

        res = Response(id=req.id, content={"id": entry.id})
        await res.send(stream)

    @expose
    async def post(self, stream, req: Request):
        assert 'data' in req.args and isinstance(req.args['data'], str)

        id = self.config.get_local_identity()
        async with self.get_db() as db:
            entry = await store_entry_prefill(
                db=db,
                id=id,
                type='post',
                data=req.args['data'].encode('utf-8'),
            )

        res = Response(id=req.id, content={"id": entry.id})
        await res.send(stream)

    @expose
    async def add(self, stream, req: Request):
        assert 'type' in req.args and isinstance(req.args['type'], str)
        assert 'data' in req.args and isinstance(req.args['data'], (str, dict))

        id = self.config.get_local_identity()
        async with self.get_db() as db:
            entry = await store_entry_prefill(
                db=db,
                id=id,
                type=req.args['type'],
                data=(
                    req.args['data'].encode('utf-8')
                    if isinstance(req.args['data'], str)
                    else req.args['data']
                ),
            )

        res = Response(id=req.id, content={"id": entry.id})
        await res.send(stream)

    @expose
    async def digest(self, stream, req: Request):
        async with self.get_db() as db:
            cursor = await db.execute(
                'SELECT id, author, seq FROM log ORDER BY author, seq',
            )
            digest = {}
            async for id, author, seq in cursor:
                if author not in digest:
                    if seq == 1:
                        digest[author] = (seq, id)
                    continue
                prev_seq, _ = digest[author]
                if prev_seq == seq - 1:
                    digest[author] = (seq, id)

            res = Response(id=req.id, content={k: id for k, (_, id) in digest.items()})
            await res.send(stream)
