import logging
import os
from pathlib import Path
from typing import Any, MutableMapping, Union

import tomlkit
import tomlkit.toml_document

from .config_db_migrator import upgrade_v3

Config = MutableMapping[str, Any]
BotConfig = MutableMapping[str, Union[str, bool]]
AsyncIOConfig = MutableMapping[str, bool]

log = logging.getLogger("migrate")


def save(config: Config, _path: str) -> None:
    if not isinstance(config, tomlkit.toml_document.TOMLDocument):
        raise TypeError("Only tomlkit saving is supported for now")

    path = Path(_path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    done = False
    config_data = tomlkit.dumps(config)

    try:
        with tmp_path.open("w+") as f:
            f.write(config_data)
            f.flush()
            os.fsync(f.fileno())

        tmp_path.replace(path)
        done = True
    finally:
        if not done:
            tmp_path.unlink()


def upgrade_v2(config: Config) -> None:
    tg_config: MutableMapping[str, str] = config["telegram"]

    if "session_name" not in tg_config:
        log.info("Adding default session name 'main' to Telegram config section")
        tg_config["session_name"] = "main"

        sess_db = Path("anon.session")
        sess_db_journal = Path("anon.session-journal")
        if sess_db.exists():
            log.info("Renaming 'anon' session to 'main'")
            sess_db.rename("main.session")
        if sess_db_journal.exists():
            sess_db_journal.rename("main.session-journal")


def upgrade_v4(config: Config) -> None:
    bot_config: BotConfig = config["bot"]

    if "report_errors" not in bot_config:
        log.info("Enabling error reporting by default without usernames")
        log.info("Please consider enabling report_username if you're comfortable with it!")
        bot_config["report_errors"] = True
        bot_config["report_username"] = False


def upgrade_v5(config: Config) -> None:
    bot_config: BotConfig = config["bot"]

    if "sentry_dsn" not in bot_config:
        log.info("Adding default Sentry DSN to bot config section")
        bot_config["sentry_dsn"] = ""


def upgrade_v6(config: Config) -> None:
    bot_config: BotConfig = config["bot"]

    if "response_mode" not in bot_config:
        log.info("Setting response mode to default 'edit'")
        bot_config["response_mode"] = "edit"


def upgrade_v7(config: Config) -> None:
    bot_config: BotConfig = config["bot"]

    if "redact_responses" not in bot_config:
        log.info("Enabling response redaction by default")
        bot_config["redact_responses"] = True


def upgrade_v8(config: Config) -> None:
    if "asyncio" not in config:
        config["asyncio"] = {}

    asyncio_config: AsyncIOConfig = config["asyncio"]

    if "use_uvloop" not in asyncio_config:
        log.info("Enabling uvloop usage by default")
        asyncio_config["use_uvloop"] = True


def upgrade_v9(config: Config) -> None:
    asyncio_config: AsyncIOConfig = config["asyncio"]

    if "debug" not in asyncio_config:
        log.info("Disabling asyncio debug mode by default")
        asyncio_config["debug"] = False


# Old version -> function to perform migration to new version
upgrade_funcs = [
    upgrade_v2,
    upgrade_v3,
    upgrade_v4,
    upgrade_v5,
    upgrade_v6,
    upgrade_v7,
    upgrade_v8,
    upgrade_v9,
]


# Master upgrade function
def upgrade(config: Config, path: str) -> None:
    # Get current version
    cur_version: int = config["version"] if "version" in config else 1

    # Already at latest version; nothing to do
    if cur_version == len(upgrade_funcs) + 1:
        return

    # Upgrade each version sequentially
    for upgrader in upgrade_funcs[cur_version - 1 :]:
        target_version = cur_version + 1
        log.info(f"Upgrading config to version {target_version}")
        upgrader(config)
        cur_version = target_version
        config["version"] = target_version

        # Save config ASAP to prevent an inconsistent state if the next upgrade fails
        save(config, path)
