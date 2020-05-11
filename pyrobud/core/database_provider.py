from typing import TYPE_CHECKING, Any

import plyvel

from .. import util
from .bot_mixin_base import MixinBase

if TYPE_CHECKING:
    from .bot import Bot


class DatabaseProvider(MixinBase):
    # Initialized during instantiation
    _db: util.db.AsyncDB
    db: util.db.AsyncDB

    def __init__(self: "Bot", **kwargs: Any) -> None:
        # Initialize database
        db_path = self.config["bot"]["db_path"]
        try:
            self._init_db(db_path)
        except plyvel.IOError as e:
            if "Resource temporarily unavailable" in str(e):
                raise OSError(
                    f"Database '{db_path}' is in use by another process! Make sure no other bot instances are running before starting this again."
                )
            else:
                raise
        except plyvel.CorruptionError:
            self.log.warning("Database is corrupted, attempting to repair")
            plyvel.repair_db(db_path)
            self._init_db(db_path)

        self.db = self.get_db("bot")

        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    def _init_db(self: "Bot", db_path: str):
        self._db = util.db.AsyncDB(
            plyvel.DB(db_path, create_if_missing=True, paranoid_checks=True)
        )

    def get_db(self: "Bot", prefix: str) -> util.db.AsyncDB:
        return self._db.prefixed_db(prefix + ".")
