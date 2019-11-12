import asyncio


async def run_sync(func):
    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, func)
    await future
    return future.result()
