import inspect
import json
import logging
import re
import traceback

from meval import meval

from .. import command, module, util


class DebugModule(module.Module):
    name = "Debug"

    @command.desc("Evaluate code")
    @command.usage("[code snippet]")
    @command.alias("ev", "exec")
    async def cmd_eval(self, ctx: command.Context):
        code = util.tg.filter_code_block(ctx.input)

        async def _eval(code):
            # Message sending helper for convenience
            async def send(*args, **kwargs):
                return await ctx.msg.respond(*args, **kwargs)

            try:
                return ("", await meval(code, globals(), send=send, self=self, ctx=ctx))
            except Exception as e:
                # Find first traceback frame involving the snippet
                first_snip_idx = -1
                tb = traceback.extract_tb(e.__traceback__)
                for i in range(len(tb)):
                    frame = tb[i]
                    if frame.filename == "<string>":
                        first_snip_idx = i
                        break

                # Re-raise exception if it wasn't caused by the snippet
                if first_snip_idx == -1:
                    raise e

                # Return formatted stripped traceback
                stripped_tb = tb[first_snip_idx:]
                formatted_tb = util.format_exception(e, tb=stripped_tb)
                return ("⚠️ Error executing snippet\n\n", formatted_tb)

        before = util.time.usec()
        prefix, result = await _eval(code)
        after = util.time.usec()

        el_us = after - before
        el_str = util.time.format_duration_us(el_us)

        return f"""{prefix}**In**:
```{code}```

**Out**:
```{str(result)}```

Time: {el_str}"""

    @command.desc("Get the code of a command")
    @command.usage("[command name]")
    async def cmd_src(self, ctx: command.Context):
        cmd_name = ctx.input

        if cmd_name not in self.bot.commands:
            return f"__Command__ `{cmd_name}` __doesn't exist.__"

        src = await util.run_sync(lambda: inspect.getsource(self.bot.commands[cmd_name].func))
        filtered_src = re.sub(r"^    ", "", src, flags=re.MULTILINE)
        return f"```{filtered_src}```"

    @command.desc("Get plain text of a message")
    @command.alias("text", "raw")
    async def cmd_gtx(self, ctx: command.Context):
        if not ctx.msg.is_reply:
            return "__Reply to a message to get the text of.__"

        reply_msg = await ctx.msg.get_reply_message()
        await ctx.respond(reply_msg.text, parse_mode=None)

    @command.desc("Send text")
    @command.usage("[text to send]")
    async def cmd_echo(self, ctx: command.Context):
        text = ctx.input
        return text

    @command.desc("Dump all the data of a message")
    @command.alias("md", "msginfo", "minfo")
    async def cmd_mdump(self, ctx: command.Context):
        if not ctx.msg.is_reply:
            return "__Reply to a message to get its data.__"

        reply_msg = await ctx.msg.get_reply_message()
        data = reply_msg.stringify()

        return f"```{data}```"

    @command.desc("Get all available information about the given entity")
    @command.usage('[entity ID/username/... or "chat" for the current chat?, or reply]', optional=True)
    @command.alias("einfo")
    async def cmd_entity(self, ctx: command.Context):
        entity_str = ctx.input

        if entity_str == "chat":
            entity = await ctx.msg.get_chat()
        elif entity_str:
            if entity_str.isdigit():
                try:
                    entity_str = int(entity_str)
                except ValueError:
                    return f"Unable to parse `{entity_str}` as ID!"

            try:
                entity = await self.bot.client.get_entity(entity_str)
            except ValueError as e:
                return f"Error getting entity `{entity_str}`: {e}"
        elif ctx.msg.is_reply:
            entity = await ctx.msg.get_reply_message()
        else:
            return "__No entity given via argument or reply.__"

        return f"```{entity.stringify()}```"

    @command.desc("Get all contextually relevant IDs")
    @command.alias("user", "info")
    async def cmd_id(self, ctx: command.Context):
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
                    lines.append(f"Forwarded message author ID: `{reply_msg.forward.from_id}`")

                if hasattr(reply_msg.forward.saved_from_peer, "channel_id"):
                    f_chat_id = reply_msg.forward.saved_from_peer.channel_id
                    lines.append(f"Forwarded message chat ID: `{f_chat_id}`")

                if reply_msg.forward.saved_from_msg_id:
                    f_msg_id = reply_msg.forward.saved_from_msg_id
                    lines.append(f"Forwarded message original ID: `{f_msg_id}`")

                if reply_msg.forward.saved_from_peer and reply_msg.forward.saved_from_msg_id:
                    lines.append(f"[Link to forwarded message](https://t.me/c/{f_chat_id}/{f_msg_id})")

        return "\n".join(lines)
