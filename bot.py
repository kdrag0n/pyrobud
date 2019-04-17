import pyrogram as tg
import threading
import traceback
import importlib
import tempfile
import modules
import command
import inspect
import module
import shutil
import time
import toml
import util
import sys
import os

class Listener():
    def __init__(self, event, func, module):
        self.event = event
        self.func = func
        self.module = module

class Bot():
    def __init__(self):
        self.commands = {}
        self.modules = {}
        self.listeners = {
            'message': [],
            'command': [],
            'load': [],
            'start': []
        }

    def register_command(self, mod, name, func):
        info = command.Info(name, mod, func)

        if name in self.commands:
            orig = self.commands[name]
            raise module.ExistingCommandError(orig, info)

        self.commands[name] = info

        for alias in getattr(func, 'aliases', []):
            if alias in self.commands:
                orig = self.commands[alias]
                raise module.ExistingCommandError(orig, info, alias=True)

            self.commands[alias] = info

    def unregister_command(self, cmd):
        del self.commands[cmd.name]

        for alias in cmd.aliases:
            del self.commands[alias]

    def register_commands(self, mod):
        for name, func in util.find_prefixed_funcs(mod, 'cmd_'):
            try:
                self.register_command(mod, name, func)
            except:
                self.unregister_commands(mod)
                raise

    def unregister_commands(self, mod):
        # Can't unregister while iterating, so collect commands to unregister afterwards
        to_unreg = []

        for name, cmd in self.commands.items():
            # Let unregister_command deal with aliases
            if name != cmd.name:
                continue

            if cmd.module == mod:
                to_unreg.append(cmd)

        # Actually unregister the commands
        for cmd in to_unreg:
            self.unregister_command(cmd)

    def register_listener(self, mod, event, func):
        listener = Listener(event, func, mod)

        if event in self.listeners:
            self.listeners[event].append(listener)
        else:
            raise module.UnknownEventError(event, listener)

    def unregister_listener(self, listener):
        self.listeners[listener.event].remove(listener)

    def register_listeners(self, mod):
        for event, func in util.find_prefixed_funcs(mod, 'on_'):
            try:
                self.register_listener(mod, event, func)
            except:
                self.unregister_listeners(mod)
                raise

    def unregister_listeners(self, mod):
        # Can't unregister while iterating, so collect listeners to unregister afterwards
        to_unreg = []

        for lst in self.listeners.values():
            for listener in lst:
                if listener.module == mod:
                    to_unreg.append(listener)

        # Actually unregister the listeners
        for listener in to_unreg:
            self.unregister_listener(listener)

    def load_module(self, cls):
        print(f"Loading module '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'...")

        if cls.name in self.modules:
            old = self.modules[cls.name].__class__
            raise module.ExistingModuleError(old, cls)

        mod = cls(self)
        self.register_listeners(mod)
        self.register_commands(mod)
        self.modules[cls.name] = mod

    def unload_module(self, mod):
        cls = mod.__class__
        print(f"Unloading module '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'...")

        self.unregister_listeners(mod)
        self.unregister_commands(mod)
        del self.modules[cls.name]

    def load_all_modules(self):
        print('Loading modules...')

        for _sym in dir(modules):
            module_mod = getattr(modules, _sym)

            if inspect.ismodule(module_mod):
                for sym in dir(module_mod):
                    cls = getattr(module_mod, sym)
                    if inspect.isclass(cls) and issubclass(cls, module.Module):
                        self.load_module(cls)

    def unload_all_modules(self):
        print('Unloading modules...')

        # Can't unload while iterating, so collect a list
        for mod in list(self.modules.values()):
            self.unload_module(mod)

    def reload_module_pkg(self):
        print('Reloading base module class...')
        importlib.reload(module)

        print('Reloading master module...')
        importlib.reload(modules)

    def setup(self, instance_name, config):
        tg.session.Session.notice_displayed = True
        self.client = tg.Client(instance_name, api_id=config['telegram']['api_id'], api_hash=config['telegram']['api_hash'])

        self.prefix = config['bot']['prefix']
        self.config = config

        # Load modules
        self.load_all_modules()
        self.dispatch_event('load')

        self.last_saved_cfg = toml.dumps(self.config)

    def save_config(self, cfg = ''):
        tmp_path = ''

        if not cfg:
            cfg = toml.dumps(self.config)

        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                tmp_path = f.name

                f.write(cfg.encode('utf-8'))
                f.flush()
                os.fsync(f.fileno())

            shutil.move(tmp_path, 'config.toml')
        except:
            os.remove(tmp_path)
            raise

        self.last_saved_cfg = cfg

    def writer(self):
        while True:
            time.sleep(15)
            cfg = toml.dumps(self.config)
            if cfg != self.last_saved_cfg:
                self.save_config(cfg)

    def register_command_handler(self):
        self.cmd_handler = self.client.add_handler(tg.MessageHandler(self.on_command, tg.Filters.user(self.uid) & tg.Filters.command(list(self.commands.keys()), prefix=self.prefix)), group=0)

    def start(self):
        self.client.start()

        # Get info
        self.user = self.client.get_me()
        self.uid = self.user.id

        # Record start time and dispatch start event
        self.start_time_us = util.time_us()
        self.dispatch_event('start', self.start_time_us)

        # Register handlers with new info
        self.client.add_handler(tg.MessageHandler(self.on_message), group=1)
        self.register_command_handler()

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

    def dispatch_event(self, event, *args):
        for l in self.listeners[event]:
            l.func(*args)

    def on_message(self, cl, msg):
        self.dispatch_event('message', msg)

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
            traceback.print_exc(file=sys.stderr)
            ret = f'⚠️ Error executing command:\n```{util.format_exception(e)}```'

        if ret is not None:
            try:
                self.mresult(msg, ret)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                ret = f'⚠️ Error updating message:\n```{util.format_exception(e)}```'

                self.mresult(msg, ret)

        self.dispatch_event('command', msg, cmd_info, args)
