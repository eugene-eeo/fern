import asyncio
from fern.identity import LocalIdentity
from fern.entry import build_entry
from fern.store.log import get_db, init_db, get_last_entry_info, store_entry, transaction


async def main():
    id = LocalIdentity.generate()
    db = get_db(':memory:')
    async with db:
        await init_db(db)
        async with transaction(db):
            await store_entry(db, build_entry(
                author=id,
                previous=None,
                sequence=1,
                timestamp=0,
                type="post",
                data=b"Hello world!",
            ))
            print(db.in_transaction)
            print(await get_last_entry_info(db, id))


if __name__ == '__main__':
    asyncio.run(main())
