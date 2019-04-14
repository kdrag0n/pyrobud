import pyrogram as tg
import traceback
import threading
import tempfile
import modules
import command
import inspect
import module
import shutil
import time
import toml
import sys
import os

class Listener():
    def __init__(self, func, module):
        self.func = func
        self.module = module

class Bot():
    def __init__(self):
        self.commands = {}
        self.modules = []
        self.listeners = {
            'message': [],
            'command': []
        }

    def load_commands(self, mod):
        for sym in dir(mod):
            if sym.startswith('cmd_'):
                cmd_name = sym[4:]
                cmd_func = getattr(mod, sym)
                if not callable(cmd_func):
                    continue
                cmd_info = command.Info(cmd_name, mod, cmd_func)

                if cmd_name in self.commands:
                    orig = self.commands[cmd_name]
                    print(f"WARNING: overwriting command '{orig.name}' ({orig.desc}) with '{cmd_name}' ({cmd_info.desc})")

                self.commands[cmd_name] = cmd_info

                for alias in getattr(cmd_func, 'aliases', []):
                    self.commands[alias] = cmd_info

    def load_module(self, cls):
        print(f"Loading module '{cls.name}' ({cls.__name__}) from '{inspect.getfile(cls)}'...")

        mod = cls(self)
        if hasattr(mod, 'on_load'):
            mod.on_load()
        if hasattr(mod, 'on_message'):
            listener = Listener(mod.on_message, mod)
            self.listeners['message'].append(listener)
        if hasattr(mod, 'on_command'):
            listener = Listener(mod.on_command, mod)
            self.listeners['command'].append(listener)

        self.load_commands(mod)
        self.modules.append(mod)

    def setup(self, instance_name, config):
        tg.session.Session.notice_displayed = True
        self.client = tg.Client(instance_name, api_id=config['telegram']['api_id'], api_hash=config['telegram']['api_hash'])

        self.prefix = config['bot']['prefix']
        self.config = config

        # Load modules
        print('Loading modules...')
        for _sym in dir(modules):
            module_mod = getattr(modules, _sym)

            if inspect.ismodule(module_mod):
                for sym in dir(module_mod):
                    cls = getattr(module_mod, sym)
                    if inspect.isclass(cls) and issubclass(cls, module.Module):
                        self.load_module(cls)

        self.last_saved_cfg = toml.dumps(self.config)

    def save_config(self, cfg = ''):
        tmp_path = ''

        if not cfg:
            cfg = toml.dumps(self.config)

        try:
            with tempfile.NamedTemporaryFile('wb', delete=False) as f:
                tmp_path = f.name

                f.write(cfg.encode('utf-8'))
                f.flush()
                os.fsync(f.fileno())
                self.last_saved_cfg = cfg

            shutil.move(tmp_path, 'config.toml')
        except Exception as e:
            os.remove(tmp_path)
            raise e

    def writer(self):
        while True:
            time.sleep(15)
            cfg = toml.dumps(self.config)
            if cfg != self.last_saved_cfg:
                self.save_config(cfg)

    def start(self):
        self.client.start()

        # Get info
        self.user = self.client.get_me()
        self.uid = self.user.id

        # Register handlers with new info
        self.client.add_handler(tg.MessageHandler(self.on_command, tg.Filters.user(self.uid) & tg.Filters.command(list(self.commands.keys()), prefix=self.prefix)))
        self.client.add_handler(tg.MessageHandler(self.on_message))

        # Save config in the background
        self.writer_thread = threading.Thread(target=self.writer)
        self.writer_thread.daemon = True
        self.writer_thread.start()

        print('Bot is ready')

    def mresult(self, msg, new):
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

    def call_listeners(self, event, *args):
        for l in self.listeners[event]:
            l.func(*args)

    def on_message(self, cl, msg):
        self.call_listeners('message', msg)

    def on_command(self, cl, msg):
        cmd_info = self.commands[msg.command[0]]
        cmd_func = cmd_info.func
        cmd_spec = inspect.getfullargspec(cmd_func)
        cmd_args = cmd_spec.args

        args = []
        if len(cmd_args) == 3:
            txt = msg.text.markdown
            if cmd_args[2].startswith('plain_'):
                txt = msg.text

            args = [txt[len(self.prefix) + len(msg.command[0]) + 1:]]
        elif cmd_spec.varargs is not None and len(cmd_spec.varargs) > 0:
            args = msg.command[1:]

        try:
            ret = cmd_func(msg, *args)
        except Exception as e:
            stack = ''.join(traceback.format_tb(e.__traceback__))
            ret = f'{stack}{type(e).__name__}: {e}'
            print(ret, file=sys.stderr)
            ret = f'```{ret}```'

        if ret is not None:
            self.mresult(msg, ret)

        self.call_listeners('command', msg, cmd_info, args)
