import re
import asyncio

from .. import command, module, util


class SnippetsModule(module.Module):
    name = "Snippet"

    async def on_load(self):
        self.db = self.bot.get_db("snippets")

    def snip_repl(self, m):
        replacement = self.db.get_sync(m.group(1))
        if replacement is not None:
            self.bot.dispatch_event_nowait("stat_event", "replaced")
            return replacement

        return m.group(0)

    async def on_message(self, msg):
        if msg.out and msg.text:
            orig_text = msg.text
            text = msg.text

            text = await util.run_sync(lambda: re.sub(r"/([^ ]+?)/", self.snip_repl, orig_text))
            text = util.tg.truncate(text)

            if text != orig_text:
                await asyncio.sleep(1)
                await msg.edit(text=text, link_preview=False)

    @command.desc("Save a snippet (fetch: `/snippet/`)")
    @command.usage("[snippet name] [text?, or reply]")
    @command.alias("snippet", "snp")
    async def cmd_snip(self, ctx: command.Context):
        if ctx.msg.is_reply:
            reply_msg = await ctx.msg.get_reply_message()

            content = reply_msg.text
            if not content:
                if len(ctx.args) > 1:
                    content = " ".join(ctx.args[1:])
                else:
                    return "__Reply to a message with text or provide text after snippet name.__"
        else:
            if len(ctx.args) > 1:
                content = " ".join(ctx.args[1:])
            else:
                return "__Reply to a message with text or provide text after snippet name.__"

        name = ctx.args[0]
        if await self.db.has(name):
            return f"__Snippet '{name}' already exists!__"

        await self.db.put(name, content.strip())
        return f"Snippet saved as `{name}`."

    @command.desc("Show all snippets")
    @command.alias("sl", "snl", "spl", "snips", "snippets")
    async def cmd_sniplist(self, ctx: command.Context):
        out = "Snippet list:"

        async for key, _ in self.db:
            out += f"\n    \u2022 **{key}**"

        if out == "Snippet list:":
            return "__No snippets saved.__"

        return out

    @command.desc("Delete a snippet")
    @command.usage("[snippet name]")
    @command.alias("ds", "sd", "snd", "spd", "rms", "srm", "rs", "sr", "rmsnip", "delsnip")
    async def cmd_snipdel(self, ctx: command.Context):
        name = ctx.input

        if not await self.db.has(name):
            return "__That snippet doesn't exist.__"

        await self.db.delete(name)
        return f"Snippet `{name}` deleted."
