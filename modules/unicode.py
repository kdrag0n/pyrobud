import command
import module

class UnicodeModule(module.Module):
    name = 'Unicode'

    @command.desc('Get a zero-width space')
    def cmd_zwsp(self, msg):
        return '>\u200b'

    @command.desc('Unicode character from hex codepoint')
    @command.alias('cp')
    def cmd_uni(self, msg, codepoint):
        if not codepoint:
            return '__Hex codepoint required.__'

        return chr(int(codepoint, 16))
