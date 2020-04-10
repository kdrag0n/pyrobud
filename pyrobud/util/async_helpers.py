import asyncio
import functools
from typing import Any, Callable, TypeVar

Result = TypeVar("Result")


async def run_sync(func: Callable[..., Result], *args: Any, **kwargs: Any) -> Result:
    """Runs the given sync function (optionally with arguments) on a separate thread."""

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
