import inspect
import io
import os
import re
import sys
import traceback
from typing import Any, ClassVar, Optional, Tuple

import telethon as tg
from meval import meval

from .. import command, module, util


class DebugModule(module.Module):
    name: ClassVar[str] = "Debug"

    @command.desc("Evaluate code")
    @command.usage("[code snippet]")
    @command.alias("ev", "exec")
    async def cmd_eval(self, ctx: command.Context) -> str:
        code = util.tg.filter_code_block(ctx.input)
        out_buf = io.StringIO()

        async def _eval() -> Tuple[str, str]:
            # Message sending helper for convenience
            async def send(*args: Any, **kwargs: Any) -> tg.custom.Message:
                return await ctx.msg.respond(*args, **kwargs)

            # Print wrapper to capture output
            # We don't override sys.stdout to avoid interfering with other output
            def _print(*args: Any, **kwargs: Any) -> None:
                if "file" not in kwargs:
                    kwargs["file"] = out_buf

                return print(*args, **kwargs)

            eval_vars = {
                # Contextual info
                "self": self,
                "ctx": ctx,
                "bot": self.bot,
                "loop": self.bot.loop,
                "client": self.bot.client,
                "commands": self.bot.commands,
                "listeners": self.bot.listeners,
                "modules": self.bot.modules,
                "stdout": out_buf,
                # Helper functions
                "send": send,
                "print": _print,
                # Built-in modules
                "inspect": inspect,
                "os": os,
                "re": re,
                "sys": sys,
                "traceback": traceback,
                # Third-party modules
                "tg": tg,
                # Custom modules
                "command": command,
                "module": module,
                "util": util,
            }

            try:
                return "", await meval(code, globals(), **eval_vars)
            except Exception as e:
                # Find first traceback frame involving the snippet
                first_snip_idx = -1
                tb = traceback.extract_tb(e.__traceback__)
                for i, frame in enumerate(tb):
                    if frame.filename == "<string>" or frame.filename.endswith(
                        "ast.py"
                    ):
                        first_snip_idx = i
                        break

                # Re-raise exception if it wasn't caused by the snippet
                if first_snip_idx == -1:
                    raise e

                # Return formatted stripped traceback
                stripped_tb = tb[first_snip_idx:]
                formatted_tb = util.format_exception(e, tb=stripped_tb)
                return "⚠️ Error executing snippet\n\n", formatted_tb

        before = util.time.usec()
        prefix, result = await _eval()
        after = util.time.usec()

        # Always write result if no output has been collected thus far
        if not out_buf.getvalue() or result is not None:
            print(result, file=out_buf)

        el_us = after - before
        el_str = util.time.format_duration_us(el_us)

        out = out_buf.getvalue()
        # Strip only ONE final newline to compensate for our message formatting
        if out.endswith("\n"):
            out = out[:-1]

        return f"""{prefix}**In:**
```{code}```

**Out:**
```{out}```

Time: {el_str}"""

    @command.desc("Get the code of a command")
    @command.usage("[command name]")
    async def cmd_src(self, ctx: command.Context) -> str:
        cmd_name = ctx.input

        if cmd_name not in self.bot.commands:
            return f"__Command__ `{cmd_name}` __doesn't exist.__"

        src = await util.run_sync(inspect.getsource, self.bot.commands[cmd_name].func)
        # Strip first level of indentation
        filtered_src = re.sub(r"^ {4}", "", src, flags=re.MULTILINE)
        return f"```{filtered_src}```"

    @command.desc("Get plain text of a message")
    @command.alias("text", "raw")
    async def cmd_gtx(self, ctx: command.Context) -> Optional[str]:
        if not ctx.msg.is_reply:
            return "__Reply to a message to get the text of.__"

        reply_msg = await ctx.msg.get_reply_message()
        await ctx.respond(reply_msg.text, parse_mode=None)
        return None

    @command.desc("Send text")
    @command.usage("[text to send]")
    async def cmd_echo(self, ctx: command.Context) -> str:
        return ctx.input

    @command.desc("Dump all the data of a message")
    @command.alias("md", "msginfo", "minfo")
    async def cmd_mdump(self, ctx: command.Context) -> str:
        if not ctx.msg.is_reply:
            return "__Reply to a message to get its data.__"

        reply_msg = await ctx.msg.get_reply_message()
        data = util.tg.pretty_print_entity(reply_msg)

        return f"```{data}```"

    @command.desc("Get all available information about the given entity")
    @command.usage(
        '[entity ID/username/... or "chat" for the current chat?, or reply]',
        optional=True,
    )
    @command.alias("einfo")
    async def cmd_entity(self, ctx: command.Context) -> str:
        entity_ref: tg.hints.EntitiesLike = ctx.input

        if ctx.input == "chat":
            entity = await ctx.msg.get_chat()
        elif ctx.input:
            if ctx.input.isdigit():
                try:
                    entity_ref = int(ctx.input)
                except ValueError:
                    return f"Unable to parse `{entity_ref}` as ID!"
            else:
                entity_ref = ctx.input

            try:
                entity = await self.bot.client.get_entity(entity_ref)
            except ValueError as e:
                return f"Error getting entity `{entity_ref}`: {e}"
        elif ctx.msg.is_reply:
            entity = await ctx.msg.get_reply_message()
        else:
            return "__No entity given via argument or reply.__"

        pretty_printed = util.tg.pretty_print_entity(entity)
        return f"```{pretty_printed}```"

    @command.desc("Get all contextually relevant IDs")
    @command.alias("user")
    async def cmd_id(self, ctx: command.Context) -> str:
        lines = []

        if ctx.msg.chat_id:
            lines.append(f"Chat ID: `{ctx.msg.chat_id}`")

        lines.append(f"My user ID: `{self.bot.uid}`")

        if ctx.msg.is_reply:
            reply_msg = await ctx.msg.get_reply_message()
            sender = await reply_msg.get_sender()
            lines.append(f"Message ID: `{reply_msg.id}`")

            if sender:
                lines.append(f"Message author ID: `{sender.id}`")

            if reply_msg.forward:
                if reply_msg.forward.from_id:
                    lines.append(
                        f"Forwarded message author ID: `{reply_msg.forward.from_id}`"
                    )

                f_chat_id = None
                if hasattr(reply_msg.forward.saved_from_peer, "channel_id"):
                    f_chat_id = reply_msg.forward.saved_from_peer.channel_id
                    lines.append(f"Forwarded message chat ID: `{f_chat_id}`")

                f_msg_id = None
                if reply_msg.forward.saved_from_msg_id:
                    f_msg_id = reply_msg.forward.saved_from_msg_id
                    lines.append(f"Forwarded message original ID: `{f_msg_id}`")

                if f_chat_id is not None and f_msg_id is not None:
                    lines.append(
                        f"[Link to forwarded message](https://t.me/c/{f_chat_id}/{f_msg_id})"
                    )

        return "\n".join(lines)
