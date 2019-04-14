import command
import module

class StatsModule(module.Module):
    name = 'Statistics'

    def on_load(self):
        if 'stats' not in self.bot.config:
            self.bot.config['stats'] = {
                'sent': 0,
                'received': 0,
                'processed': 0,
                'replaced': 0
            }
        else:
            for k in ['sent', 'received', 'processed', 'replaced']:
                if k not in self.bot.config['stats']:
                    self.bot.config['stats'][k] = 0

    def on_message(self, msg):
        if msg.from_user and msg.from_user.id == self.bot.uid:
            # Stats
            self.bot.config['stats']['sent'] += 1
        else:
            # Stats
            self.bot.config['stats']['received'] += 1

    @command.desc('Show message stats')
    def cmd_stats(self, msg):
        st = self.bot.config['stats']

        return f'''Stats:
    \u2022 Messages received: {st['received']}
    \u2022 Messages sent: {st['sent']}
    \u2022 Percent of total messages sent: {'%.2f' % ((float(st['sent']) / float(st['received'])) * 100)}%
    \u2022 Commands processed: {st['processed']}
    \u2022 Snippets replaced: {st['replaced']}
    \u2022 Percent of sent messages processed as commands: {'%.2f' % ((float(st['processed']) / float(st['sent'])) * 100)}%
    \u2022 Percent of sent messages with snippets: {'%.2f' % ((float(st['replaced']) / float(st['sent'])) * 100)}%'''
