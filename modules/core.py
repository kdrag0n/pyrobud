import command
import module
import util

class CoreModule(module.Module):
    name = 'Core'

    @command.desc('Pong')
    def cmd_ping(self, msg):
        # Telegram's timestamps are only accurate to the second, so we have to do it manually
        before = util.time_ms()
        self.bot.mresult(msg, 'Calculating response time...')
        after = util.time_ms()

        return 'Request response time: %.2f ms' % (after - before)

    @command.desc('List the commands')
    def cmd_help(self, msg):
        out = 'Command list:'

        for name, cmd in self.bot.commands.items():
            # Don't count aliases as separate commands
            if name != cmd.name:
                continue

            desc = cmd.desc if cmd.desc else '__No description provided__'
            aliases = ''
            if cmd.aliases:
                aliases = f' (aliases: {", ".join(cmd.aliases)})'

            out += f'\n    \u2022 **{cmd.name}**: {desc}{aliases}'

        return out
