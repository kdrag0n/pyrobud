from .. import command, module, util


class ManagerModule(module.Module):
    name = "Manager"

    @command.desc("Reload all modules")
    @command.alias("ra", "reload", "r")
    async def cmd_reloadall(self, msg):
        before = util.time.usec()

        await self.bot.dispatch_event("stop")

        await msg.result("Unloading all modules...")
        self.bot.unload_all_modules()

        await msg.result("Reloading module classes...")
        await self.bot.reload_module_pkg()

        await msg.result("Loading new modules...")
        self.bot.load_all_modules()

        await msg.result("Dispatching events...")
        await self.bot.dispatch_event("load")
        await self.bot.dispatch_event("start", util.time.usec())

        after = util.time.usec()
        delta = after - before

        return f"All modules reloaded in {util.time.format_duration_us(delta)}."
