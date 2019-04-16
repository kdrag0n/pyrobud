import importlib
import pkgutil
import os

__all__ = list(module for _, module, _ in pkgutil.iter_modules([os.path.dirname(__file__)]))

from . import *

try:
    _reload_flag
except:
    _reload_flag = True
else:
    # Module has been reloaded, reload our submodules
    print('Reloading module classes...')
    for sym in __all__:
        module = globals()[sym]
        importlib.reload(module)
