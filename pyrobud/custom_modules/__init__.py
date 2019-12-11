import logging
import os
import pkgutil
from importlib import reload as _importlib_reload
from typing import List

log = logging.getLogger("metamod_custom")


def reload() -> None:
    log.info("Reloading custom module classes")
    for sym in __all__:
        module = globals()[sym]
        _importlib_reload(module)


__all__: List[str] = list(info.name for info in pkgutil.iter_modules([os.path.dirname(__file__)]))

from . import *


try:
    _reload_flag: bool

    # noinspection PyUnboundLocalVariable
    if _reload_flag:
        # Module has been reloaded, reload our submodules
        reload()
except NameError:
    _reload_flag = True
