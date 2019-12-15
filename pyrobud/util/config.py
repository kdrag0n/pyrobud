import logging
import os
from pathlib import Path
from typing import Any, List, MutableMapping, Sequence, Union

import plyvel
import tomlkit
import tomlkit.toml_document

from .db import AsyncDB
from .time import sec as now_sec

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


def upgrade_v2(config: Config, path: str) -> None:
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


def upgrade_v3(config: Config, path: str) -> None:
    def migrate_antibot() -> None:
        if "antibot" in config:
            log.info("Migrating antibot settings to database")
            mcfg: MutableMapping[str, Union[int, Sequence[int]]] = config["antibot"]
            mdb = db.prefixed_db("antibot.")

            if mcfg["threshold_time"] != 30:
                mdb.put_sync("threshold_time", mcfg["threshold_time"])

            if isinstance(mcfg["group_ids"], List):
                group_db = mdb.prefixed_db("groups.")
                for gid in mcfg["group_ids"]:
                    group_db.put_sync(f"{gid}.enabled", True)
                    group_db.put_sync(f"{gid}.enable_time", now_sec())

            del config["antibot"]

    def migrate_snippets() -> None:
        if "snippets" in config:
            log.info("Migrating snippets to database")
            mdb = db.prefixed_db("snippets.")

            for snip, repl in config["snippets"].items():
                mdb.put_sync(snip, repl)

            del config["snippets"]

    def migrate_stats() -> None:
        if "stats" in config:
            log.info("Migrating stats to database")
            mdb = db.prefixed_db("stats.")

            for stat, value in config["stats"].items():
                mdb.put_sync(stat, value)

            del config["stats"]

    def migrate_stickers() -> None:
        if "stickers" in config:
            log.info("Migrating stickers to database")
            mdb = db.prefixed_db("stickers.")

            for sticker, value in config["stickers"].items():
                mdb.put_sync(sticker, value)

            del config["stickers"]

        if "user" in config:
            log.info("Migrating sticker settings to database")
            mcfg = config["user"]
            mdb = db.prefixed_db("sticker_settings.")

            if "kang_pack" in mcfg:
                mdb.put_sync("kang_pack", mcfg["kang_pack"])

            del config["user"]

    bot_config: BotConfig = config["bot"]

    if "default_prefix" not in bot_config:
        log.info("Renaming 'prefix' key to 'default_prefix' in bot config section")
        bot_config["default_prefix"] = bot_config["prefix"]
        del bot_config["prefix"]

    if "db_path" not in bot_config:
        log.info("Adding default database path 'main.db' to bot config section")
        bot_config["db_path"] = "main.db"

    with AsyncDB(plyvel.DB(config["bot"]["db_path"], create_if_missing=True)) as db:
        migrate_antibot()
        migrate_snippets()
        migrate_stats()
        migrate_stickers()


def upgrade_v4(config: Config, _: str) -> None:
    bot_config: BotConfig = config["bot"]

    if "report_errors" not in bot_config:
        log.info("Enabling error reporting by default without usernames")
        log.info("Please consider enabling report_username if you're comfortable with it!")
        bot_config["report_errors"] = True
        bot_config["report_username"] = False


def upgrade_v5(config: Config, _: str) -> None:
    bot_config: BotConfig = config["bot"]

    if "sentry_dsn" not in bot_config:
        log.info("Adding default Sentry DSN to bot config section")
        bot_config["sentry_dsn"] = ""


def upgrade_v6(config: Config, _: str) -> None:
    bot_config: BotConfig = config["bot"]

    if "response_mode" not in bot_config:
        log.info("Setting response mode to default 'edit'")
        bot_config["response_mode"] = "edit"


def upgrade_v7(config: Config, _: str) -> None:
    bot_config: BotConfig = config["bot"]

    if "redact_responses" not in bot_config:
        log.info("Enabling response redaction by default")
        bot_config["redact_responses"] = True


def upgrade_v8(config: Config, _: str) -> None:
    if "asyncio" not in config:
        config["asyncio"] = {}

    asyncio_config: AsyncIOConfig = config["asyncio"]

    if "use_uvloop" not in asyncio_config:
        log.info("Enabling uvloop usage by default")
        asyncio_config["use_uvloop"] = True


# Old version -> function to perform migration to new version
upgrade_funcs = [
    upgrade_v2,  # 1 -> 2
    upgrade_v3,  # 2 -> 3
    upgrade_v4,  # 3 -> 4
    upgrade_v5,  # 4 -> 5
    upgrade_v6,  # 5 -> 6
    upgrade_v7,  # 6 -> 7
    upgrade_v8,  # 7 -> 8
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
        upgrader(config, path)
        cur_version = target_version
        config["version"] = target_version

        # Save config ASAP to prevent an inconsistent state if the next upgrade fails
        save(config, path)
