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
            orig_txt = msg.text
            txt = msg.text

            txt = await util.run_sync(lambda: re.sub(r"/([^ ]+?)/", self.snip_repl, orig_txt))

            if txt != orig_txt:
                await asyncio.sleep(0.1)
                await msg.result(txt)

    @command.desc("Save a snippet (fetch: `/snippet/`)")
    @command.alias("snippet", "snp")
    async def cmd_snip(self, msg, *args):
        if not args:
            return "__Specify a name for the snippet, then reply to a message or provide text.__"

        if msg.is_reply:
            reply_msg = await msg.get_reply_message()

            content = reply_msg.text
            if not content:
                if len(args) > 1:
                    content = " ".join(args[1:])
                else:
                    return "__Reply to a message with text or provide text after snippet name.__"
        else:
            if len(args) > 1:
                content = " ".join(args[1:])
            else:
                return "__Reply to a message with text or provide text after snippet name.__"

        name = args[0]
        if await self.db.has(name):
            return f"__Snippet '{name}' already exists!__"

        await self.db.put(name, content.strip())
        return f"Snippet saved as `{name}`."

    @command.desc("Show all snippets")
    @command.alias("sl", "snl", "spl", "snips", "snippets")
    async def cmd_sniplist(self, msg):
        out = "Snippet list:"

        async for key, _ in self.db:
            out += f"\n    \u2022 **{key}**"

        if out == "Snippet list:":
            return "__No snippets saved.__"

        return out

    @command.desc("Delete a snippet")
    @command.alias("ds", "sd", "snd", "spd", "rms", "srm", "rs", "sr", "rmsnip", "delsnip")
    async def cmd_snipdel(self, msg, name):
        if not name:
            return "__Provide the name of a snippet to delete.__"

        if not await self.db.has(name):
            return "__That snippet doesn't exist.__"

        await self.db.delete(name)
        return f"Snippet `{name}` deleted."
