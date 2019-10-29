import asyncio
import importlib
import inspect
import logging
import os
import sys
import traceback

import aiofiles
import aiohttp
import telethon as tg
from telethon.tl.types import PeerUser, PeerChat, PeerChannel
import toml

import command
import module
import modules
import util

from datetime import datetime, timedelta

from pprint import pprint


class Listener:
    def __init__(self, event, func, module):
        self.event = event
        self.func = func
        self.module = module


class Bot:
    def __init__(self, config, config_path):
        self.commands = {}
        self.modules = {}
        self.listeners = {}

        self.log = logging.getLogger("bot")
        self.client = tg.TelegramClient("anon", config["telegram"]["api_id"], config["telegram"]["api_hash"])
        self.http_session = aiohttp.ClientSession()

        self.config = config
        self.config_path = config_path
        self.prefix = config["bot"]["prefix"]
        self.last_saved_cfg = toml.dumps(config)

    def register_command(self, mod, name, func):
        info = command.Info(name, mod, func)

        if name in self.commands:
            orig = self.commands[name]
            raise module.ExistingCommandError(orig, info)

        self.commands[name] = info

        for alias in getattr(func, "aliases", []):
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

    def register_listener(self, mod, event, func):
        listener = Listener(event, func, mod)

        if event in self.listeners:
            self.listeners[event].append(listener)
        else:
            self.listeners[event] = [listener]

    def unregister_listener(self, listener):
        self.listeners[listener.event].remove(listener)

    def register_listeners(self, mod):
        for event, func in util.find_prefixed_funcs(mod, "on_"):
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
        self.log.info(f"Loading module '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'")

        if cls.name in self.modules:
            old = self.modules[cls.name].__class__
            raise module.ExistingModuleError(old, cls)

        mod = cls(self)
        self.register_listeners(mod)
        self.register_commands(mod)
        self.modules[cls.name] = mod

    def unload_module(self, mod):
        cls = mod.__class__
        self.log.info(f"Unloading module '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'")

        self.unregister_listeners(mod)
        self.unregister_commands(mod)
        del self.modules[cls.name]

    def load_all_modules(self):
        self.log.info("Loading modules")

        for _sym in dir(modules):
            module_mod = getattr(modules, _sym)

            if inspect.ismodule(module_mod):
                for sym in dir(module_mod):
                    cls = getattr(module_mod, sym)
                    if inspect.isclass(cls) and issubclass(cls, module.Module):
                        self.load_module(cls)

    def unload_all_modules(self):
        self.log.info("Unloading modules...")

        # Can't modify while iterating, so collect a list first
        for mod in list(self.modules.values()):
            self.unload_module(mod)

    async def reload_module_pkg(self):
        self.log.info("Reloading base module class...")
        await util.run_sync(lambda: importlib.reload(module))

        self.log.info("Reloading master module...")
        await util.run_sync(lambda: importlib.reload(modules))

    async def save_config(self, data=None):
        tmp_path = self.config_path + ".tmp"

        if data is None:
            data = toml.dumps(self.config)

        try:
            async with aiofiles.open(tmp_path, "wb+") as f:
                await f.write(data.encode("utf-8"))
                await f.flush()
                await util.run_sync(lambda: os.fsync(f.fileno()))

            await util.run_sync(lambda: os.rename(tmp_path, self.config_path))
        except:
            await util.run_sync(lambda: os.remove(tmp_path))
            raise

        self.last_saved_cfg = data

    async def writer(self):
        while True:
            await asyncio.sleep(15)

            cfg = toml.dumps(self.config)
            if cfg != self.last_saved_cfg:
                await self.save_config(data=cfg)

    # Custom Shit
    async def updateChannelLeaves(self):
        gay_events = []
        channel = await self.client.get_entity(PeerChannel(1441900591))  # "https://t.me/joinchat/AAAAAFXxqC9BNDFm8uFc3A"
        logchannel = await self.client.get_entity(PeerChannel(1441900591))
        while True:
            await asyncio.sleep(3600)
            if len(gay_events) > 500: gay_events = gay_events[:500]
            async for event in self.client.iter_admin_log(channel, leave=True):
                if not event.left or event in gay_events: continue
                gay_events.append(event)
                user = await self.client.get_entity(PeerUser(event.user_id))
                timestamp = event.date.strftime("%Y-%m-%d %H:%M:%S")
                msg = f"🔙 {timestamp}\n{util.mention_user(user)} ({event.user_id})";
                await self.client.send_message(logchannel, msg, schedule=timedelta(seconds=10))

    def command_predicate(self, event):
        if event.raw_text.startswith(self.prefix):
            parts = event.raw_text.split()
            parts[0] = parts[0][len(self.prefix):]

            event.segments = parts
            return True

        return False

    async def start(self, catch_up=True):
        # Get and store current event loop, since this is the first coroutine
        self.loop = asyncio.get_event_loop()

        # Load modules and save config in case any migration changes were made
        self.load_all_modules()
        await self.dispatch_event("load")
        await self.save_config()

        # Start Telegram client
        await self.client.start()

        # Get info
        self.user = await self.client.get_me()
        self.uid = self.user.id

        # Hijack Message class to provide result function
        async def result(msg, new_text, **kwargs):
            t = self.config["telegram"]
            api_id = str(t["api_id"])
            api_hash = t["api_hash"]

            if api_id in new_text:
                new_text = new_text.replace(api_id, "[REDACTED]")
            if api_hash in new_text:
                new_text = new_text.replace(api_hash, "[REDACTED]")
            if self.user.phone in new_text:
                new_text = new_text.replace(self.user.phone, "[REDACTED]")

            if "link_preview" not in kwargs:
                kwargs["link_preview"] = False

            await msg.edit(text=new_text, **kwargs)

        tg.types.Message.result = result

        # Record start time and dispatch start event
        self.start_time = datetime.utcnow()
        self.start_time_us = util.time_us()
        await self.dispatch_event("start", self.start_time_us)

        # Register handlers
        self.client.add_event_handler(self.on_message, tg.events.NewMessage)
        self.client.add_event_handler(self.on_message_edit, tg.events.MessageEdited)
        self.client.add_event_handler(self.on_command, tg.events.NewMessage(outgoing=True, func=self.command_predicate))
        self.client.add_event_handler(self.on_chat_action, tg.events.ChatAction)
        if len(self.config["bot"]["auto_admins"]) > 0:
            self.client.add_event_handler(self.on_raw_event, tg.events.Raw)

        # Save config in the background
        self.loop.create_task(self.writer())
        self.loop.create_task(self.updateChannelLeaves())

        self.log.info("Bot is ready")
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await self.client.send_message(self.user, f"[{timestamp}] Pyrobud is ready")

        # Catch up on missed events
        if catch_up:
            self.log.info("Catching up on missed events")
            await self.client.catch_up()
            self.log.info("Finished catching up")

        # Save config to sync updated stats after catching up
        await self.save_config()
        self.log.info("Everything ready!")

    no_events = [
        "UpdateNewChannelMessage", "UpdateMessageID", "UpdateReadChannelInbox", "UpdateReadChannelOutbox",
        "UpdateEditChannelMessage", "UpdateUserStatus"
    ]

    async def on_raw_event(self, event):
        name = event.__class__.__name__
        if name == "UpdateChatParticipants":
            print(event)
            if event.participants.version == 1:
                is_creator = False
                for participant in event.participants.participants:
                    participant_type = participant.__class__.__name__
                    if participant_type == "ChatParticipantCreator":
                        if participant.user_id == self.uid: is_creator = True
                    # elif == "ChatParticipant":
                if is_creator:
                    await asyncio.sleep(2.5)
                    chat = await self.client.get_entity(event.participants.chat_id)
                    await self.client(
                        tg.tl.functions.channels.InviteToChannelRequest(chat, self.config["bot"]["auto_admins"]))
                    rights = tg.tl.types.ChatAdminRights(post_messages=True, add_admins=True, invite_users=True,
                                                         change_info=True,
                                                         ban_users=True, delete_messages=True, pin_messages=True,
                                                         invite_link=True, edit_messages=True)
                    for auto_admin in self.config["bot"]["auto_admins"]:
                        user = await self.client.get_entity(auto_admin)
                        await self.client(tg.tl.functions.channels.EditAdminRequest(chat, user, rights))
                    admincnt = len(self.config["bot"]["auto_admins"])
                    chat.send_message(f"Added {admincnt} admins.")

    async def stop(self):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await self.client.send_message(self.user, f"[{timestamp}] Selfbot is stopping")
        await self.dispatch_event("stop")
        await self.save_config()
        await self.http_session.close()

    async def dispatch_event(self, event, *args):
        tasks = set()

        try:
            listeners = self.listeners[event]
        except KeyError:
            return None

        for l in listeners:
            task = self.loop.create_task(l.func(*args))
            tasks.add(task)

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

                args = [txt[len(self.prefix) + len(event.segments[0]) + 1:]]
            elif cmd_spec.varargs is not None and len(cmd_spec.varargs) > 0 and not cmd_spec.kwonlyargs:
                args = event.segments[1:]

            try:
                ret = await cmd_func(event, *args)
            except Exception as e:
                self.log.error("Error in command function", exc_info=e)
                ret = f"⚠️ Error executing command:\n```{util.format_exception(e)}```"

            if ret is not None:
                try:
                    await event.result(ret)
                except Exception as e:
                    self.log.error(
                        "Error updating message with data returned by command '%s'", cmd_info.name, exc_info=e
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
