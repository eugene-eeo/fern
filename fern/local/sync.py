import json
import base64
from fern.identity import Identity
from fern.proto.stream import RPCStream
from fern.proto.rpc import Response, Request
from fern.local.server import Handler, expose


class SyncHandler(Handler):
    prefix = 'sync'

    @expose
    async def follows(self, s: RPCStream, r: Request):
        id = r.args.get('id', str(self.config.get_local_identity()))
        id = Identity.from_id(id)

        async with self.get_db() as db:
            cursor = await db.execute(
                'SELECT type, data FROM log WHERE log.author = ? AND '
                '(log.type = "follow" OR log.type = "unfollow")',
                (str(id),)
            )
            follows = set()
            async for type, data in cursor:
                if type == 'follow':
                    follows.add(base64.b64decode(json.loads(data)).decode('ascii'))
                elif type == 'unfollow':
                    follows.discard(base64.b64decode(json.loads(data)).decode('ascii'))

        res = Response(id=r.id, content=list(follows))
        await res.send(s)
