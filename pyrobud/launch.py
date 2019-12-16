import asyncio
import logging
import sys

import aiorun
import tomlkit

from . import DEFAULT_CONFIG_PATH, util
from .core import Bot

log = logging.getLogger("launch")
# Silence aiorun's overly verbose logger
aiorun.logger.disabled = True


def setup_asyncio(config: util.config.Config) -> asyncio.AbstractEventLoop:
    asyncio_config: util.config.AsyncIOConfig = config["asyncio"]

    if sys.platform == "win32":
        # Force ProactorEventLoop on Windows for subprocess support
        asyncio.set_event_loop(asyncio.ProactorEventLoop())
    elif asyncio_config["use_uvloop"]:
        # Initialize uvloop if available and working
        try:
            # noinspection PyUnresolvedReferences
            import uvloop

            uvloop.install()
        except ImportError:
            log.warning("Unable to load uvloop; falling back to default asyncio event loop")

    loop = asyncio.get_event_loop()
    if asyncio_config["debug"]:
        log.warning("Enabling asyncio debug mode")
        loop.set_debug(True)

    return loop


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

    loop = setup_asyncio(config)

    log.info("Initializing bot")
    aiorun.run(Bot.create_and_run(config), loop=loop)
