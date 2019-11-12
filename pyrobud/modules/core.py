from pyrobud import command, module, util


class CoreModule(module.Module):
    name = "Core"

    @command.desc("List the commands")
    async def cmd_help(self, msg):
        lines = {}

        for name, cmd in self.bot.commands.items():
            # Don't count aliases as separate commands
            if name != cmd.name:
                continue

            desc = cmd.desc if cmd.desc else "__No description provided__"
            aliases = ""
            if cmd.aliases:
                aliases = f' (aliases: {", ".join(cmd.aliases)})'

            mod_name = cmd.module.__class__.name
            if mod_name not in lines:
                lines[mod_name] = []

            lines[mod_name].append(f"**{cmd.name}**: {desc}{aliases}")

        sections = []
        for mod, ln in lines.items():
            sections.append(f"**{mod}**:\n    \u2022 " + "\n    \u2022 ".join(ln) + "\n")

        return "\n".join(sections)

    @command.desc("Get how long the bot has been up for")
    async def cmd_uptime(self, msg):
        delta_us = util.time.usec() - self.bot.start_time_us
        return f"Uptime: {util.time.format_duration_us(delta_us)}"

    @command.desc("Get or change the bot prefix")
    async def cmd_prefix(self, msg, new_prefix):
        if not new_prefix:
            return f"The prefix is `{self.bot.prefix}`."

        self.bot.prefix = new_prefix
        await self.bot.db.put("prefix", new_prefix)

        return f"Prefix set to `{self.bot.prefix}`."
