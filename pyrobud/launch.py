import asyncio
import logging

import tomlkit

from . import DEFAULT_CONFIG_PATH, util
from .bot import Bot

log = logging.getLogger("launch")


def setup_asyncio(config: util.config.Config) -> None:
    asyncio_config: util.config.AsyncIOConfig = config["asyncio"]

    # Initialize uvloop if enabled, available, and working
    if asyncio_config["use_uvloop"]:
        try:
            import uvloop

            uvloop.install()
        except ImportError:
            log.warning("Unable to load uvloop; falling back to default asyncio event loop")


def main(*, config_path: str = DEFAULT_CONFIG_PATH) -> None:
    log.info("Loading config")
    with open(config_path, "r") as f:
        config_data = f.read()
    config: util.config.Config = tomlkit.loads(config_data)

    # Initialize Sentry reporting here to exempt config syntax errors and query
    # the user's report_errors value, defaulting to enabled if not specified
    if config["bot"].get("report_errors", True):
        log.info("Initializing Sentry error reporting")
        util.sentry.init()

    util.config.upgrade(config, config_path)

    setup_asyncio(config)
    log.info("Initializing bot")
    bot = Bot(config)

    log.info("Starting bot")
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(bot.start())
    except KeyboardInterrupt:
        log.warning("Received interrupt while connecting; exiting")
        return

    bot.client.run_until_disconnected()

    log.info("Stopping bot")
    loop.run_until_complete(bot.stop())
