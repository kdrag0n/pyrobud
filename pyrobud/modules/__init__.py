import logging
import pkgutil
from importlib import reload as _importlib_reload
from pathlib import Path
from typing import Sequence

log = logging.getLogger("metamod")


def reload() -> None:
    log.info("Reloading module classes")
    for sym in __all__:
        module = globals()[sym]
        _importlib_reload(module)


__all__: Sequence[str] = list(info.name for info in pkgutil.iter_modules([str(Path(__file__).parent)]))

from . import *  # isort:skip


try:
    _reload_flag: bool

    # noinspection PyUnboundLocalVariable
    if _reload_flag:
        # Module has been reloaded, reload our submodules
        reload()
except NameError:
    _reload_flag = True
