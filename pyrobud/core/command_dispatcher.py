from typing import TYPE_CHECKING, Any, MutableMapping

import telethon as tg

from .. import command, module, util
from .bot_mixin_base import MixinBase

if TYPE_CHECKING:
    from .bot import Bot


class CommandDispatcher(MixinBase):
    # Initialized during instantiation
    commands: MutableMapping[str, command.Command]

    def __init__(self: "Bot", **kwargs: Any) -> None:
        # Initialize command map
        self.commands = {}

        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    def register_command(
        self: "Bot", mod: module.Module, name: str, func: command.CommandFunc
    ) -> None:
        cmd = command.Command(name, mod, func)

        if name in self.commands:
            orig = self.commands[name]
            raise module.ExistingCommandError(orig, cmd)

        self.commands[name] = cmd

        for alias in cmd.aliases:
            if alias in self.commands:
                orig = self.commands[alias]
                raise module.ExistingCommandError(orig, cmd, alias=True)

            self.commands[alias] = cmd

    def unregister_command(self: "Bot", cmd: command.Command) -> None:
        del self.commands[cmd.name]

        for alias in cmd.aliases:
            try:
                del self.commands[alias]
            except KeyError:
                continue

    def register_commands(self: "Bot", mod: module.Module) -> None:
        for name, func in util.misc.find_prefixed_funcs(mod, "cmd_"):
            done = False

            try:
                self.register_command(mod, name, func)
                done = True
            finally:
                if not done:
                    self.unregister_commands(mod)

    def unregister_commands(self: "Bot", mod: module.Module) -> None:
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

    def command_predicate(self: "Bot", event: tg.events.NewMessage.Event) -> bool:
        if event.raw_text.startswith(self.prefix):
            parts = event.raw_text.split()
            parts[0] = parts[0][len(self.prefix) :]

            event.segments = parts
            return True

        return False

    async def on_command(self: "Bot", msg: tg.events.NewMessage.Event) -> None:
        cmd = None

        # Don't process commands from inline bots
        if msg.via_bot_id:
            return

        try:
            # Attempt to get command info
            try:
                cmd = self.commands[msg.segments[0]]
            except KeyError:
                return

            # Construct invocation context
            ctx = command.Context(
                self,
                msg,
                msg.message,
                msg.segments,
                len(self.prefix) + len(msg.segments[0]) + 1,
            )

            # Ensure specified argument needs are met
            if cmd.usage is not None and not ctx.input:
                err_base = f"⚠️ Missing parameters: {cmd.usage}"

                if cmd.usage_reply:
                    if msg.is_reply:
                        reply_msg = await msg.get_reply_message()
                        if reply_msg.text:
                            ctx.input = reply_msg.text
                            ctx.plain_input = reply_msg.raw_text
                        elif not cmd.usage_optional:
                            await ctx.respond(
                                f"{err_base}\n__The message you replied to doesn't contain text.__"
                            )
                            return
                    elif not cmd.usage_optional:
                        await ctx.respond(f"{err_base} (replying is also supported)")
                        return
                elif not cmd.usage_optional:
                    await ctx.respond(err_base)
                    return

            # Invoke command function
            try:
                ret = await cmd.func(ctx)

                # Response shortcut
                if ret is not None:
                    await ctx.respond(ret)
            except tg.errors.MessageNotModifiedError:
                cmd.module.log.warning(
                    f"Command '{cmd.name}' triggered a message edit with no changes; make sure there is only a single bot instance running"
                )
            except Exception as e:
                cmd.module.log.error(f"Error in command '{cmd.name}'", exc_info=e)
                await ctx.respond(
                    f"⚠️ Error executing command:\n```{util.error.format_exception(e)}```"
                )

            await self.dispatch_event("command", cmd, msg)
        except Exception as e:
            if cmd is not None:
                cmd.module.log.error("Error in command handler", exc_info=e)

            await self.respond(
                msg.message,
                f"⚠️ Error in command handler:\n```{util.error.format_exception(e)}```",
            )
