import asyncio
import time
from datetime import datetime

import telethon as tg
import toml

from .. import command, module, util


class BotSetupModule(module.Module):
    name = "Bot Setup"

    def parse_config(self, chat_id, input_cfg):
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

        cfg = {}
        if input_cfg:
            try:
                cfg = toml.loads(input_cfg)
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

        rule_str = "\n    • ".join(rules)
        button_links = [f"[{name}](buttonurl://{dest})" for name, dest in button_map.items()]
        button_str = "\n".join(button_links)

        return (target, rule_str, button_str, cfg)

    def get_commands(self, chat_id, rule_str, button_str):
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
            '/addblacklist "http://t.cn/*" "This isn\'t the place for cryptocurrency advertising."',
            "/disconnect",
        ]

    async def promote_bot(self, chat, username):
        rights = tg.tl.types.ChatAdminRights(delete_messages=True, ban_users=True, invite_users=True, pin_messages=True)

        request = tg.tl.functions.channels.EditAdminRequest(chat, username, rights, "bot")
        await self.bot.client(request)

    def truncate_cmd_list(self, commands):
        new_list = []

        for cmd in commands:
            lines = cmd.split("\n")
            primary_line = lines[0]

            if len(lines) > 1:
                primary_line += "..."

            new_list.append(primary_line)

        return new_list

    @command.desc("Set up @MissRose_bot and derivatives")
    async def cmd_bsetup(self, msg, input_cfg):
        if not msg.is_group:
            return "__This feature can only be used in groups.__"

        parse_results = self.parse_config(msg.chat_id, input_cfg)
        if isinstance(parse_results, str):
            # A string return value means an error occurred, so propagate it
            return parse_results

        target, rule_str, button_str, parsed_cfg = parse_results
        commands = self.get_commands(msg.chat_id, rule_str, button_str)
        formatted_cfg = toml.dumps(parsed_cfg)

        before = datetime.now()

        status_header = f"Setting up @{target} via PM connection..."
        await msg.result(status_header)

        try:
            await self.promote_bot(msg.chat, target)
        except Exception as e:
            status_header += f"\n**WARNING**: Unable to promote @{target}: `{str(e)}`"
            await msg.result(status_header)

        async with self.bot.client.conversation(target) as conv:

            async def reply_and_ack():
                # Wait for a reply
                await conv.get_reply()
                # Ack the reply to suppress its notiication
                await conv.mark_read()

            for idx, cmd in enumerate(commands):
                await conv.send_message(cmd, parse_mode=None)

                cur_cmd_list = self.truncate_cmd_list(commands[: idx + 1])
                cmd_log = "\n".join(cur_cmd_list)
                status = f"""{status_header}

Commands issued:
```{cmd_log}```"""

                await msg.result(status)

                # Wait for both the rate-limit and the bot's response
                try:
                    await asyncio.wait([reply_and_ack(), asyncio.sleep(0.25)])
                except asyncio.TimeoutError:
                    after = datetime.now()
                    delta_seconds = int((after - before).total_seconds())

                    return f"""Setup of @{target} failed after {delta_seconds} seconds.

Settings used:
```{formatted_cfg}```
Commands issued:
```{cmd_log}```

The bot failed to respond within 1 minute of issuing the last command. Perhaps the command is incorrect or the bot is down?"""

        after = datetime.now()
        delta_seconds = int((after - before).total_seconds())

        return f"""Setup of @{target} finished in {delta_seconds} seconds.

Settings used:
```{formatted_cfg}```
Commands issued:
```{cmd_log}```"""
