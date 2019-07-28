import command
import module
import util


class ManagerModule(module.Module):
    name = "Manager"

    @command.desc("Reload all modules")
    @command.alias("ra")
    async def cmd_reloadall(self, msg):
        before = util.time_us()

        await self.bot.dispatch_event("stop")
        await self.bot.save_config()

        await msg.result("Unloading all modules...")
        self.bot.unload_all_modules()

        await msg.result("Reloading module classes...")
        await self.bot.reload_module_pkg()

        await msg.result("Loading new modules...")
        try:
            self.bot.load_all_modules()
        except module.ExistingModuleError:
            pass

        await msg.result("Dispatching events...")
        await self.bot.dispatch_event("load")
        await self.bot.dispatch_event("start", util.time_us())

        await self.bot.save_config()

        after = util.time_us()
        delta = after - before

        return f"All modules reloaded in {util.format_duration_us(delta)}."
