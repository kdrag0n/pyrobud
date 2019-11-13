import logging
# import os,sys,inspect
# _currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
# _parentdir = os.path.dirname(_currentdir)
# sys.path.insert(0,_parentdir)
import typing
if typing.TYPE_CHECKING:
    from bot import Bot


class ModuleLoadError(Exception):
    pass


class ExistingModuleError(ModuleLoadError):
    def __init__(self, old_module, new_module):
        super().__init__(f"Replacing existing module '{old_module.name}' ({old_module.__name__})")

        self.old_module = old_module
        self.new_module = new_module


class ExistingCommandError(ModuleLoadError):
    def __init__(self, old_cmd, new_cmd, alias=False):
        al_str = "alias of " if alias else ""
        super().__init__(
            f"Replacing existing command '{old_cmd.name}' (from {old_cmd.module.__class__.__name__}) with {al_str}'{new_cmd.name}' (from {new_cmd.module.__class__.__name__})"
        )

        self.old_cmd = old_cmd
        self.new_cmd = new_cmd
        self.alias = alias


class Module:
    name = "Unnamed"
    bot: 'Bot'

    def __init__(self, bot: 'Bot'):
        self.bot = bot
        self.log = logging.getLogger(self.__class__.name.lower())
