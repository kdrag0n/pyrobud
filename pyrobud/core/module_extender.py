import importlib
import inspect
import os
from types import ModuleType
from typing import TYPE_CHECKING, Any, MutableMapping, Optional, Type

from .. import custom_modules, module, modules, util
from .bot_mixin_base import MixinBase

if TYPE_CHECKING:
    from .bot import Bot


class ModuleExtender(MixinBase):
    # Initialized during instantiation
    modules: MutableMapping[str, module.Module]

    def __init__(self: "Bot", **kwargs: Any) -> None:
        # Initialize module map
        self.modules = {}

        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    def load_module(self: "Bot", cls: Type[module.Module], *, comment: Optional[str] = None) -> None:
        _comment = comment + " " if comment else ""
        self.log.info(
            f"Loading {_comment}module '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"
        )

        if cls.name in self.modules:
            old = type(self.modules[cls.name])
            raise module.ExistingModuleError(old, cls)

        mod = cls(self)
        mod.comment = comment
        self.register_listeners(mod)
        self.register_commands(mod)
        self.modules[cls.name] = mod

    def unload_module(self: "Bot", mod: module.Module) -> None:
        _comment = mod.comment + " " if mod.comment else ""

        cls = type(mod)
        path = os.path.relpath(inspect.getfile(cls))
        self.log.info(f"Unloading {_comment}module '{cls.name}' ({cls.__name__}) from '{path}'")

        self.unregister_listeners(mod)
        self.unregister_commands(mod)
        del self.modules[cls.name]

    def _load_modules_from_metamod(self: "Bot", metamod: ModuleType, *, comment: str = None) -> None:
        for _sym in getattr(metamod, "__all__", ()):
            module_mod: ModuleType = getattr(metamod, _sym)

            if inspect.ismodule(module_mod):
                for sym in dir(module_mod):
                    cls = getattr(module_mod, sym)
                    if inspect.isclass(cls) and issubclass(cls, module.Module):
                        self.load_module(cls, comment=comment)

    def load_all_modules(self: "Bot") -> None:
        self.log.info("Loading modules")
        self._load_modules_from_metamod(modules)
        self._load_modules_from_metamod(custom_modules, comment="custom")
        self.log.info("All modules loaded.")

    def unload_all_modules(self: "Bot") -> None:
        self.log.info("Unloading modules...")

        # Can't modify while iterating, so collect a list first
        for mod in list(self.modules.values()):
            self.unload_module(mod)

        self.log.info("All modules unloaded.")

    async def reload_module_pkg(self: "Bot") -> None:
        self.log.info("Reloading base module class...")
        await util.run_sync(importlib.reload, module)

        self.log.info("Reloading master module...")
        await util.run_sync(importlib.reload, modules)

        self.log.info("Reloading custom master module...")
        await util.run_sync(importlib.reload, custom_modules)
