import asyncio
import logging

import aiohttp
import telethon as tg

from ..util.config import Config
from .command_dispatcher import CommandDispatcher
from .database_provider import DatabaseProvider
from .event_dispatcher import EventDispatcher
from .module_extender import ModuleExtender
from .telegram_bot import TelegramBot


class Bot(TelegramBot, ModuleExtender, CommandDispatcher, DatabaseProvider, EventDispatcher):
    # Initialized during instantiation
    config: Config
    log: logging.Logger
    http: aiohttp.ClientSession
    client: tg.TelegramClient
    loop: asyncio.AbstractEventLoop
    stopping: bool

    def __init__(self, config: Config):
        self.config = config
        self.log = logging.getLogger("bot")
        self.loop = asyncio.get_event_loop()
        self.stopping = False

        # Initialize mixins
        super().__init__()

        # Initialize aiohttp session last in case another mixin fails
        self.http = aiohttp.ClientSession()

    @classmethod
    async def create_and_run(cls, config: Config) -> "Bot":
        bot = None

        try:
            bot = cls(config)
            await bot.run()
            return bot
        finally:
            if bot is None or (bot is not None and not bot.stopping):
                asyncio.get_event_loop().stop()

    async def stop(self) -> None:
        self.stopping = True

        self.log.info("Stopping")
        await self.dispatch_event("stop")
        await self.http.close()
        await self._db.close()

        self.log.info("Running post-stop hooks")
        await self.dispatch_event("stopped")
