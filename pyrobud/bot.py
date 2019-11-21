import asyncio
import bisect
import importlib
import inspect
import logging
import os
import sys
import traceback

import aiohttp
import telethon as tg
import toml
import plyvel
import sentry_sdk

from . import command, module, modules, custom_modules, util


class Listener:
    def __init__(self, event, func, module, priority):
        self.event = event
        self.func = func
        self.module = module
        self.priority = priority

    def __lt__(self, other):
        return self.priority < other.priority


class Bot:
    def __init__(self, config):
        # Initialize module dicts
        self.commands = {}
        self.modules = {}
        self.listeners = {}

        # Save reference to config
        self.config = config

        # Initialize other objects
        self.log = logging.getLogger("bot")
        self.http_session = aiohttp.ClientSession()

        # Initialize database
        self._db = util.db.AsyncDB(plyvel.DB(config["bot"]["db_path"], create_if_missing=True))
        self.db = self.get_db("bot")

        # Initialize Telegram client
        tg_config = config["telegram"]
        self.client = tg.TelegramClient(tg_config["session_name"], tg_config["api_id"], tg_config["api_hash"])

    def get_db(self, prefix):
        return self._db.prefixed_db(prefix + ".")

    def register_command(self, mod, name, func):
        info = command.Info(name, mod, func)

        if name in self.commands:
            orig = self.commands[name]
            raise module.ExistingCommandError(orig, info)

        self.commands[name] = info

        for alias in info.aliases:
            if alias in self.commands:
                orig = self.commands[alias]
                raise module.ExistingCommandError(orig, info, alias=True)

            self.commands[alias] = info

    def unregister_command(self, cmd):
        del self.commands[cmd.name]

        for alias in cmd.aliases:
            try:
                del self.commands[alias]
            except KeyError:
                continue

    def register_commands(self, mod):
        for name, func in util.find_prefixed_funcs(mod, "cmd_"):
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

    def register_listener(self, mod, event, func, priority=100):
        listener = Listener(event, func, mod, priority)

        if event in self.listeners:
            bisect.insort(self.listeners[event], listener)
        else:
            self.listeners[event] = [listener]

    def unregister_listener(self, listener):
        self.listeners[listener.event].remove(listener)

    def register_listeners(self, mod):
        for event, func in util.find_prefixed_funcs(mod, "on_"):
            try:
                self.register_listener(mod, event, func, priority=getattr(func, "listener_priority", 100))
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

    def load_module(self, cls, *, comment=None):
        _comment = comment + " " if comment else ""
        self.log.info(
            f"Loading {_comment}module '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"
        )

        if cls.name in self.modules:
            old = self.modules[cls.name].__class__
            raise module.ExistingModuleError(old, cls)

        mod = cls(self)
        mod.comment = comment
        self.register_listeners(mod)
        self.register_commands(mod)
        self.modules[cls.name] = mod

    def unload_module(self, mod):
        _comment = mod.comment + " " if mod.comment else ""

        cls = mod.__class__
        self.log.info(
            f"Unloading {_comment}module '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"
        )

        self.unregister_listeners(mod)
        self.unregister_commands(mod)
        del self.modules[cls.name]

    def _load_modules_from_metamod(self, metamod, *, comment=None):
        for _sym in metamod.__all__:
            module_mod = getattr(metamod, _sym)

            if inspect.ismodule(module_mod):
                for sym in dir(module_mod):
                    cls = getattr(module_mod, sym)
                    if inspect.isclass(cls) and issubclass(cls, module.Module):
                        self.load_module(cls, comment=comment)

    def load_all_modules(self):
        self.log.info("Loading modules")
        self._load_modules_from_metamod(modules)
        self._load_modules_from_metamod(custom_modules, comment="custom")
        self.log.info("All modules loaded.")

    def unload_all_modules(self):
        self.log.info("Unloading modules...")

        # Can't modify while iterating, so collect a list first
        for mod in list(self.modules.values()):
            self.unload_module(mod)

        self.log.info("All modules unloaded.")

    async def reload_module_pkg(self):
        self.log.info("Reloading base module class...")
        await util.run_sync(lambda: importlib.reload(module))

        self.log.info("Reloading master module...")
        await util.run_sync(lambda: importlib.reload(modules))

        self.log.info("Reloading custom master module...")
        await util.run_sync(lambda: importlib.reload(custom_modules))

    def command_predicate(self, event):
        if event.raw_text.startswith(self.prefix):
            parts = event.raw_text.split()
            parts[0] = parts[0][len(self.prefix) :]

            event.segments = parts
            return True

        return False

    async def start(self):
        # Get and store current event loop, since this is the first coroutine
        self.loop = asyncio.get_event_loop()

        # Load prefix
        self.prefix = await self.db.get("prefix", self.config["bot"]["default_prefix"])

        # Load modules
        self.load_all_modules()
        await self.dispatch_event("load")

        # Start Telegram client
        await self.client.start()

        # Get info
        self.user = await self.client.get_me()
        self.uid = self.user.id

        # Set Sentry username if enabled
        if self.config["bot"]["report_username"]:
            with sentry_sdk.configure_scope() as scope:
                scope.user = {"username": self.user.username}

        # Hijack Message class to provide result function
        async def result(msg, new_text, **kwargs):
            tg_config = self.config["telegram"]
            api_id = str(tg_config["api_id"])
            api_hash = tg_config["api_hash"]

            # Redact sensitive information
            if api_id in new_text:
                new_text = new_text.replace(api_id, "[REDACTED]")
            if api_hash in new_text:
                new_text = new_text.replace(api_hash, "[REDACTED]")
            if self.user.phone in new_text:
                new_text = new_text.replace(self.user.phone, "[REDACTED]")

            # Default to disabling link previews in responses
            if "link_preview" not in kwargs:
                kwargs["link_preview"] = False

            # Truncate messages longer than Telegram's 4096-character length limit
            truncated_suffix = "... (truncated)"
            if len(new_text) > 4096:
                new_text = new_text[: 4096 - len(truncated_suffix)] + truncated_suffix

            await msg.edit(text=new_text, **kwargs)

        tg.types.Message.result = result

        # Record start time and dispatch start event
        self.start_time_us = util.time.usec()
        await self.dispatch_event("start", self.start_time_us)

        # Register handlers
        self.client.add_event_handler(self.on_message, tg.events.NewMessage)
        self.client.add_event_handler(self.on_message_edit, tg.events.MessageEdited)
        self.client.add_event_handler(self.on_command, tg.events.NewMessage(outgoing=True, func=self.command_predicate))
        self.client.add_event_handler(self.on_chat_action, tg.events.ChatAction)

        self.log.info("Bot is ready")

        # Catch up on missed events
        self.log.info("Catching up on missed events")
        await self.client.catch_up()
        self.log.info("Finished catching up")

    async def stop(self):
        await self.dispatch_event("stop")
        await self.http_session.close()
        await self._db.close()

        self.log.info("Running post-stop hooks")
        await self.dispatch_event("stopped")

    async def dispatch_event(self, event, *args):
        tasks = set()

        try:
            listeners = self.listeners[event]
        except KeyError:
            return None

        if not listeners:
            return

        for l in listeners:
            task = self.loop.create_task(l.func(*args))
            tasks.add(task)

        self.log.debug(f"Dispatching event '{event}' with data {args}")
        return await asyncio.wait(tasks)

    def dispatch_event_nowait(self, *args, **kwargs):
        return self.loop.create_task(self.dispatch_event(*args, **kwargs))

    async def on_message(self, event):
        await self.dispatch_event("message", event)

    async def on_message_edit(self, event):
        await self.dispatch_event("message_edit", event)

    async def on_chat_action(self, event):
        await self.dispatch_event("chat_action", event)

    async def on_command(self, event):
        try:
            try:
                cmd_info = self.commands[event.segments[0]]
            except KeyError:
                return

            cmd_func = cmd_info.func
            cmd_spec = inspect.getfullargspec(cmd_func)
            cmd_args = cmd_spec.args

            args = []
            if len(cmd_args) == 3:
                txt = event.text

                # Contrary to typical terms, text = raw text (i.e. with Markdown formatting)
                # and raw_text = parsed text (i.e. plain text without formatting symbols)
                if cmd_args[2].startswith("parsed_"):
                    txt = event.raw_text

                args = [txt[len(self.prefix) + len(event.segments[0]) + 1 :]]
            elif cmd_spec.varargs and not cmd_spec.kwonlyargs:
                args = event.segments[1:]

            try:
                ret = await cmd_func(event, *args)
            except Exception as e:
                cmd_info.module.log.log(cmd_info.error_level, "Error in command function", exc_info=e)
                ret = f"⚠️ Error executing command:\n```{util.format_exception(e)}```"

            if ret is not None:
                try:
                    await event.result(ret)
                except Exception as e:
                    cmd_info.module.log.log(
                        cmd_info.error_level,
                        "Error updating message with data returned by command '%s'",
                        cmd_info.name,
                        exc_info=e,
                    )
                    ret = f"⚠️ Error updating message:\n```{util.format_exception(e)}```"

                    await event.result(ret)

            await self.dispatch_event("command", event, cmd_info, args)
        except Exception as e:
            try:
                await event.result(f"⚠️ Error in command handler:\n```{util.format_exception(e)}```")
            except Exception:
                raise

            raise
