import inspect
import logging
import os.path
from typing import TYPE_CHECKING, ClassVar, Optional, Type

if TYPE_CHECKING:
    from .core import Bot
    from .command import Command


class Module:
    # Class variables
    name: ClassVar[str] = "Unnamed"
    disabled: ClassVar[bool] = False

    # Instance variables
    bot: "Bot"
    log: logging.Logger
    comment: Optional[str]

    def __init__(self, bot: "Bot") -> None:
        self.bot = bot
        self.log = logging.getLogger(type(self).name.lower().replace(" ", "_"))
        self.comment = None

    @classmethod
    def format_desc(cls, comment: Optional[str] = None):
        _comment = comment + " " if comment else ""
        return f"{_comment}module '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"

    def __repr__(self):
        return "<" + self.format_desc(self.comment) + ">"


class ModuleLoadError(Exception):
    pass


class ExistingModuleError(ModuleLoadError):
    old_module: Type[Module]
    new_module: Type[Module]

    def __init__(self, old_module: Type[Module], new_module: Type[Module]) -> None:
        super().__init__(
            f"Module '{old_module.name}' ({old_module.__name__}) already exists"
        )

        self.old_module = old_module
        self.new_module = new_module


class ExistingCommandError(ModuleLoadError):
    old_cmd: "Command"
    new_cmd: "Command"
    alias: bool

    def __init__(
        self, old_cmd: "Command", new_cmd: "Command", alias: bool = False
    ) -> None:
        al_str = "alias of " if alias else ""
        old_name = type(old_cmd.module).__name__
        new_name = type(new_cmd.module).__name__
        super().__init__(
            f"Attempt to replace existing command '{old_cmd.name}' (from {old_name}) with {al_str}'{new_cmd.name}' (from {new_name})"
        )

        self.old_cmd = old_cmd
        self.new_cmd = new_cmd
        self.alias = alias
