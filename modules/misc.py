import command
import module
import time
import toml
import util

class MiscModule(module.Module):
    name = 'Miscellaneous'

    @command.desc('Set up Marie-based bots (@MissRose_bot, etc)')
    def cmd_bsetup(self, msg, params):
        if not msg.chat:
            return '__This can only be used in groups.__'
        plain_params = util.filter_input_block(params)

        cfg_err = '''**Invalid TOML config.** The following options are supported:

```
# Bot to setup
target = "MissRose_bot"

# Default rules
rules = ["No spam", "English only", "Respect others", "No NSFW"]
extra_rules = ["No extreme off-topic"]

# Add ":same" at the end of links to put buttons on the same line
[buttons]
"XDA Thread" = "https://forum.xda-developers.com/"
GitHub = "https://github.com/"```

{}'''

        if plain_params.startswith('?') or plain_params.startswith('help'):
            return cfg_err.format('')

        extra_btn = ''
        rules = [
            'No spam',
            'English only',
            'Respect others',
            'No NSFW content',
            'No extreme off-topic'
        ]
        target = 'MissRose_bot'

        ex_btn_map = {}

        if plain_params:
            try:
                cfg = toml.loads(plain_params)
            except Exception as e:
                return cfg_err.format(str(e))

            if 'target' in cfg:
                target = cfg['target']

            if 'rules' in cfg:
                rules = cfg['rules']
            if 'extra_rules' in cfg:
                rules.extend(cfg['extra_rules'])

            if 'buttons' in cfg:
                for name, dest in cfg['buttons'].items():
                    ex_btn_map[name] = dest

        rule_str = f'    \u2022 {rules[0]}'
        for rule in rules[1:]:
            rule_str += f'\n    \u2022 {rule}'

        for name, dest in ex_btn_map.items():
            extra_btn += f'\n[{name}](buttonurl://{dest})'

        before = util.time_us()

        try:
            self.bot.client.promote_chat_member(msg.chat.id, target, can_change_info=False)
        except Exception:
            self.bot.mresult(msg, f'**WARNING**: Unable to promote @{target}')

        first = '{first}'
        srules = '{rules}'
        commands = [
            'welcome on',
            'goodbye off',
            'warnlimit 3',
            'strongwarn off',
            f'''setwelcome *Welcome*, {first}!
Please read the rules before chatting. {srules}{extra_btn}''',
            'cleanwelcome on',
            f'setrules \u200b{rule_str}',
            'setflood 20',
            'setfloodmode tmute 3h',
            'gbanstat on',
            'gmutestat on',
            'reports on',
            'cleanservice on',
            'welcomemute on',
            'welcomemutetime 3h'
        ]

        for cmd in commands:
            csplit = cmd.split(' ')
            _cmd = '/' + csplit[0] + f'@{target} ' + ' '.join(csplit[1:])
            self.bot.client.send_message(msg.chat.id, _cmd, parse_mode='HTML')
            time.sleep(0.180) # ratelimit

        # Clean up the mess
        if msg.reply_to_message:
            msg.reply_to_message.reply(f'/purge@{target}')
        else:
            msg.reply(f'/purge@{target}')

        after = util.time_us()

        return f'Setup completed in {util.format_duration_us(after - before)}.'

    @command.desc('Mass forward one message.')
    @command.alias('massfwd', 'fwd')
    def cmd_forward(self, msg, _count):
        if not _count:
            return '__Provide the amount of times to forward the message.__'
        if not msg.reply_to_message:
            return '__Reply to the message to forward.__'

        try:
            count = int(_count)
        except ValueError:
            return '__Specify a valid number of times to forward the message.__'

        for _ in range(count):
            self.bot.client.forward_messages(msg.chat.id, msg.chat.id, msg.reply_to_message.message_id)
            time.sleep(0.15)
