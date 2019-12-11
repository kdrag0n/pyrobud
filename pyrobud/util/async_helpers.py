import asyncio
from typing import Callable, TypeVar

Result = TypeVar("Result")


async def run_sync(func: Callable[[], Result]) -> Result:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func)
