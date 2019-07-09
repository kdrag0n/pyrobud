import command
import module

class UnicodeModule(module.Module):
    name = 'Unicode'

    @command.desc('Unicode character from hex codepoint')
    @command.alias('cp', 'chr', 'uc')
    async def cmd_uni(self, msg, codepoint):
        if not codepoint:
            return '__Hex codepoint required.__'

        return chr(int(codepoint, 16))
