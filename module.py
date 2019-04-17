class ModuleLoadError(Exception):
    pass

class ExistingModuleError(ModuleLoadError):
    def __init__(self, old_module, new_module):
        super().__init__(f"Replacing existing module '{old_module.name}' ({old_module.__name__})")
        
        self.old_module = old_module
        self.new_module = new_module

class UnknownEventError(ModuleLoadError):
    def __init__(self, event_name, listener):
        super().__init__(f"Registering listener for unknown event '{event_name}'")

        self.event_name = event_name
        self.listener = listener

class ExistingCommandError(ModuleLoadError):
    def __init__(self, old_cmd, new_cmd, alias=False):
        al_str = 'alias of ' if alias else ''
        super().__init__(f"Replacing existing command '{old_cmd.name}' (from {old_cmd.module.__class__.__name__}) with {al_str}'{new_cmd.name}' (from {new_cmd.module.__class__.__name__})")

        self.old_cmd = old_cmd
        self.new_cmd = new_cmd
        self.alias = alias

class Module():
    name = 'Unnamed'

    def __init__(self, bot):
        self.bot = bot

    def log_stat(self, key):
        if 'Stats' in self.bot.modules and 'stats' in self.bot.config and key in self.bot.config['stats']:
            self.bot.config['stats'][key] += 1
