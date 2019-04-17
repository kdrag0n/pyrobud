import command
import module
import util

USEC_PER_HOUR = 60 * 60 * 1000000
USEC_PER_DAY = USEC_PER_HOUR * 24

class StatsModule(module.Module):
    name = 'Stats'

    def on_load(self):
        if 'stats' not in self.bot.config:
            self.bot.config['stats'] = {}

        keys = [
            'sent',
            'received',
            'processed',
            'replaced',
            'sent_edits',
            'received_edits',
            'sent_stickers',
            'received_stickers',
            'uptime',
            'spambots_banned',
            'stickers_created'
        ]

        for k in keys:
            if k not in self.bot.config['stats']:
                self.bot.config['stats'][k] = 0

    def on_start(self, time_us):
        self.last_time = time_us

    def on_message(self, msg):
        if msg.from_user and msg.from_user.id == self.bot.uid:
            base_stat = 'sent'
        else:
            base_stat = 'received'

        stat = base_stat
        if msg.edit_date:
            stat += '_edits'

        self.bot.config['stats'][stat] += 1

        if msg.sticker:
            stat = base_stat + '_stickers'
            self.bot.config['stats'][stat] += 1

        self.update_uptime()

    def on_command(self, msg, cmd_info, args):
        self.bot.config['stats']['processed'] += 1

    def update_uptime(self):
        now = util.time_us()
        delta_us = now - self.last_time
        self.bot.config['stats']['uptime'] += delta_us
        self.last_time = now

    def calc_pct(self, num1, num2):
        if not num2:
            return '0'

        return '{:.1f}'.format((num1 / num2) * 100).rstrip('0').rstrip('.')

    def calc_ph(self, stat, uptime):
        up_hr = max(1, uptime) / USEC_PER_HOUR
        return '{:.1f}'.format(stat / up_hr).rstrip('0').rstrip('.')

    def calc_pd(self, stat, uptime):
        up_day = max(1, uptime) / USEC_PER_DAY
        return '{:.1f}'.format(stat / up_day).rstrip('0').rstrip('.')

    @command.desc('Show chat stats (pass `reset` to reset stats)')
    @command.alias('stat')
    def cmd_stats(self, msg, args):
        if args == "reset":
            self.bot.config['stats'] = {}
            self.on_load()
            self.on_start(util.time_us())
            return '__All stats have been reset.__'

        self.update_uptime()
        self.bot.save_config()

        st = self.bot.config['stats']
        uptime = st['uptime']
        sent = st['sent']
        sent_stickers = st['sent_stickers']
        recv = st['received']
        recv_stickers = st['received_stickers']
        processed = st['processed']
        replaced = st['replaced']
        banned = st['spambots_banned']
        stickers = st['stickers_created']

        return f'''**Stats since last reset**:
    • **Total time elapsed**: {util.format_duration_us(uptime)}
    • **Messages received**: {recv} ({self.calc_ph(recv, uptime)}/h) • {self.calc_pct(recv_stickers, recv)}% are stickers
    • **Messages sent**: {sent} ({self.calc_ph(sent, uptime)}/h) • {self.calc_pct(sent_stickers, sent)}% are stickers
    • **Percent of total messages sent**: {self.calc_pct(sent, sent + recv)}%
    • **Commands processed**: {processed} ({self.calc_ph(processed, uptime)}/h) • {self.calc_pct(processed, sent)}% of sent messages
    • **Snippets replaced**: {replaced} ({self.calc_ph(replaced, uptime)}/h) • {self.calc_pct(replaced, sent)}% of sent messages
    • **Spambots banned**: {banned} ({self.calc_pd(banned, uptime)}/day)
    • **Stickers created**: {stickers} ({self.calc_pd(stickers, uptime)}/day)'''
