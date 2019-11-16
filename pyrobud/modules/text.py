import random
import string
import unicodedata

from .. import command, module


class TextModule(module.Module):
    name = "Text"

    @command.desc("Unicode character from hex codepoint")
    @command.alias("cp", "chr", "uc", "c")
    async def cmd_uni(self, msg, codepoint):
        if not codepoint:
            return "__Hex codepoint required.__"

        return chr(int(codepoint, 16))

    @command.desc("Get a character equivalent to a zero-width space that works on Telegram")
    @command.alias("empty")
    async def cmd_zwsp(self, msg):
        return "\U000e0020"

    @command.desc("Apply a sarcasm/mocking filter to the given text")
    @command.alias("sar", "sarc", "scm", "mock")
    async def cmd_sarcasm(self, msg, text):
        if not text:
            if msg.is_reply:
                reply_msg = await msg.get_reply_message()
                text = reply_msg.text
            else:
                return "__Reply to a message with text or provide text to filter.__"

        chars = list(text)
        for idx, ch in enumerate(chars):
            if random.choice((True, False)):
                ch = ch.upper()

            chars[idx] = ch

        return "".join(chars)

    @command.desc("Apply strike-through formatting to the given text")
    @command.alias("str", "strikethrough")
    async def cmd_strike(self, msg, text):
        if not text:
            return "__Text required.__"

        return "\u0336".join(text) + "\u0336"

    @command.desc("Generate fake Google Play-style codes (optional arguments: count, length)")
    @command.alias("genkey")
    async def cmd_gencode(self, msg, *args):
        count = 10
        length = 23

        if args:
            try:
                count = int(args[0])
            except ValueError:
                return "__Invalid number provided for count.__"

        if len(args) >= 2:
            try:
                length = int(args[1])
            except ValueError:
                return "__Invalid number provided for length.__"

        codes = []
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(count):
            code = "".join([random.choice(alphabet) for _ in range(length)])
            codes.append(code)

        codes_str = "\n".join(codes)
        return f"```{codes_str}```"

    @command.desc("Dissect a string into named Unicode codepoints")
    @command.alias("cinfo", "chinfo", "ci")
    async def cmd_charinfo(self, msg, text):
        if not text and msg.is_reply:
            reply_msg = await msg.get_reply_message()
            text = reply_msg.text

        if not text:
            return "__Provide text or reply to a message with text to dissect.__"

        chars = []
        for char in text:
            # Don't preview characters that mess up the output
            preview = char not in "`"

            # Attempt to get the codepoint's name
            try:
                name = unicodedata.name(char)
            except ValueError:
                # Control characters don't have names, so insert a placeholder
                # and prevent the character from being rendered to avoid breaking
                # the output
                name = "UNNAMED CONTROL CHARACTER"
                preview = False

            # Render the line and only show the character if safe
            line = "`U+%04X` %s" % (ord(char), name)
            if preview:
                line += " `%c`" % char

            chars.append(line)

        return "\n".join(chars)

    @command.desc("Replace the spaces in a string with clap emojis")
    async def cmd_clap(self, msg, text):
        if not text:
            return "__Provide text to insert claps into.__"

        return "👏".join(text.split())
