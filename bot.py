'''Main bot class'''

from typing import Callable, Dict, Union, List
import pyrogram as tg
import command
import inspect
import traceback
import util
import re
import requests
import tempfile


class Bot():
    def __init__(self) -> None:
        self.commands: Dict[str, Callable[[tg.Message], Union[None, str]]] = {}

    def setup(self, instance_name: str, prefix: str, id: int, hash: str) -> None:
        self.client: tg.Client = tg.Client(instance_name, api_id=id, api_hash=hash)

        self.prefix: str = prefix

        # Collect commands
        for sym in dir(self):
            if sym.startswith('cmd_'):
                cmd_name: str = sym[4:]
                self.commands[cmd_name] = getattr(self, sym)

    def start(self) -> None:
        self.client.start()

        # Get info
        self.user: tg.User = self.client.get_me()
        self.uid: int = self.user.id

        # Register handlers with new info
        self.client.add_handler(tg.MessageHandler(self.on_message, tg.Filters.user(self.uid) & tg.Filters.command(list(self.commands.keys()), prefix=self.prefix)))

    def mresult(self, msg: tg.Message, new: str) -> None:
        self.client.edit_message_text(msg.chat.id, msg.message_id, new, parse_mode='MARKDOWN')

    def on_message(self, cl: tg.Client, msg: tg.Message) -> None:
        cmd_func: Callable[[tg.Message], Union[None, str]] = self.commands[msg.command[0]]
        cmd_spec: inspect.FullArgSpec = inspect.getfullargspec(cmd_func)
        cmd_args: List[str] = cmd_spec.args

        args: List[str] = []
        if len(cmd_args) == 3:
            args = [msg.text[len(self.prefix) + len(msg.command[0]) + 1:]]
        elif cmd_spec.varargs is not None and len(cmd_spec.varargs) > 0:
            args = msg.command[1:]

        try:
            ret: Union[None, str] = cmd_func(msg, *args)
        except Exception as e:
            stack = ''.join(traceback.format_tb(e.__traceback__))
            ret = f'{stack}{type(e).__name__}: {e}'
            print(ret)
            ret = f'```{ret}```'

        if ret is not None:
            self.mresult(msg, ret)

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
            out += f'\n    \u2022 **{name}**: {cmd.description}'

        return out

    @command.desc(r'¯\_(ツ)_/¯')
    def cmd_shrug(self, msg: tg.Message, raw_args: str) -> str:
        if len(msg.text) > 0:
            return msg.text[len(self.prefix) + 6:] + r' ¯\_(ツ)_/¯'
        else:
            return r'¯\_(ツ)_/¯'

    @command.desc('z e r o')
    def cmd_zwsp(self, msg: tg.Message) -> str:
        return '>\u200b'

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
            return '__Command name required to get source code__'
        
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
            link = resp['link']

            # Avoid fetching as this is ephemeral with Markdown []() format
            return f'[{link}]({link})'
