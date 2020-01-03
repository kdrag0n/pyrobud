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

    def __init__(self, config: Config):
        # Save reference to config
        self.config = config

        # Initialize other objects
        self.log = logging.getLogger("bot")
        self.http = aiohttp.ClientSession()

        # Initialize mixins
        super().__init__()

    @classmethod
    async def create_and_run(cls, config: Config) -> "Bot":
        bot = cls(config)
        await bot.run()
        return bot

    async def stop(self) -> None:
        self.log.info("Stopping")
        await self.dispatch_event("stop")
        await self.http.close()
        await self._db.close()

        self.log.info("Running post-stop hooks")
        await self.dispatch_event("stopped")
