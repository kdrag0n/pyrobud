import asyncio
import collections
from datetime import datetime
from typing import ClassVar, Sequence, Tuple, Union

import telethon as tg
import tomlkit
from tomlkit.toml_document import TOMLDocument

from .. import command, module, util

Exchange = collections.namedtuple("Exchange", ["command", "response"])


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
    def get_exchanges(
        chat_id: int, rule_str: str, button_str: str
    ) -> Sequence[Exchange]:
        return [
            Exchange(f"/connect {chat_id}", response="connected"),
            Exchange("/welcome on", response="welcom"),
            Exchange("/goodbye off", response="leave"),
            Exchange("/setwarnlimit 3", response="updated"),
            Exchange("/setwarnmode ban", response="updated"),
            Exchange(
                """/setwelcome *Welcome*, {first}!
Please read the rules _before_ participating.
"""
                + button_str,
                response="saved",
            ),
            Exchange("/cleanwelcome on", response="delet"),
            Exchange(f"/setrules {rule_str}", response="success"),
            Exchange("/setflood 13", response="updated"),
            Exchange("/setfloodmode tmute 3h", response="updated"),
            Exchange("/reports on", response="able"),
            Exchange("/captchamode text", response="set to text"),
            Exchange("/captchatime 13w", response="13 weeks"),
            Exchange("/blacklistmode tban 2d", response="updated"),
            Exchange("/disconnect", response="disconnect"),
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
    def truncate_xchg_list(commands: Sequence[Exchange]) -> Sequence[str]:
        new_list = []

        for xchg in commands:
            lines = xchg.command.split("\n")
            first_line = lines[0]

            if len(lines) > 1:
                first_line += "..."

            new_list.append(first_line)

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
        exchanges = self.get_exchanges(ctx.msg.chat_id, rule_str, button_str)
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

            async def reply_and_ack() -> tg.custom.Message:
                # Wait for a reply
                reply = await conv.get_reply()
                # Ack the reply to suppress its notification
                await conv.mark_read()

                return reply

            for idx, xchg in enumerate(exchanges):
                await conv.send_message(xchg.command, parse_mode=None)

                cur_cmd_list = self.truncate_xchg_list(exchanges[: idx + 1])
                cmd_log = "\n".join(cur_cmd_list)
                status_body = f"""Settings:{settings_used}
Commands issued:
```{cmd_log}```"""
                status = f"""{status_header}

{status_body}"""

                # Wait for the rate-limit, the bot's response, and the send
                try:
                    reply_task = self.bot.loop.create_task(reply_and_ack())
                    send_task = self.bot.loop.create_task(ctx.respond(status))

                    # pylint: disable=unused-variable
                    done, pending = await asyncio.wait(
                        (reply_task, send_task, asyncio.sleep(0.25))
                    )

                    # Raise all exceptions
                    for future in done:
                        exp = future.exception()
                        if exp is not None:
                            raise exp
                except asyncio.TimeoutError:
                    return f"""@{target} failed to respond during setup. Try again later.

{status_body}"""

                # Validate response
                msg = reply_task.result()
                if xchg.response not in msg.raw_text.lower():
                    return f"""Unexpected response received from @{target} during setup.

{status_body}

Last response: "{msg.text}"
"""

        after = datetime.now()
        delta_seconds = int((after - before).total_seconds())

        return f"""Setup of @{target} finished in {delta_seconds} seconds.

{status_body}"""
