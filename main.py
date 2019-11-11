#!/usr/bin/env python3

import asyncio
import logging

import colorlog
import toml
import uvloop

import util
from bot import Bot

LOG_LEVEL = logging.INFO
LOG_FORMAT = "  %(log_color)s%(levelname)-8s%(reset)s | %(name)-7s | %(log_color)s%(message)s%(reset)s"

log = logging.getLogger("wrapper")


def setup_logging():
    logging.root.setLevel(LOG_LEVEL)
    formatter = colorlog.ColoredFormatter(LOG_FORMAT)

    stream = logging.StreamHandler()
    stream.setLevel(LOG_LEVEL)
    stream.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    root.addHandler(stream)


def main():
    config_path = "config.toml"

    setup_logging()

    log.info("Loading config")
    config = toml.load(config_path)

    if "version" not in config or config["version"] < 2:
        log.info("Upgrading config to version 2")
        util.config.upgrade_v2(config, config_path)

    log.info("Initializing bot")
    bot = Bot(config, config_path)

    log.info("Starting bot")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.start())

    bot.client.run_until_disconnected()

    log.info("Stopping bot")
    loop.run_until_complete(bot.stop())


if __name__ == "__main__":
    uvloop.install()
    main()
