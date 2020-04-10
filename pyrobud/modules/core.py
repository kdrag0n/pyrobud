import platform
from collections import defaultdict
from typing import ClassVar, MutableMapping

from .. import __version__, command, module, util

OFFICIAL_SUPPORT_LINK = "https://t.me/pyrobud"


class CoreModule(module.Module):
    name: ClassVar[str] = "Core"

    @command.desc("List the commands")
    @command.usage("[filter: command or module name?]", optional=True)
    async def cmd_help(self, ctx: command.Context):
        filt = ctx.input
        modules: MutableMapping[str, MutableMapping[str, str]] = defaultdict(dict)

        # Handle command filters
        if filt and filt not in self.bot.modules:
            if filt in self.bot.commands:
                cmd = self.bot.commands[filt]

                # Generate aliases section
                aliases = f"`{'`, `'.join(cmd.aliases)}`" if cmd.aliases else "none"

                # Generate parameters section
                if cmd.usage is None:
                    args_desc = "none"
                else:
                    args_desc = cmd.usage

                    if cmd.usage_optional:
                        args_desc += " (optional)"
                    if cmd.usage_reply:
                        args_desc += " (also accepts replies)"

                # Show info card
                return f"""`{cmd.name}`: **{cmd.desc if cmd.desc else '__No description provided.__'}**

Module: {cmd.module.name}
Aliases: {aliases}
Expected parameters: {args_desc}"""
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

            mod_name = type(cmd.module).name
            modules[mod_name][cmd.name] = desc + aliases

        response = None
        for mod_name, commands in sorted(modules.items()):
            section = util.text.join_map(commands, heading=mod_name)
            add_len = len(section) + 2
            if response and (len(response) + add_len > util.tg.MESSAGE_CHAR_LIMIT):
                await ctx.respond_multi(response)
                response = None

            if response:
                response += "\n\n" + section
            else:
                response = section

        if response:
            await ctx.respond_multi(response)

    @command.desc("Get how long this bot has been up for")
    async def cmd_uptime(self, ctx: command.Context) -> str:
        delta_us = util.time.usec() - self.bot.start_time_us
        return f"Uptime: {util.time.format_duration_us(delta_us)}"

    @command.desc("Get or change this bot prefix")
    @command.usage("[new prefix?]", optional=True)
    async def cmd_prefix(self, ctx: command.Context) -> str:
        new_prefix = ctx.input

        if not new_prefix:
            return f"The prefix is `{self.bot.prefix}`."

        self.bot.prefix = new_prefix
        await self.bot.db.put("prefix", new_prefix)

        return f"Prefix set to `{self.bot.prefix}`."

    @command.desc("Get the link to the official bot support group")
    async def cmd_support(self, ctx: command.Context) -> str:
        return f"[Join the official bot support group for help.]({OFFICIAL_SUPPORT_LINK})"

    @command.desc("Get information about this bot instance")
    @command.alias("botinfo", "binfo", "bi", "i")
    async def cmd_info(self, ctx: command.Context) -> None:
        # Get tagged version and optionally the Git commit
        commit = await util.run_sync(util.version.get_commit)
        dirty = ", dirty" if await util.run_sync(util.git.is_dirty) else ""
        unofficial = ", unofficial" if not await util.run_sync(util.git.is_official) else ""
        version = f"{__version__} (<code>{commit}</code>{dirty}{unofficial})" if commit else __version__

        # Clean system version
        sys_ver = platform.release()
        try:
            sys_ver = sys_ver[: sys_ver.index("-")]
        except ValueError:
            pass

        # Get current uptime
        now = util.time.usec()
        uptime = util.time.format_duration_us(now - self.bot.start_time_us)

        # Get total uptime from stats module (if loaded)
        stats_module = self.bot.modules.get("Stats", None)
        get_start_time = getattr(stats_module, "get_start_time", None)
        total_uptime = None
        if stats_module is not None and callable(get_start_time):
            stats_start_time = await get_start_time()
            total_uptime = util.time.format_duration_us(now - stats_start_time) + "\n"
        else:
            uptime += "\n"

        # Get total number of chats, including PMs
        num_chats = (await self.bot.client.get_dialogs(limit=0)).total

        response = util.text.join_map(
            {
                "Version": version,
                "Python": f"{platform.python_implementation()} {platform.python_version()}",
                "System": f"{platform.system()} {sys_ver}",
                "Uptime": uptime,
                **({"Total uptime": total_uptime} if total_uptime else {}),
                "Commands loaded": len(self.bot.commands),
                "Modules loaded": len(self.bot.modules),
                "Listeners loaded": sum(len(evt) for evt in self.bot.listeners.values()),
                "Events activated": f"{self.bot.events_activated}\n",
                "Chats": num_chats,
            },
            heading='<a href="https://github.com/kdrag0n/pyrobud">Pyrobud</a> info',
            parse_mode="html",
        )

        # HTML allows us to send a bolded link (nested entities)
        await ctx.respond(response, parse_mode="html")
