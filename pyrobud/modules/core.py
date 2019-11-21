import inspect

from .. import command, module, util

OFFICIAL_SUPPORT_LINK = "https://t.me/pyrobud"


class CoreModule(module.Module):
    name = "Core"

    @command.desc("List the commands")
    async def cmd_help(self, msg, filt):
        lines = {}

        # Handle command filters
        if filt and filt not in self.bot.modules:
            if filt in self.bot.commands:
                cmd = self.bot.commands[filt]

                # Generate aliases section
                aliases = f"`{'`, `'.join(cmd.aliases)}`" if cmd.aliases else "none"

                # Generate arguments section
                cmd_func = cmd.func
                cmd_spec = inspect.getfullargspec(cmd_func)
                cmd_args = cmd_spec.args

                if len(cmd_args) == 3:
                    args_desc = "Yes, one string"
                elif cmd_spec.varargs and not cmd_spec.kwonlyargs:
                    args_desc = "Yes, whitespace-separated segments"
                else:
                    args_desc = "No"

                # Show info card
                return f"""`{cmd.name}`: **{cmd.desc if cmd.desc else '__No description provided.__'}**

Module: {cmd.module.name}
Aliases: {aliases}
Takes arguments: {args_desc}"""
            else:
                return "__That filter didn't match any commands or modules.__"

        # Show full help
        for name, cmd in self.bot.commands.items():
            # Check if a filter is being used
            if filt:
                # Ignore commands that aren't part of the filtered module
                if cmd.module.name != filt:
                    continue
            else:
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
        for mod, ln in sorted(lines.items()):
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

    @command.desc("Get the link to the official bot support group")
    async def cmd_support(self, msg):
        return f"[Join the official bot support group for help.]({OFFICIAL_SUPPORT_LINK})"
