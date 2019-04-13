'''Main bot class'''

from typing import Dict, Union, List, NewType
from urllib.parse import urlparse
from PIL import Image
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
import yaml
import json
import os.path
import subprocess

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
                cmd_func: command.Func = getattr(self, sym)
                cmd_info: command.Info = command.Info(cmd_name, cmd_func)

                if cmd_name in self.commands:
                    orig: command.Info = self.commands[cmd_name]
                    print(f"WARNING: overwriting command '{orig.name}' ({orig.desc}) with '{cmd_name}' ({cmd_info.desc})")

                self.commands[cmd_name]: command.Info = cmd_info

                for alias in getattr(cmd_func, 'aliases', []):
                    self.commands[alias]: command.Info = cmd_info

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
        if 'todo' not in self.config:
            self.config['todo']: Dict[str, List[str]] = {}
        if 'user' not in self.config:
            self.config['user']: Dict[str, str] = {}
        if 'stickers' not in self.config:
            self.config['stickers']: Dict[str, str] = {}

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
        t = self.config['telegram']
        api_id = str(t['api_id'])
        api_hash = t['api_hash']

        if api_id in new:
            new = new.replace(api_id, '[REDACTED]')
        if api_hash in new:
            new = new.replace(api_hash, '[REDACTED]')
        if self.user.phone_number in new:
            new = new.replace(self.user.phone_number, '[REDACTED]')

        self.client.edit_message_text(msg.chat.id, msg.message_id, new, parse_mode='MARKDOWN', disable_web_page_preview=True)

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

                txt = re.sub(r'/([^ ]+?)/', snip_repl, orig_txt)

                if txt != orig_txt:
                    self.mresult(msg, txt)

            # Stats
            self.config['stats']['sent'] += 1
        else:
            # Stats
            self.config['stats']['received'] += 1

    def on_command(self, cl: tg.Client, msg: tg.Message) -> None:
        cmd_info: command.Info = self.commands[msg.command[0]]
        cmd_func: command.Func = cmd_info.func
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

    # Commands

    @command.desc('Pong')
    def cmd_ping(self, msg: tg.Message) -> str:
        # Telegram's timestamps are only accurate to the second, so we have to do it manually
        before = util.time_ms()
        self.mresult(msg, 'Calculating response time...')
        after = util.time_ms()

        return 'Request response time: %.2f ms' % (after - before)

    @command.desc('Time `1 + 1`')
    def cmd_time11(self, msg: tg.Message) -> str:
        reps = 1000000

        before = util.time_us()
        for i in range(reps):
            v = 1 + 1
        after = util.time_us()

        el_us = (after - before) / reps
        return '`1 + 1`: %.0f ns' % (el_us * 1000)

    @command.desc('List the commands')
    def cmd_help(self, msg: tg.Message) -> str:
        out = 'Command list:'

        for name, cmd in self.commands.items():
            # Don't count aliases as separate commands
            if name != cmd.name :
                continue

            desc = cmd.desc if cmd.desc else '__No description provided__'
            aliases = ''
            if cmd.aliases:
                aliases = f' (aliases: {", ".join(cmd.aliases)})'

            out += f'\n    \u2022 **{cmd.name}**: {desc}{aliases}'

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
            return msg.text.markdown[len(self.prefix) + 6:] + r' (╯°□°）╯︵ ┻━┻'
        else:
            return r'(╯°□°）╯︵ ┻━┻'

    @command.desc(r'┬─┬ ノ( ゜-゜ノ)')
    def cmd_unflip(self, msg: tg.Message, raw_args: str) -> str:
        if len(msg.text.markdown) > 0:
            return msg.text.markdown[len(self.prefix) + 6:] + r' ┬─┬ ノ( ゜-゜ノ)'
        else:
            return r'┬─┬ ノ( ゜-゜ノ)'

    @command.desc(r'( ͡° ͜ʖ ͡°)')
    def cmd_lenny(self, msg: tg.Message, raw_args: str) -> str:
        if len(msg.text.markdown) > 0:
            return msg.text.markdown[len(self.prefix) + 6:] + r' ( ͡° ͜ʖ ͡°)'
        else:
            return r'( ͡° ͜ʖ ͡°)'

    @command.desc('z e r o')
    def cmd_zwsp(self, msg: tg.Message) -> str:
        return '>\u200b'

    @command.desc('Unicode character from hex codepoint')
    def cmd_uni(self, msg: tg.Message, codepoint: str) -> str:
        if not str: return '__Hex codepoint required.__'
        return chr(int(codepoint, 16))

    @command.desc('Save a snippet (fetch: `/snippet/`)')
    @command.alias('sn', 'sp')
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
    @command.alias('sl', 'snl', 'spl')
    def cmd_sniplist(self, msg: tg.Message) -> str:
        if not self.config['snippets']:
            return '__No snippets saved.__'

        out = 'Snippet list:'

        for name in self.config['snippets'].keys():
            out += f'\n    \u2022 **{name}**'

        return out

    @command.desc('Delete a snippet')
    @command.alias('ds', 'sd', 'snd', 'spd', 'rms', 'srm', 'rs', 'sr')
    def cmd_snipdel(self, msg: tg.Message, name: str) -> str:
        if not name: return '__Provide the name of a snippet to delete.__'

        del self.config['snippets'][name]
        self.save_config()

        return f'Snippet `{name}` deleted.'

    @command.desc('Evaluate code')
    @command.alias('ev', 'c')
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
    @command.alias('hs')
    def cmd_haste(self, msg: tg.Message, text: str) -> str:
        orig: tg.Message = msg.reply_to_message
        if orig is None:
            if text:
                txt = text
            else:
                return '__Reply to a message or provide text in command.__'
        else:
            txt = orig.text
            if not txt:
                if orig.document:
                    def prog_func(cl: tg.Client, current: int, total: int):
                        self.mresult(msg, f'Downloading...\nProgress: `{float(current) / 1000.0}/{float(total) / 1000.0}` KB')

                    with tempfile.TemporaryDirectory() as tmpdir:
                        path = self.client.download_media(msg.reply_to_message, file_name=tmpdir + '/', progress=prog_func, progress_args=())
                        if not path:
                            return '__Error downloading file__'

                        with open(path, 'rb') as f:
                            txt = f.read().decode('utf-8')
                else:
                    return '__Reply to a message with text or a text file, or provide text in command.__'

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
            if not txt:
                if orig.document:
                    def prog_func(cl: tg.Client, current: int, total: int):
                        self.mresult(msg, f'Downloading...\nProgress: `{float(current) / 1000.0}/{float(total) / 1000.0}` KB')

                    with tempfile.TemporaryDirectory() as tmpdir:
                        path = self.client.download_media(msg.reply_to_message, file_name=tmpdir + '/', progress=prog_func, progress_args=())
                        if not path:
                            return '__Error downloading file__'

                        with open(path, 'rb') as f:
                            txt = f.read().decode('utf-8')
                else:
                    return '__Reply to a message with text or a text file, or provide text in command.__'

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
    \u2022 Percent of total messages sent: {'%.2f' % ((float(st['sent']) / float(st['received'])) * 100)}%
    \u2022 Commands processed: {st['processed']}
    \u2022 Snippets replaced: {st['replaced']}
    \u2022 Percent of sent messages processed as commands: {'%.2f' % ((float(st['processed']) / float(st['sent'])) * 100)}%
    \u2022 Percent of sent messages with snippets: {'%.2f' % ((float(st['replaced']) / float(st['sent'])) * 100)}%'''

    @command.desc('Get plain text of a message (debug)')
    def cmd_gtx(self, msg: tg.Message) -> str:
        if not msg.reply_to_message: return '__Reply to a message to get the text of.__'
        return f'```{msg.reply_to_message.text}```'

    @command.desc('Send text (debug)')
    def cmd_echo(self, msg: tg.Message, text: str) -> str:
        if not text: return '__Provide text to send.__'
        return text

    @command.desc('Set up Marie-based bots (@MissRose_bot, etc)')
    def cmd_bsetup(self, msg: tg.Message, plain_params: str) -> str:
        if not msg.chat: return '__This can only be used in groups.__'

        cfg_err: str = '''**Invalid TOML config.** The following options are supported:

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

        extra_btn: str = ''
        rules: List[str] = [
            'No spam',
            'English only',
            'Respect others',
            'No NSFW',
            'No extreme off-topic'
        ]
        target: str = 'MissRose_bot'

        ex_btn_map: Dict[str, str] = {}

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

        before = util.time_ms()

        try:
            self.client.promote_chat_member(msg.chat.id, target, can_change_info=False)
        except Exception:
            self.mresult(msg, f'**WARNING**: Unable to promote @{target}')

        first = '{first}'
        srules = '{rules}'
        commands: List[str] = [
            'welcome on',
            'goodbye off',
            'warnlimit 3',
            'strongwarn off',
            f'''setwelcome *Welcome*, {first}!
Please read the rules before chatting. {srules}{extra_btn}''',
            'cleanwelcome on',
            f'setrules \u200b{rule_str}',
            'setflood 16',
            'gbanstat on',
            'gmutestat on',
            'reports on',
            'cleanservice on'
        ]

        for cmd in commands:
            csplit = cmd.split(' ')
            _cmd = '/' + csplit[0] + f'@{target} ' + ' '.join(csplit[1:])
            self.client.send_message(msg.chat.id, _cmd, parse_mode='HTML')
            time.sleep(0.180) # ratelimit

        # Clean up the mess
        if msg.reply_to_message:
            msg.reply_to_message.reply(f'/purge@{target}')
        else:
            msg.reply(f'/purge@{target}')

        after = util.time_ms()

        return f'Finished in `{(after - before) / 1000.0}` seconds.'

    @command.desc('Add an item to the todo list')
    @command.alias('t', 'td')
    def cmd_todo(self, msg: tg.Message, args: str) -> str:
        if not args: return '__Provide an item to add to the todo list.__'
        if args.startswith('list ') or args == "list": return self.cmd_todolist(msg, args[5:])
        if args.startswith('del '): return self.cmd_tododel(msg, args[4:])

        item = args
        l_name = 'main'

        if l_name not in self.config['todo']:
            self.config['todo'][l_name]: List[str] = []

        self.config['todo'][l_name].append(item)
        self.save_config()

        idx = len(self.config['todo'][l_name])
        return f'Added item `{item}` as entry {idx}.'

    @command.desc('Show the todo list')
    @command.alias('tl')
    def cmd_todolist(self, msg: tg.Message, l_name: str) -> str:
        if not l_name:
            l_name = 'main'
        if l_name not in self.config['todo']:
            return f'__List \'{l_name}\' doesn\'t exist.'
        if not self.config['todo'][l_name]:
            return '__Todo list is empty.__'

        out = 'Todo list:'

        for idx, item in enumerate(self.config['todo'][l_name]):
            out += f'\n    {idx + 1}. {item}'

        return out

    @command.desc('Delete an item from the todo list')
    @command.alias('tdd', 'tld', 'tr', 'trm', 'dt', 'done')
    def cmd_tododel(self, msg: tg.Message, idx_str: str) -> str:
        if not idx_str: return '__Provide the entry number or entry text to delete.__'
        list = self.config['todo']['main']

        try:
            idx = int(idx_str)
        except ValueError:
            try:
                idx = list.index(idx_str) + 1
            except ValueError:
                return '__Invalid entry number or text to delete.__'

        l = len(list)
        if idx > l:
            return f'__Entry number out of range, there are {l} entries.__'

        idx -= 1

        item = list[idx]

        del list[idx]
        self.save_config()

        return f'Item `{item}`, #{idx + 1} deleted.'

    @command.desc('Dump all the data of a message')
    @command.alias('md')
    def cmd_mdump(self, msg: tg.Message) -> str:
        if not msg.reply_to_message:
            return '__Reply to a message to get its data.__'

        j = str(msg.reply_to_message)
        dat = json.loads(j)

        def _filter(obj):
            if '_' in obj:
                del obj['_']
            if 'phone_number' in obj:
                del obj['phone_number']

            for item in obj.values():
                if isinstance(item, dict):
                    _filter(item)

        _filter(dat)

        t = yaml.dump(dat, default_flow_style=False)

        return f'```{t}```\u200b'

    @command.desc('Kang a sticker into configured/provided pack')
    def cmd_kang(self, msg: tg.Message, pack_name: str) -> str:
        if not msg.reply_to_message or not msg.reply_to_message.sticker:
            return '__Reply to a sticker message to kang it.__'
        if 'sticker_pack' not in self.config['user'] and not pack_name:
            return '__Specify a sticker pack name.__'
        if pack_name:
            self.config['user']['sticker_pack'] = pack_name
            self.save_config()
        else:
            pack_name = self.config['user']['sticker_pack']

        self.mresult(msg, 'Kanging...')

        st: tg.Sticker = msg.reply_to_message.sticker
        st_bot: str = 'Stickers'

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.client.download_media(msg.reply_to_message, file_name=tmpdir + '/')
            if not path:
                return '__Error downloading sticker__'

            im = Image.open(path).convert('RGB')
            im.save(path + '.png', 'png')

            self.client.send_message(st_bot, '/addsticker')
            time.sleep(0.15)
            self.client.send_message(st_bot, pack_name)
            time.sleep(0.15)
            self.client.send_document(st_bot, path + '.png')
            time.sleep(0.25)

            if st.emoji:
                self.client.send_message(st_bot, st.emoji)
            else:
                self.client.send_message(st_bot, '❓')
            time.sleep(0.6)

            self.client.send_message(st_bot, '/done')
            return f"[Kanged](https://t.me/addstickers/{pack_name})."

    @command.desc('Save a sticker with a name as reference')
    def cmd_save(self, msg: tg.Message, name: str) -> str:
        if not msg.reply_to_message or not msg.reply_to_message.sticker:
            return '__Reply to a sticker message to save it.__'
        if not name:
            return '__Provide a name to save the sticker as.__'
        if name in self.config['stickers']:
            return '__There\'s already a sticker with that name.__'

        self.config['stickers'][name] = msg.reply_to_message.sticker.file_id
        self.save_config()

        return f'Sticker saved as `{name}`.'

    @command.desc('Save a sticker with a name to disk')
    def cmd_saved(self, msg: tg.Message, name: str) -> str:
        if not msg.reply_to_message or not msg.reply_to_message.sticker:
            return '__Reply to a sticker message to save it.__'
        if not name:
            return '__Provide a name to save the sticker as.__'
        if name in self.config['stickers']:
            return '__There\'s already a sticker with that name.__'

        path = self.client.download_media(msg.reply_to_message, file_name=f'stickers/{name}01.webp')
        if not path:
            return '__Error downloading sticker__'

        self.config['stickers'][name] = path
        self.save_config()

        return f'Sticker saved to disk as `{name}`.'

    @command.desc('List saved stickers')
    def cmd_stickers(self, msg: tg.Message) -> str:
        if not self.config['stickers']:
            return '__No stickers saved.__'

        out = 'Stickers saved:'

        for item in self.config['stickers']:
            s_type = 'local' if self.config['stickers'][item].endswith('.webp') else 'reference'
            out += f'\n    \u2022 **{item}** ({s_type})'

        return out

    @command.desc('List locally saved stickers')
    def cmd_stickersp(self, msg: tg.Message) -> str:
        if not self.config['stickers']:
            return '__No stickers saved.__'

        out = 'Stickers saved:'

        for item in self.config['stickers']:
            if self.config['stickers'][item].endswith('.webp'):
                out += f'\n    \u2022 **{item}**'

        return out

    @command.desc('Delete a saved sticker')
    def cmd_sdel(self, msg: tg.Message, name: str) -> str:
        if not name: return '__Provide the name of a sticker to delete.__'

        s_type = 'local' if self.config['stickers'][name].endswith('.webp') else 'reference'

        del self.config['stickers'][name]
        self.save_config()

        return f'{s_type.title()} sticker `{name}` deleted.'

    @command.desc('Get a sticker by name')
    def cmd_s(self, msg: tg.Message, name: str):
        if not name:
            self.mresult(msg, '__Provide the name of a sticker.__')
            return
        if name not in self.config['stickers']:
            self.mresult(msg, '__That sticker doesn\'t exist.__')
            return

        chat_id: int = msg.chat.id
        reply_id = msg.reply_to_message.message_id if msg.reply_to_message else None
        self.mresult(msg, 'Uploading sticker...')
        self.client.send_sticker(chat_id, self.config['stickers'][name], reply_to_message_id=reply_id)
        self.client.delete_messages(msg.chat.id, msg.message_id, revoke=True)

    @command.desc('Get a sticker by name and send it as a photo')
    def cmd_sp(self, msg: tg.Message, name: str):
        if not name:
            self.mresult(msg, '__Provide the name of a sticker.__')
            return
        if name not in self.config['stickers']:
            self.mresult(msg, '__That sticker doesn\'t exist.__')
            return

        if not self.config['stickers'][name].endswith('.webp'):
            self.mresult(msg, '__That sticker can not be sent as a photo.__')
            return

        chat_id: int = msg.chat.id
        reply_id = msg.reply_to_message.message_id if msg.reply_to_message else None

        path = self.config['stickers'][name]
        if not os.path.isfile(path + '.png'):
            im = Image.open(path).convert('RGB')
            im.save(path + '.png', 'png')

        self.mresult(msg, 'Uploading sticker...')
        self.client.send_photo(chat_id, path + '.png', reply_to_message_id=reply_id)
        self.client.delete_messages(msg.chat.id, msg.message_id, revoke=True)

    @command.desc('Sticker an image')
    def cmd_sticker(self, msg: tg.Message, pack: str):
        if not msg.reply_to_message and not msg.reply_to_message.photo and not msg.reply_to_message.document:
            self.mresult(msg, '__Reply to a message with an image to sticker it.__')
            return
        if not pack:
            self.mresult(msg, '__Provide the name of the pack to add the sticker to.__')
            return

        ps = pack.split()
        emoji = ps[1] if len(ps) > 1 else '❓'

        self.mresult(msg, 'Stickering...')

        st: tg.Sticker = msg.reply_to_message.sticker
        st_bot: str = 'Stickers'

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.client.download_media(msg.reply_to_message, file_name=tmpdir + '/')
            if not path:
                return '__Error downloading image__'

            im = Image.open(path).convert('RGB')

            sz = im.size
            target = 512
            if sz[0] > sz[1]:
                w_ratio = target / float(sz[0])
                h_size = int(float(sz[1]) * float(w_ratio))
                im = im.resize((target, h_size), Image.LANCZOS)
            else:
                h_ratio = target / float(sz[1])
                w_size = int(float(sz[0]) * float(h_ratio))
                im = im.resize((w_size, target), Image.LANCZOS)

            im.save(path + '.png', 'png')

            self.client.send_message(st_bot, '/addsticker')
            time.sleep(0.15)
            self.client.send_message(st_bot, ps[0])
            time.sleep(0.15)
            self.client.send_document(st_bot, path + '.png')
            time.sleep(0.15)

            self.client.send_message(st_bot, emoji)
            time.sleep(0.6)

            self.client.send_message(st_bot, '/done')
            self.mresult(msg, f'[Stickered]({ps[0]}).')

            im.save(path + '.webp', 'webp')
            self.client.send_sticker(msg.chat.id, path + '.webp')

    @command.desc('Sticker an image and save it to disk')
    def cmd_qstick(self, msg: tg.Message, name: str):
        if not msg.reply_to_message and not msg.reply_to_message.photo and not msg.reply_to_message.document:
            self.mresult(msg, '__Reply to a message with an image to sticker it.__')
            return
        if not name:
            return '__Provide a name to save the sticker as.__'
        if name in self.config['stickers']:
            return '__There\'s already a sticker with that name.__'

        self.mresult(msg, 'Stickering...')

        st: tg.Sticker = msg.reply_to_message.sticker
        st_bot: str = 'Stickers'

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.client.download_media(msg.reply_to_message, file_name=tmpdir + '/')
            if not path:
                return '__Error downloading image__'

            im = Image.open(path).convert('RGB')

            sz = im.size
            target = 512
            if sz[0] > sz[1]:
                w_ratio = target / float(sz[0])
                h_size = int(float(sz[1]) * float(w_ratio))
                im = im.resize((target, h_size), Image.LANCZOS)
            else:
                h_ratio = target / float(sz[1])
                w_size = int(float(sz[0]) * float(h_ratio))
                im = im.resize((w_size, target), Image.LANCZOS)

            im.save(f'stickers/{name}01.webp', 'webp')

            self.config['stickers'][name] = f'stickers/{name}01.webp'
            self.save_config()

            return f'Sticker saved to disk as `{name}`.'

    @command.desc('Glitch an image')
    def cmd_glitch(self, msg: tg.Message, boffset_str: str):
        if not msg.reply_to_message and not msg.reply_to_message.photo and not msg.reply_to_message.document:
            self.mresult(msg, '__Reply to a message with an image to glitch it.__')
            return

        boffset = 8
        if boffset_str:
            try:
                boffset = int(boffset_str)
            except ValueError:
                return '__Invalid distorted block offset strength.__'

        self.mresult(msg, 'Glitching...')

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.client.download_media(msg.reply_to_message, file_name=tmpdir + '/')
            if not path:
                return '__Error downloading sticker image__'

            im = Image.open(path).convert('RGB')
            im.save(path + '.png', 'png')

            subprocess.run(['corrupter', '-boffset', str(boffset), path + '.png', path + '_glitch.png'])

            chat_id: int = msg.chat.id
            reply_id = msg.reply_to_message.message_id if msg.reply_to_message else None
            self.mresult(msg, 'Uploading glitched image...')
            self.client.send_photo(chat_id, path + '_glitch.png', reply_to_message_id=reply_id)
            self.client.delete_messages(msg.chat.id, msg.message_id, revoke=True)

    @command.desc('Save the config')
    @command.alias('sc')
    def cmd_save_config(self, msg: tg.Message) -> str:
        self.save_config()
        return 'Config saved to disk.'

    @command.desc('Mass forward one message.')
    @command.alias('massfwd', 'fwd')
    def cmd_forward(self, msg: tg.Message, _count: str) -> str:
        if not _count:
            return '__Provide the amount of times to forward the message.__'
        if not msg.reply_to_message:
            return '__Reply to the message to forward.__'

        try:
            count = int(_count)
        except ValueError:
            return '__Specify a valid number of times to forward the message.__'

        for i in range(0, count):
            self.client.forward_messages(msg.chat.id, msg.chat.id, msg.reply_to_message.message_id)
            time.sleep(0.15)
