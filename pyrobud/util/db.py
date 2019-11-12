import struct

import msgpack
import plyvel
from async_generator import asynccontextmanager

from .async_helpers import run_sync


def encode(value):
    return msgpack.packb(value, use_bin_type=True)


def decode(value):
    return msgpack.unpackb(value, raw=False)


class AsyncDB:
    """Simplified asyncio wrapper for plyvel that only supports string keys."""

    def __init__(self, db):
        self.db = db

        # Inherit PrefixedDB's prefix attribute if applicable
        if hasattr(db, "prefix"):
            self.prefix = db.prefix

    # Core operations
    def put_sync(self, key, value, **kwargs):
        value = encode(value)
        return self.db.put(key.encode("utf-8"), value, **kwargs)

    async def put(self, key, value, **kwargs):
        return await run_sync(lambda: self.put_sync(key, value, **kwargs))

    def get_sync(self, key, default=None, **kwargs):
        value = self.db.get(key.encode("utf-8"), **kwargs)

        if value is None:
            # We re-implement this to disambiguate types
            return default

        return decode(value)

    async def get(self, key, default=None, **kwargs):
        return await run_sync(lambda: self.get_sync(key, default, **kwargs))

    def delete_sync(self, key, **kwargs):
        return self.db.delete(key.encode("utf-8"), **kwargs)

    async def delete(self, key, **kwargs):
        return await run_sync(lambda: self.delete_sync(key, **kwargs))

    def close_sync(self):
        return self.db.close()

    async def close(self):
        return await run_sync(self.close_sync)

    # Extensions
    def snapshot_sync(self):
        return AsyncDB(self.db.snapshot())

    async def snapshot(self):
        return await run_sync(self.snapshot_sync)

    def prefixed_db(self, prefix):
        prefixed_db = self.db.prefixed_db(prefix.encode("utf-8"))
        return AsyncDB(prefixed_db)

    def inc_sync(self, key, delta=1):
        old_value = self.get_sync(key, 0)
        return self.put_sync(key, old_value + delta)

    async def inc(self, key, delta=1):
        return await run_sync(lambda: self.inc_sync(key, delta))

    def dec_sync(self, key, delta=1):
        old_value = self.get_sync(key, 0)
        return self.put_sync(key, old_value - delta)

    async def dec(self, key, delta=1):
        return await run_sync(lambda: self.dec_sync(key, delta))

    def has_sync(self, key, **kwargs):
        value = self.db.get(key.encode("utf-8"), **kwargs)
        return value is not None

    async def has(self, key, **kwargs):
        return await run_sync(lambda: self.has_sync(key, **kwargs))

    def clear_sync(self, **kwargs):
        for key, _ in self.db:
            self.db.delete(key, **kwargs)

    async def clear(self, **kwargs):
        async for key, _ in self:
            await self.delete(key, **kwargs)

    # Context manager support
    async def __aenter__(self):
        return self

    async def __aexit__(self, typ, value, tb):
        await self.close()

    def __enter__(self):
        return self

    def __exit__(self, typ, value, tb):
        self.close_sync()

    # Iterator support
    def iterator(self, *args, **kwargs):
        for key, value in kwargs.items():
            if isinstance(key, str):
                kwargs[key] = value.encode("utf-8")

        iterator = self.db.iterator(*args, **kwargs)
        return AsyncDBIterator(iterator)

    def __aiter__(self):
        return self.iterator()


# Iterator wrapper
class AsyncDBIterator:
    def __init__(self, iterator):
        self.iterator = iterator

    # Iterator core
    def __aiter__(self):
        return self

    async def __anext__(self):
        def _next():
            try:
                return next(self.iterator)
            except StopIteration:
                raise StopAsyncIteration

        tup = await run_sync(_next)
        return (tup[0].decode("utf-8"), decode(tup[1]))

    # Context manager support
    async def __aenter__(self):
        return self

    async def __aexit__(self, typ, value, tb):
        await self.close()

    async def close(self):
        return await run_sync(self.iterator.close)

    # plyvel extensions
    async def prev(self):
        return await run_sync(self.iterator.prev)

    async def seek_to_start(self):
        return await run_sync(self.iterator.seek_to_start)

    async def seek_to_stop(self):
        return await run_sync(self.iterator.seek_to_stop)

    async def seek(self, target):
        return await run_sync(lambda: self.iterator.seek(target.encode("utf-8")))
