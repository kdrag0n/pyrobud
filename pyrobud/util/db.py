from types import TracebackType
from typing import Any, Optional, Tuple, Type, TypeVar, Union, overload

import msgpack
import plyvel

from .async_helpers import run_sync

Value = TypeVar("Value")


def encode(value: Any) -> bytes:
    return msgpack.packb(value, use_bin_type=True)


def decode(value: bytes) -> Any:
    return msgpack.unpackb(value, raw=False)


class AsyncDB:
    """Simplified asyncio wrapper for plyvel that only supports string keys."""

    db: plyvel.DB
    prefix: Optional[str]

    def __init__(self, db: plyvel.DB) -> None:
        self.db = db

        # Inherit PrefixedDB's prefix attribute if applicable
        self.prefix = getattr(db, "prefix", None)

    # Core operations
    def put_sync(self, key: str, value: Any, **kwargs: Any) -> None:
        value = encode(value)
        return self.db.put(key.encode("utf-8"), value, **kwargs)

    async def put(self, key: str, value: Any, **kwargs: Any) -> None:
        return await run_sync(self.put_sync, key, value, **kwargs)

    @overload
    def get_sync(self, key: str, **kwargs: Any) -> Optional[Value]:
        pass

    @overload
    def get_sync(self, key: str, default: Value, **kwargs: Any) -> Value:
        pass

    def get_sync(self, key: str, default: Optional[Value] = None, **kwargs: Any) -> Optional[Value]:
        value: Optional[bytes] = self.db.get(key.encode("utf-8"), **kwargs)
        if value is None:
            # We re-implement this to disambiguate types
            return default

        return decode(value)

    @overload
    async def get(self, key: str, **kwargs: Any) -> Optional[Value]:
        pass

    @overload
    async def get(self, key: str, default: Value, **kwargs: Any) -> Value:
        pass

    async def get(self, key: str, default: Optional[Value] = None, **kwargs: Any) -> Optional[Value]:
        return await run_sync(self.get_sync, key, default, **kwargs)

    def delete_sync(self, key: str, **kwargs: Any) -> None:
        return self.db.delete(key.encode("utf-8"), **kwargs)

    async def delete(self, key: str, **kwargs: Any) -> None:
        return await run_sync(self.delete_sync, key, **kwargs)

    def close_sync(self) -> None:
        return self.db.close()

    async def close(self) -> None:
        return await run_sync(self.close_sync)

    # Extensions
    def snapshot_sync(self) -> "AsyncDB":
        return AsyncDB(self.db.snapshot())

    async def snapshot(self) -> "AsyncDB":
        return await run_sync(self.snapshot_sync)

    def prefixed_db(self, prefix: str) -> "AsyncDB":
        prefixed_db = self.db.prefixed_db(prefix.encode("utf-8"))
        return AsyncDB(prefixed_db)

    def inc_sync(self, key: str, delta: int = 1) -> None:
        old_value: int = self.get_sync(key, 0)
        return self.put_sync(key, old_value + delta)

    async def inc(self, key: str, delta: int = 1) -> None:
        return await run_sync(self.inc_sync, key, delta)

    def dec_sync(self, key: str, delta: int = 1) -> None:
        old_value: int = self.get_sync(key, 0)
        return self.put_sync(key, old_value - delta)

    async def dec(self, key: str, delta: int = 1) -> None:
        return await run_sync(self.dec_sync, key, delta)

    def has_sync(self, key: str, **kwargs: Any) -> bool:
        value: Optional[Any] = self.db.get(key.encode("utf-8"), **kwargs)
        return value is not None

    async def has(self, key: str, **kwargs: Any) -> bool:
        return await run_sync(self.has_sync, key, **kwargs)

    def clear_sync(self, **kwargs: Any) -> None:
        for key, _ in self.db:
            self.db.delete(key, **kwargs)

    async def clear(self, **kwargs: Any) -> None:
        async for key, _ in self:
            await self.delete(key, **kwargs)

    # Context manager support
    async def __aenter__(self) -> "AsyncDB":
        return self

    async def __aexit__(
        self, typ: Optional[Type[BaseException]], value: Optional[BaseException], tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    def __enter__(self) -> "AsyncDB":
        return self

    def __exit__(
        self, typ: Optional[Type[BaseException]], value: Optional[BaseException], tb: Optional[TracebackType],
    ) -> None:
        self.close_sync()

    # Iterator support
    def iterator(self, *args: Any, **kwargs: Union[bool, str, bytes]) -> "AsyncDBIterator":
        for key, value in kwargs.items():
            if isinstance(value, str):
                kwargs[key] = value.encode("utf-8")

        iterator = self.db.iterator(*args, **kwargs)
        return AsyncDBIterator(iterator)

    def __aiter__(self) -> "AsyncDBIterator":
        return self.iterator()


# Iterator wrapper
class AsyncDBIterator:
    def __init__(self, iterator: plyvel._plyvel.Iterator) -> None:
        self.iterator = iterator

    # Iterator core
    def __aiter__(self) -> "AsyncDBIterator":
        return self

    async def __anext__(self) -> Tuple[str, Any]:
        def _next() -> Tuple[bytes, bytes]:
            try:
                return next(self.iterator)
            except StopIteration:
                raise StopAsyncIteration

        tup = await run_sync(_next)
        return tup[0].decode("utf-8"), decode(tup[1])

    # Context manager support
    async def __aenter__(self) -> "AsyncDBIterator":
        return self

    async def __aexit__(
        self, typ: Optional[Type[BaseException]], value: Optional[BaseException], tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    async def close(self) -> None:
        return await run_sync(self.iterator.close)

    # plyvel extensions
    async def prev(self) -> Tuple[bytes, bytes]:
        return await run_sync(self.iterator.prev)

    async def seek_to_start(self) -> None:
        return await run_sync(self.iterator.seek_to_start)

    async def seek_to_stop(self) -> None:
        return await run_sync(self.iterator.seek_to_stop)

    async def seek(self, target: str) -> None:
        return await run_sync(self.iterator.seek, target.encode("utf-8"))
