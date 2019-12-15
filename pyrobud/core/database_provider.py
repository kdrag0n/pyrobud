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
        self._db = util.db.AsyncDB(plyvel.DB(self.config["bot"]["db_path"], create_if_missing=True))
        self.db = self.get_db("bot")

        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    def get_db(self: "Bot", prefix: str) -> util.db.AsyncDB:
        return self._db.prefixed_db(prefix + ".")
