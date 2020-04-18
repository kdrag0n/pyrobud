import collections.abc
import logging
import os
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Union

import tomlkit
import tomlkit.toml_document

from .async_helpers import run_sync
from .config_db_migrator import upgrade_v3

Config = MutableMapping[str, Any]
BotConfig = MutableMapping[str, Union[str, bool]]
AsyncIOConfig = MutableMapping[str, bool]

log = logging.getLogger("migrate")


class Dummy:
    pass


DeleteValue = Dummy()


def save(config: Config, _path: str) -> None:
    """Saves the given config to the given path as a TOML file."""

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


# Source: https://stackoverflow.com/a/3233356
def _recursive_update(d: MutableMapping, u: Mapping) -> MutableMapping:  # sourcery off
    for k, v in u.items():
        if v is DeleteValue:
            del d[k]
            continue

        if isinstance(v, collections.abc.Mapping):
            d[k] = _recursive_update(d.get(k, {}), v)
        else:
            d[k] = v

    return d


async def _upgrade_v2(config: Config) -> None:
    tg_config: MutableMapping[str, str] = config["telegram"]

    if "session_name" not in tg_config:
        log.info("Adding default session name 'main' to Telegram config section")
        tg_config["session_name"] = "main"

        sess_db = Path("anon.session")
        sess_db_journal = Path("anon.session-journal")
        if await run_sync(sess_db.exists):
            log.info("Renaming 'anon' session to 'main'")
            await run_sync(sess_db.rename, "main.session")
        if await run_sync(sess_db_journal.exists):
            await run_sync(sess_db_journal.rename, "main.session-journal")


# Functions or dicts to merge to migrate each version
upgrade_methods = [
    _upgrade_v2,  # Session rename
    upgrade_v3,  # Large config->DB migration
    {"version": 4, "bot": {"report_errors": True, "report_username": False}},
    {"version": 5, "bot": {"sentry_dsn": ""}},
    {"version": 6, "bot": {"response_mode": "edit"}},
    {"version": 7, "bot": {"redact_responses": True}},
    {"version": 8, "asyncio": {"use_uvloop": True}},
    {"version": 9, "asyncio": {"debug": False}},
    {"version": 10, "asyncio": {"use_uvloop": DeleteValue, "disable_uvloop": False}},
]


# Master upgrade function
async def upgrade(config: Config, path: str) -> None:
    """Upgrades given config until it's completely up to date."""

    # Get current version
    cur_version: int = config["version"] if "version" in config else 1

    # Already at latest version; nothing to do
    if cur_version == len(upgrade_methods) + 1:
        return

    # Upgrade each version sequentially
    for upgrader in upgrade_methods[cur_version - 1 :]:
        # Deduce and log target version
        target_version = cur_version + 1
        log.info(f"Upgrading config to version {target_version}")

        # Perform upgrade
        if callable(upgrader):
            await upgrader(config)
        elif isinstance(upgrader, dict):
            _recursive_update(config, upgrader)
        else:
            raise TypeError(
                f"Unrecognized upgrader type {type(upgrader)} for version {target_version}"
            )

        # Account for the upgrade
        cur_version = target_version
        config["version"] = target_version

        # Save config ASAP to prevent an inconsistent state if the next upgrade fails
        await run_sync(save, config, path)
