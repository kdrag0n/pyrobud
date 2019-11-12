import importlib
import logging
import os
import pkgutil

__all__ = list(module for _, module, _ in pkgutil.iter_modules([os.path.dirname(__file__)]))

from . import *


log = logging.getLogger("metamod")

try:
    _reload_flag = _reload_flag
except NameError:
    _reload_flag = True
else:
    # Module has been reloaded, reload our submodules
    log.info("Reloading module classes")
    for sym in __all__:
        module = globals()[sym]
        importlib.reload(module)
