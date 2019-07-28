import re

import command
import module


class SnippetModule(module.Module):
    name = "Snippet"

    async def on_load(self):
        # Populate config if necessary
        if "snippets" not in self.bot.config:
            self.bot.config["snippets"] = {}

    def snip_repl(self, m):
        if m.group(1) in self.bot.config["snippets"]:
            self.bot.dispatch_event_nowait("stat_event", "replaced")
            return self.bot.config["snippets"][m.group(1)]

        return m.group(0)

    async def on_message(self, msg):
        if msg.out and msg.text:
            orig_txt = msg.text
            txt = msg.text

            txt = re.sub(r"/([^ ]+?)/", self.snip_repl, orig_txt)

            if txt != orig_txt:
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
        if name in self.bot.config["snippets"]:
            return f"__Snippet '{name}' already exists!__"

        self.bot.config["snippets"][name] = content.strip()

        # Commit it to disk
        await self.bot.save_config()

        return f"Snippet saved as `{name}`."

    @command.desc("Show all snippets")
    @command.alias("sl", "snl", "spl", "snips", "snippets")
    async def cmd_sniplist(self, msg):
        if not self.bot.config["snippets"]:
            return "__No snippets saved.__"

        out = "Snippet list:"

        for name in self.bot.config["snippets"].keys():
            out += f"\n    \u2022 **{name}**"

        return out

    @command.desc("Delete a snippet")
    @command.alias("ds", "sd", "snd", "spd", "rms", "srm", "rs", "sr", "rmsnip", "delsnip")
    async def cmd_snipdel(self, msg, name):
        if not name:
            return "__Provide the name of a snippet to delete.__"

        del self.bot.config["snippets"][name]
        await self.bot.save_config()

        return f"Snippet `{name}` deleted."
