'''Main bot class'''

from typing import Dict, Union, List, NewType
from urllib.parse import urlparse
import pyrogram as tg
import command
import inspect
import traceback
import util
import re
import requests
import tempfile
import os
import shutil
import toml
import threading
import time
import sys

Config = NewType('Config', Dict[str, Dict[str, Union[int, str]]])
CommandMap = NewType('CommandMap', Dict[str, command.Func])

class Bot():
    def __init__(self) -> None:
        self.commands: CommandMap = {}

    def setup(self, instance_name: str, config: Config) -> None:
        self.client: tg.Client = tg.Client(instance_name, api_id=config['telegram']['api_id'], api_hash=config['telegram']['api_hash'])

        self.prefix: str = config['bot']['prefix']
        self.config: Config = config

        # Collect commands
        for sym in dir(self):
            if sym.startswith('cmd_'):
                cmd_name: str = sym[4:]
                self.commands[cmd_name]: command.Func = getattr(self, sym)

        # Initialize config
        if 'snippets' not in self.config:
            self.config['snippets']: Dict[str, str] = {}
        if 'stats' not in self.config:
            self.config['stats']: Dict[str, int] = {
                'sent': 0,
                'received': 0,
                'processed': 0,
                'replaced': 0
            }
        else:
            for k in ['sent', 'received', 'processed', 'replaced']:
                if k not in self.config['stats']:
                    self.config['stats'][k] = 0

        self.last_saved_cfg: str = toml.dumps(self.config)
    
    def save_config(self, cfg: str = '') -> None:
        tmp_path: str = ''

        if not cfg:
            cfg = toml.dumps(self.config)

        try:
            with tempfile.NamedTemporaryFile('wb', delete=False) as f:
                tmp_path = f.name

                f.write(cfg.encode('utf-8'))
                self.last_saved_cfg = cfg

            shutil.move(tmp_path, 'config.toml')
        except Exception as e:
            os.remove(tmp_path)
            raise e
    
    def writer(self) -> None:
        while True:
            time.sleep(60)
            cfg: str = toml.dumps(self.config)
            if cfg != self.last_saved_cfg:
                self.save_config(cfg)

    def start(self) -> None:
        self.client.start()

        # Get info
        self.user: tg.User = self.client.get_me()
        self.uid: int = self.user.id

        # Register handlers with new info
        self.client.add_handler(tg.MessageHandler(self.on_command, tg.Filters.user(self.uid) & tg.Filters.command(list(self.commands.keys()), prefix=self.prefix)))
        self.client.add_handler(tg.MessageHandler(self.on_message))

        # Save config in the background
        self.writer_thread: threading.Thread = threading.Thread(target=self.writer)
        self.writer_thread.daemon = True
        self.writer_thread.start()

    def mresult(self, msg: tg.Message, new: str) -> None:
        self.client.edit_message_text(msg.chat.id, msg.message_id, new, parse_mode='MARKDOWN')

    def on_message(self, cl: tg.Client, msg: tg.Message) -> None:
        if msg.from_user and msg.from_user.id == self.uid:
            if msg.text:
                orig_txt = msg.text.markdown
                txt = msg.text.markdown

                # Snippets
                def snip_repl(m) -> None:
                    if m.group(1) in self.config['snippets']:
                        self.config['stats']['replaced'] += 1
                        return self.config['snippets'][m.group(1)]
                    
                    return m.group(0)

                txt = re.sub(r'\(\(([^ ]+?)\)\)', snip_repl, orig_txt)
                
                if txt != orig_txt:
                    self.mresult(msg, txt)

            # Stats
            self.config['stats']['sent'] += 1
        else:
            # Stats
            self.config['stats']['received'] += 1

    def on_command(self, cl: tg.Client, msg: tg.Message) -> None:
        cmd_func: command.Func = self.commands[msg.command[0]]
        cmd_spec: inspect.FullArgSpec = inspect.getfullargspec(cmd_func)
        cmd_args: List[str] = cmd_spec.args

        args: List[str] = []
        if len(cmd_args) == 3:
            txt = msg.text.markdown
            if cmd_args[2].startswith('plain_'):
                txt = msg.text

            args = [txt[len(self.prefix) + len(msg.command[0]) + 1:]]
        elif cmd_spec.varargs is not None and len(cmd_spec.varargs) > 0:
            args = msg.command[1:]

        try:
            ret: Union[None, str] = cmd_func(msg, *args)
        except Exception as e:
            stack = ''.join(traceback.format_tb(e.__traceback__))
            ret = f'{stack}{type(e).__name__}: {e}'
            print(ret, file=sys.stderr)
            ret = f'```{ret}```'

        if ret is not None:
            self.mresult(msg, ret)

        self.config['stats']['processed'] += 1

    # Commands, the lazy way

    @command.desc('Test this stoof (raw args too)')
    def cmd_test(self, msg: tg.Message, raw_args: str) -> str:
        if len(raw_args) > 0:
            return raw_args
        else:
            return 'It works!'

    @command.desc('Test arguments (echo)')
    def cmd_argtest(self, msg: tg.Message, *args) -> str:
        if len(args) > 0:
            return ' '.join(args)
        else:
            return '__No arguments supplied__'
    
    @command.desc('Pong')
    def cmd_ping(self, msg: tg.Message) -> str:
        # Telegram's timestamps are only accurate to the second... so we have to do it manually
        before = util.time_ms()
        self.mresult(msg, 'Calculating response time...')
        after = util.time_ms()

        return 'Request response time: %.2f ms' % (after - before)
    
    @command.desc('Time setting 1 + 1 into a variable because why not')
    def cmd_time11(self, msg: tg.Message) -> str:
        before = util.time_us()
        self.var = 1 + 1
        after = util.time_us()

        el_us = after - before
        return '`var = 1 + 1`: %.3f ms / %.2f μs / %.0f ns' % (el_us / 1000.0, el_us, el_us * 1000.0)

    @command.desc('List the commands')
    def cmd_help(self, msg: tg.Message) -> str:
        out = 'Command list:'

        for name, cmd in self.commands.items():
            desc = getattr(cmd, 'description', '__No description provided.__')
            out += f'\n    \u2022 **{name}**: {desc}'

        return out

    @command.desc(r'¯\_(ツ)_/¯')
    def cmd_shrug(self, msg: tg.Message, raw_args: str) -> str:
        if len(msg.text.markdown) > 0:
            return msg.text.markdown[len(self.prefix) + 6:] + r' ¯\_(ツ)_/¯'
        else:
            return r'¯\_(ツ)_/¯'

    @command.desc(r'(╯°□°）╯︵ ┻━┻')
    def cmd_tableflip(self, msg: tg.Message, raw_args: str) -> str:
        if len(msg.text.markdown) > 0:
            return msg.tex.markdownt[len(self.prefix) + 6:] + r' (╯°□°）╯︵ ┻━┻'
        else:
            return r'(╯°□°）╯︵ ┻━┻'

    @command.desc(r'┬─┬ ノ( ゜-゜ノ)')
    def cmd_unflip(self, msg: tg.Message, raw_args: str) -> str:
        if len(msg.text.markdown) > 0:
            return msg.text.markdown[len(self.prefix) + 6:] + r' ┬─┬ ノ( ゜-゜ノ)'
        else:
            return r'┬─┬ ノ( ゜-゜ノ)'

    @command.desc('z e r o')
    def cmd_zwsp(self, msg: tg.Message) -> str:
        return '>\u200b'
    
    @command.desc('Unicode character from hex codepoint')
    def cmd_uni(self, msg: tg.Message, codepoint: str) -> str:
        if not str: return '__Hex codepoint required.__'
        return chr(int(codepoint, 16))

    @command.desc('Save a snippet (fetch: `((snippet))`)')
    def cmd_snip(self, msg: tg.Message, *args: List[str]) -> str:
        if not args:
            return '__Specify a name for the snippet, then reply to a message or provide text.__'

        if msg.reply_to_message:
            content = msg.reply_to_message.text.markdown
            if not content:
                if len(args) > 1:
                    content = ' '.join(args[1:])
                else:
                    return '__Reply to a message with text or provide text after snippet name.__'
        else:
            if len(args) > 1:
                content = ' '.join(args[1:])
            else:
                return '__Reply to a message with text or provide text after snippet name.__'
        
        name = args[0]
        if name in self.config['snippets']:
            return f'__Snippet \'{name}\' already exists!__'
        
        self.config['snippets'][name] = content.strip()

        # Actually save it to disk
        self.save_config()

        return f'Snippet saved as `{name}`.'

    @command.desc('Show all snippets')
    def cmd_sniplist(self, msg: tg.Message) -> str:
        if not self.config['snippets']:
            return '__No snippets saved.__'

        out = 'Snippet list:'

        for name in self.config['snippets'].keys():
            out += f'\n    \u2022 **{name}**'

        return out
    
    @command.desc('Delete a snippet')
    def cmd_snipdel(self, msg: tg.Message, name: str) -> str:
        if not name: return '__Provide the name of a snippet to delete.__'
        
        del self.config['snippets'][name]
        self.save_config()

        return f'Snippet `{name}` deleted.'

    @command.desc('Evaluate code')
    def cmd_eval(self, msg: tg.Message, raw_args: str) -> str:
        before = util.time_us()
        result = eval(raw_args)
        after = util.time_us()

        el_us = after - before
        el_str = '%.3f ms, %.2f μs' % (el_us / 1000.0, el_us)

        return f'''In:
```{raw_args}```

Out:
```{str(result)}```

Time: {el_str}'''

    @command.desc('Get the code of a command')
    def cmd_src(self, msg: tg.Message, cmd_name: str) -> str:
        if cmd_name is None or len(cmd_name) < 1:
            return '__Command name required to get source code.__'
        
        src = inspect.getsource(self.commands[cmd_name])
        filtered_src = re.sub(r'^    ', '', src, flags=re.MULTILINE)
        return f'```{filtered_src}```\u200b'

    @command.desc('Evalulate code (statement)')
    def cmd_exec(self, msg: tg.Message) -> str:
        exec(msg)
        return 'Evaulated.'

    @command.desc('Paste message text to Hastebin')
    def cmd_haste(self, msg: tg.Message, text: str) -> str:
        orig: tg.Message = msg.reply_to_message
        if orig is None:
            if text:
                txt = text
            else:
                return '__Reply to a message or provide text in command.__'
        else:
            txt = orig.text

        resp: Dict[str, Union[bool, str]] = requests.post('https://hastebin.com/documents', data=txt).json()
        return f'https://hastebin.com/{resp["key"]}'
    
    @command.desc('Paste message text to Dogbin')
    def cmd_dog(self, msg: tg.Message, text: str) -> str:
        orig: tg.Message = msg.reply_to_message
        if orig is None:
            if text:
                txt = text
            else:
                return '__Reply to a message or provide text in command.__'
        else:
            txt = orig.text

        orig: tg.Message = msg.reply_to_message
        resp: Dict[str, Union[bool, str]] = requests.post('https://del.dog/documents', data=txt).json()
        return f'https://del.dog/{resp["key"]}'

    @command.desc('Upload replied-to file to file.io')
    def cmd_fileio(self, msg: tg.Message, expires: str) -> str:
        if msg.reply_to_message is None:
            return '__Reply to a message with the file to upload.__'
        
        if expires == 'help':
            return '__Expiry format: 1y/12m/52w/365d__'
        elif expires:
            if expires[-1] not in ['y', 'm', 'w', 'd']:
                return '__Unknown unit. Expiry format: 1y/12m/52w/365d__'
            else:
                try:
                    int(expires[:-1])
                except ValueError:
                    return '__Invalid number. Expiry format: 1y/12m/52w/365d__'
        else:
            expires = '1w'

        def prog_func(cl: tg.Client, current: int, total: int):
            self.mresult(msg, f'Downloading...\nProgress: `{float(current) / 1000.0}/{float(total) / 1000.0}` KB')

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.client.download_media(msg.reply_to_message, file_name=tmpdir + '/', progress=prog_func, progress_args=())
            if not path:
                return '__Error downloading file__'

            self.mresult(msg, 'Uploading...')
            with open(path, 'rb') as f:
                resp = requests.post(f'https://file.io/?expires={expires}', files={'file': f}).json()

            if not resp['success']:
                return '__Error uploading file__'

            return resp['link']
    
    @command.desc('Upload replied-to file to transfer.sh')
    def cmd_transfer(self, msg: tg.Message) -> str:
        if msg.reply_to_message is None:
            return '__Reply to a message with the file to upload.__'
        
        def prog_func(cl: tg.Client, current: int, total: int):
            self.mresult(msg, f'Downloading...\nProgress: `{float(current) / 1000.0}/{float(total) / 1000.0}` KB')

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.client.download_media(msg.reply_to_message, file_name=tmpdir + '/', progress=prog_func, progress_args=())
            if not path:
                return '__Error downloading file__'

            self.mresult(msg, 'Uploading...')
            with open(path, 'rb') as f:
                resp = requests.put(f'https://transfer.sh/{os.path.basename(path)}', data=f)

            if not resp.ok:
                return '__Error uploading file__'

            return resp.text

    @command.desc('Show message stats')
    def cmd_stats(self, msg: tg.Message) -> str:
        st = self.config['stats']

        return f'''Stats:
    \u2022 Messages received: {st['received']}
    \u2022 Messages sent: {st['sent']}
    \u2022 Commands processed: {st['processed']}
    \u2022 Snippets replaced: {st['replaced']}'''

    @command.desc('Get plain text of a message (debug)')
    def cmd_gtx(self, msg: tg.Message) -> str:
        if not msg.reply_to_message: return '__Reply to a message to get the text of.__'
        return f'```{msg.reply_to_message.text}```'
    
    @command.desc('Send text (debug)')
    def cmd_echo(self, msg: tg.Message, text: str) -> str:
        if not text: return '__Provide text to send.__'
        return text

    @command.desc('Set up @KarafuruBot')
    def cmd_ksetup(self, msg: tg.Message, plain_params: str) -> str:
        if not msg.chat: return '__This can only be used in groups.__'

        cfg_err: str = '''**Invalid TOML config.** The following options are supported:

```rules = ["No spam", "English only"]
extra_rules = ["Respect others"]

[buttons]
"XDA Thread" = "https://forum.xda-developers.com/"
GitHub = "https://github.com/"```

{}'''

        extra_btn: str = ''
        rules: List[str] = [
            'No spam',
            'English only',
            'Respect others',
            'No NSFW',
            'No extreme off-topic'
        ]

        ex_btn_map: Dict[str, str] = {}

        if plain_params:
            try:
                cfg = toml.loads(plain_params)
            except Exception as e:
                return cfg_err.format(str(e))

            if 'rules' in cfg:
                rules = cfg['rules']
            if 'extra_rules' in cfg:
                rules.extend(cfg['extra_rules'])
            
            if 'buttons' in cfg:
                for name, dest in cfg['buttons'].items():
                    if '://' in dest:
                        p_dest = urlparse(dest)
                        ex_btn_map[name] = f'{p_dest.netloc}{p_dest.path}'
                    else:
                        ex_btn_map[name] = dest

        rule_str = f'    \u2022 {rules[0]}'
        for rule in rules[1:]:
            rule_str += f'\n    \u2022 {rule}'
        
        for name, dest in ex_btn_map.items():
            extra_btn += f'\n[{name}](buttonurl://{dest})'

        before = util.time_ms()

        try:
            self.client.promote_chat_member(msg.chat.id, 'KarafuruBot', can_change_info=False)
        except Exception:
            self.mresult(msg, '**WARNING**: Unable to promote @KarafuruBot')

        first = 'first'
        commands: List[str] = [
            'welcome on',
            'goodbye off',
            'disable afk',
            'warnlimit 3',
            'strongwarn off'
            f'''setwelcome **Welcome**, {first}!
Please read the rules __before__ chatting.
[Rules](buttonurl://t.me/KarafuruBot?start={msg.chat.id}{extra_btn}''',
            'cleanwelcome on',
            f'setrules \u200b{rule_str}',
            'setflood 16',
            'gbanstat on',
            'gmutestat on',
            'reports on'
        ]

        for cmd in commands:
            csplit = cmd.split(' ')
            _cmd = '/' + csplit[0] + '@KarafuruBot ' + ' '.join(csplit[1:])
            self.client.send_message(msg.chat.id, _cmd, parse_mode='MARKDOWN')
            time.sleep(0.200) # ratelimit
        
        # Clean up the mess
        if msg.reply_to_message:
            msg.reply_to_message.reply('/purge@KarafuruBot')
        else:
            msg.reply('/purge@KarafuruBot')

        after = util.time_ms()

        return f'Finished in `{(after - before) / 1000.0}` seconds.'
