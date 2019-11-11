import logging
import os

import toml

log = logging.getLogger("migration")


def save(config, path):
    tmp_path = path + ".tmp"

    try:
        with open(tmp_path, "w+") as f:
            toml.dump(config, f)
            f.flush()
            os.fsync(f.fileno())

        os.rename(tmp_path, path)
    except:
        os.remove(tmp_path)
        raise


def upgrade_v2(config, path):
    tg_config = config["telegram"]

    if "session_name" not in tg_config:
        log.info("Adding default session name 'main' to Telegram config section")
        tg_config["session_name"] = "main"

        if os.path.exists("anon.session"):
            log.info("Renaming 'anon' session to 'main'")
            os.rename("anon.session", "main.session")
        if os.path.exists("anon.session-journal"):
            os.rename("anon.session-journal", "main.session-journal")

    config["version"] = 2
    save(config, path)
