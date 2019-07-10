import command
import module
import random

class TextModule(module.Module):
    name = 'Text'

    @command.desc('Unicode character from hex codepoint')
    @command.alias('cp', 'chr', 'uc')
    async def cmd_uni(self, msg, codepoint):
        if not codepoint:
            return '__Hex codepoint required.__'

        return chr(int(codepoint, 16))

    @command.desc('Apply a sarcasm/mocking filter to the given text')
    @command.alias('sar', 'sarc', 'scm', 'mock')
    async def cmd_sarcasm(self, msg, text):
        if not text:
            return '__Text required.__'

        chars = list(text)
        for idx, ch in enumerate(chars):
            if random.choice((True, False)):
                ch = ch.upper()

            chars[idx] = ch

        return ''.join(chars)
