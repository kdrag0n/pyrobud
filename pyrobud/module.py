import logging


class ModuleLoadError(Exception):
    pass


class ExistingModuleError(ModuleLoadError):
    def __init__(self, old_module, new_module):
        super().__init__(f"Module '{old_module.name}' ({old_module.__name__}) already exists")

        self.old_module = old_module
        self.new_module = new_module


class ExistingCommandError(ModuleLoadError):
    def __init__(self, old_cmd, new_cmd, alias=False):
        al_str = "alias of " if alias else ""
        super().__init__(
            f"Attempted to replace existing command '{old_cmd.name}' (from {old_cmd.module.__class__.__name__}) with {al_str}'{new_cmd.name}' (from {new_cmd.module.__class__.__name__})"
        )

        self.old_cmd = old_cmd
        self.new_cmd = new_cmd
        self.alias = alias


class Module:
    name = "Unnamed"

    def __init__(self, bot):
        self.bot = bot
        self.log = logging.getLogger(self.__class__.name.lower())
