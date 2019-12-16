import logging
from typing import TYPE_CHECKING, List, MutableMapping, Sequence, Union

import plyvel

from .db import AsyncDB
from .time import sec as now_sec

if TYPE_CHECKING:
    from .config import Config, BotConfig

log = logging.getLogger("migrate")


async def upgrade_v3(config: "Config") -> None:
    bot_config: "BotConfig" = config["bot"]

    if "default_prefix" not in bot_config:
        log.info("Renaming 'prefix' key to 'default_prefix' in bot config section")
        bot_config["default_prefix"] = bot_config["prefix"]
        del bot_config["prefix"]

    if "db_path" not in bot_config:
        log.info("Adding default database path 'main.db' to bot config section")
        bot_config["db_path"] = "main.db"

    async with AsyncDB(plyvel.DB(config["bot"]["db_path"], create_if_missing=True)) as db:
        await migrate_antibot(config, db)
        await migrate_snippets(config, db)
        await migrate_stats(config, db)
        await migrate_stickers(config, db)


async def migrate_antibot(config: "Config", db: AsyncDB) -> None:
    if "antibot" not in config:
        return

    log.info("Migrating antibot settings to database")
    mcfg: MutableMapping[str, Union[int, Sequence[int]]] = config["antibot"]
    mdb = db.prefixed_db("antibot.")

    if mcfg["threshold_time"] != 30:
        await mdb.put("threshold_time", mcfg["threshold_time"])

    if isinstance(mcfg["group_ids"], List):
        group_db = mdb.prefixed_db("groups.")
        for gid in mcfg["group_ids"]:
            await group_db.put(f"{gid}.enabled", True)
            await group_db.put(f"{gid}.enable_time", now_sec())

    del config["antibot"]


async def migrate_snippets(config: "Config", db: AsyncDB) -> None:
    if "snippets" in config:
        log.info("Migrating snippets to database")
        mdb = db.prefixed_db("snippets.")

        for snip, repl in config["snippets"].items():
            await mdb.put(snip, repl)

        del config["snippets"]


async def migrate_stats(config: "Config", db: AsyncDB) -> None:
    if "stats" in config:
        log.info("Migrating stats to database")
        mdb = db.prefixed_db("stats.")

        for stat, value in config["stats"].items():
            await mdb.put(stat, value)

        del config["stats"]


async def migrate_stickers(config: "Config", db: AsyncDB) -> None:
    if "stickers" in config:
        log.info("Migrating stickers to database")
        mdb = db.prefixed_db("stickers.")

        for sticker, value in config["stickers"].items():
            await mdb.put(sticker, value)

        del config["stickers"]

    if "user" in config:
        log.info("Migrating sticker settings to database")
        mcfg = config["user"]
        mdb = db.prefixed_db("sticker_settings.")

        if "kang_pack" in mcfg:
            await mdb.put("kang_pack", mcfg["kang_pack"])

        del config["user"]
