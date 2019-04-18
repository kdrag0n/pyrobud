import command
import module
import util

class ManagerModule(module.Module):
    name = 'Manager'

    @command.desc('Reload all modules')
    @command.alias('ra')
    def cmd_reloadall(self, msg):
        before = util.time_us()

        self.bot.save_config()

        self.bot.mresult(msg, 'Unloading all modules...')
        self.bot.unload_all_modules()

        self.bot.mresult(msg, 'Reloading module classes...')
        self.bot.reload_module_pkg()

        self.bot.mresult(msg, 'Loading new modules...')
        try:
            self.bot.load_all_modules()
        except module.ExistingModuleError:
            pass

        self.bot.mresult(msg, 'Dispatching load and start events...')
        self.bot.dispatch_event('load')
        self.bot.dispatch_event('start', util.time_us())

        self.bot.save_config()

        after = util.time_us()
        delta = after - before

        return f'All modules reloaded in {util.format_duration_us(delta)}.'
