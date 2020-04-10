import random
import string
import unicodedata
from typing import ClassVar

from .. import command, module


class TextModule(module.Module):
    name: ClassVar[str] = "Text"

    @command.desc("Unicode character from hex codepoint")
    @command.usage("[hexadecimal Unicode codepoint]")
    @command.alias("cp", "chr", "uc", "c")
    async def cmd_uni(self, ctx: command.Context) -> str:
        codepoint = ctx.input
        return chr(int(codepoint, 16))

    @command.desc(
        "Get a character equivalent to a zero-width space that works on Telegram"
    )
    @command.alias("empty")
    async def cmd_zwsp(self, ctx: command.Context) -> str:
        return "\U000e0020"

    @command.desc("Apply a sarcasm/mocking filter to the given text")
    @command.usage("[text to filter]", reply=True)
    @command.alias("sarcasm", "sar", "sarc", "scm")
    async def cmd_mock(self, ctx: command.Context) -> str:
        text = ctx.input
        chars = list(text)
        for idx, ch in enumerate(chars):
            ch = ch.upper() if random.choice((True, False)) else ch.lower()
            chars[idx] = ch

        return "".join(chars)

    @command.desc("Apply strike-through formatting to the given text")
    @command.usage("[text to format]", reply=True)
    @command.alias("str", "strikethrough")
    async def cmd_strike(self, ctx: command.Context) -> str:
        text = ctx.input
        return "\u0336".join(text) + "\u0336"

    @command.desc("Generate fake Google Play-style codes")
    @command.usage(
        "[number of codes to generate?] [length of each code?]", optional=True
    )
    @command.alias("genkey", "gencodes", "genkeys")
    async def cmd_gencode(self, ctx: command.Context) -> str:
        count = 10
        length = 23

        if ctx.args:
            try:
                count = int(ctx.args[0])
            except ValueError:
                return "__Invalid number provided for count.__"

        if len(ctx.args) >= 2:
            try:
                length = int(ctx.args[1])
            except ValueError:
                return "__Invalid number provided for length.__"

        codes = []
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(count):
            code = "".join(random.choice(alphabet) for _ in range(length))
            codes.append(code)

        codes_str = "\n".join(codes)
        return f"```{codes_str}```"

    @command.desc("Dissect a string into named Unicode codepoints")
    @command.usage("[text to dissect]", reply=True)
    @command.alias("cinfo", "chinfo", "ci")
    async def cmd_charinfo(self, ctx: command.Context) -> str:
        text = ctx.input

        chars = []
        for char in text:
            # Don't preview characters that mess up the output
            preview = char not in "`"

            # Attempt to get the codepoint's name
            try:
                name: str = unicodedata.name(char)
            except ValueError:
                # Control characters don't have names, so insert a placeholder
                # and prevent the character from being rendered to avoid breaking
                # the output
                name = "UNNAMED CONTROL CHARACTER"
                preview = False

            # Render the line and only show the character if safe
            line = f"`U+{ord(char):04X}` {name}"
            if preview:
                line += f" `{char}`"

            chars.append(line)

        return "\n".join(chars)

    @command.desc("Replace the spaces in a string with clap emoji")
    @command.usage("[text to filter]", reply=True)
    async def cmd_clap(self, ctx: command.Context) -> str:
        text = ctx.input
        return "\n".join("👏".join(line.split()) for line in text.split("\n"))
