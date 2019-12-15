import logging

import aiorun
import tomlkit

from . import DEFAULT_CONFIG_PATH, util
from .core import Bot

log = logging.getLogger("launch")
# Suppress most messages from aiorun's overly verbose logger
aiorun.logger.setLevel(logging.WARNING)


def get_use_uvloop(config: util.config.Config) -> bool:
    asyncio_config: util.config.AsyncIOConfig = config["asyncio"]

    # Initialize uvloop if enabled, available, and working
    if asyncio_config["use_uvloop"]:
        try:
            import uvloop
        except ImportError:
            log.warning("Unable to load uvloop; falling back to default asyncio event loop")
            return False
        else:
            return True


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

    use_uvloop = get_use_uvloop(config)
    log.info("Initializing bot")
    bot = Bot(config)

    aiorun.run(bot.run(), use_uvloop=use_uvloop)
