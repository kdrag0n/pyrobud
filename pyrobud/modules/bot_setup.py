import asyncio
from datetime import datetime
from typing import ClassVar, Sequence, Tuple, Union

import telethon as tg
import tomlkit
from tomlkit.toml_document import TOMLDocument

from .. import command, module, util


class BotSetupModule(module.Module):
    name: ClassVar[str] = "Bot Setup"

    @staticmethod
    def parse_config(
        chat_id: int, input_cfg: str
    ) -> Union[str, Tuple[str, str, str, TOMLDocument]]:
        target = "MissRose_bot"
        rules = [
            "Rules:",
            "*Use common sense.* We're all people.",
            "*Don't spam.* Consider other people's notifications.",
            "*English only.* This is a universal chat — make sure everyone can understand your messages.",
            "*Search before asking questions.* It saves everyone's time, including yours.",
            "*Limit off-topic discussion.* While minor off-topic content is allowed, keep the chat's original topic in mind.",
        ]

        default_rules_list = ", ".join(f'"{rule}"' for rule in rules)
        bracket_format = "{}"
        cfg_err = f"""**Invalid config.** The following options are supported:
```
# Bot to setup
target = "{target}"

# Default rules
rules = [{default_rules_list}]
extra_rules = []

# Add ":same" at the end of links to put buttons on the same line
# "Rules" is always present as the first button
[buttons]
"XDA Thread" = "https://forum.xda-developers.com/"
GitHub = "https://github.com/"```

{bracket_format}"""

        input_cfg = util.tg.filter_code_block(input_cfg)
        if input_cfg.startswith("?") or input_cfg.startswith("help"):
            return cfg_err.format("")

        button_map = {"Rules": f"https://t.me/{target}?start=rules_{chat_id}"}

        cfg: TOMLDocument
        if input_cfg:
            try:
                cfg = tomlkit.loads(input_cfg)
            except Exception as e:
                return cfg_err.format(str(e))

            if "target" in cfg:
                target = cfg["target"]

            if "rules" in cfg:
                rules = cfg["rules"]

            if "extra_rules" in cfg:
                rules.extend(cfg["extra_rules"])

            if "buttons" in cfg:
                button_map.update(cfg["buttons"])
        else:
            cfg = tomlkit.document()

        rule_str = util.text.join_list(rules)
        button_links = [
            f"[{name}](buttonurl://{dest})" for name, dest in button_map.items()
        ]
        button_str = "\n".join(button_links)

        return target, rule_str, button_str, cfg

    @staticmethod
    def get_commands(chat_id: int, rule_str: str, button_str: str) -> Sequence[str]:
        first = "{first}"

        return [
            f"/connect {chat_id}",
            "/welcome on",
            "/goodbye off",
            "/setwarnlimit 3",
            "/setwarnmode ban",
            f"""/setwelcome *Welcome*, {first}!
Please read the rules _before_ participating.
{button_str}""",
            "/cleanwelcome on",
            f"/setrules {rule_str}",
            "/setflood 13",
            "/setfloodmode tmute 3h",
            "/reports on",
            "/welcomemute on",
            "/welcomemutetime 2h",
            "/blacklistmode tban 2d",
            "/disconnect",
        ]

    async def promote_bot(self, chat: tg.types.InputPeerChannel, username: str) -> None:
        rights = tg.tl.types.ChatAdminRights(
            delete_messages=True, ban_users=True, invite_users=True, pin_messages=True
        )

        request = tg.tl.functions.channels.EditAdminRequest(
            chat, username, rights, "bot"
        )
        await self.bot.client(request)

    @staticmethod
    def truncate_cmd_list(commands: Sequence[str]) -> Sequence[str]:
        new_list = []

        for cmd in commands:
            lines = cmd.split("\n")
            primary_line = lines[0]

            if len(lines) > 1:
                primary_line += "..."

            new_list.append(primary_line)

        return new_list

    @command.desc("Set up @MissRose_bot and derivatives")
    @command.usage("[config?]", optional=True)
    async def cmd_bsetup(self, ctx: command.Context) -> str:
        input_cfg = ctx.input

        if not ctx.msg.is_group:
            return "__This feature can only be used in groups.__"

        parse_results = self.parse_config(ctx.msg.chat_id, input_cfg)
        if isinstance(parse_results, str):
            # A string return value means an error occurred, so propagate it
            return parse_results

        target, rule_str, button_str, parsed_cfg = parse_results
        commands = self.get_commands(ctx.msg.chat_id, rule_str, button_str)
        formatted_cfg = tomlkit.dumps(parsed_cfg)
        if formatted_cfg:
            settings_used = f"\n```{formatted_cfg}```"
        else:
            settings_used = " defaults\n"

        before = datetime.now()

        status_header = f"Setting up @{target} via PM connection..."
        await ctx.respond(status_header)

        input_chat = await ctx.msg.get_input_chat()
        if isinstance(input_chat, tg.types.InputPeerChannel):
            try:
                await self.promote_bot(input_chat, target)
            except Exception as e:
                status_header += (
                    f"\n**WARNING:** Unable to promote @{target}: `{str(e)}`"
                )
                await ctx.respond(status_header)

        async with self.bot.client.conversation(target) as conv:

            async def reply_and_ack():
                # Wait for a reply
                await conv.get_reply()
                # Ack the reply to suppress its notification
                await conv.mark_read()

            for idx, cmd in enumerate(commands):
                await conv.send_message(cmd, parse_mode=None)

                cur_cmd_list = self.truncate_cmd_list(commands[: idx + 1])
                cmd_log = "\n".join(cur_cmd_list)
                status = f"""{status_header}

Commands issued:
```{cmd_log}```"""

                await ctx.respond(status)

                # Wait for both the rate-limit and the bot's response
                try:
                    # pylint: disable=unused-variable
                    done, pending = await asyncio.wait(
                        (reply_and_ack(), asyncio.sleep(0.25))
                    )

                    # Raise all exceptions
                    for future in done:
                        exp = future.exception()
                        if exp is not None:
                            raise exp
                except asyncio.TimeoutError:
                    after = datetime.now()
                    delta_seconds = int((after - before).total_seconds())

                    return f"""Setup of @{target} failed after {delta_seconds} seconds.

Settings used:{settings_used}
Commands issued:
```{cmd_log}```

The bot failed to respond within 1 minute of issuing the last command. Perhaps the command is incorrect or the bot is down?"""

        after = datetime.now()
        delta_seconds = int((after - before).total_seconds())

        return f"""Setup of @{target} finished in {delta_seconds} seconds.

Settings used:{settings_used}
Commands issued:
```{cmd_log}```"""
