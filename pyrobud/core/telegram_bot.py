import asyncio
from typing import TYPE_CHECKING, Any, Mapping, Optional, Type, TypeVar, Union

import sentry_sdk
import telethon as tg

from .. import util
from .bot_mixin_base import MixinBase

if TYPE_CHECKING:
    from .bot import Bot

TelegramConfig = Mapping[str, Union[int, str]]
EventType = TypeVar("EventType", bound=tg.events.common.EventBuilder)


class TelegramBot(MixinBase):
    # Initialized during instantiation
    tg_config: TelegramConfig

    # Initialized during startup
    client: tg.TelegramClient
    loop: asyncio.AbstractEventLoop
    prefix: str
    user: tg.types.User
    uid: int
    start_time_us: int

    def __init__(self: "Bot", **kwargs: Any) -> None:
        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    async def init_client(self: "Bot") -> None:
        # Get Telegram parameters from config and check types
        self.tg_config = self.config["telegram"]

        session_name = self.tg_config["session_name"]
        if not isinstance(session_name, str):
            raise TypeError("Session name must be a string")

        api_id = self.tg_config["api_id"]
        if not isinstance(api_id, int):
            raise TypeError("API ID must be an integer")

        api_hash = self.tg_config["api_hash"]
        if not isinstance(api_hash, str):
            raise TypeError("API hash must be a string")

        # Initialize Telegram client with gathered parameters
        self.client = tg.TelegramClient(session_name, api_id, api_hash)

    async def start(self: "Bot") -> None:
        self.log.info("Starting")
        await self.init_client()

        # Get and store current event loop, since this is the first coroutine that runs
        self.loop = asyncio.get_event_loop()

        # Load prefix
        self.prefix = await self.db.get("prefix", self.config["bot"]["default_prefix"])

        # Load modules
        self.load_all_modules()
        await self.dispatch_event("load")

        # Start Telegram client
        await self.client.start()

        # Get info
        user = await self.client.get_me()
        if not isinstance(user, tg.types.User):
            raise TypeError("Missing full self user information")
        self.user = user
        # noinspection PyTypeChecker
        self.uid = user.id

        # Set Sentry username if enabled
        if self.config["bot"]["report_username"]:
            with sentry_sdk.configure_scope() as scope:
                scope.set_user({"username": self.user.username})

        # Record start time and dispatch start event
        self.start_time_us = util.time.usec()
        await self.dispatch_event("start", self.start_time_us)

        # Register core handlers
        self.client.add_event_handler(
            self.on_command, tg.events.NewMessage(outgoing=True, func=self.command_predicate),
        )

        # Register module handlers
        self.add_module_event_handler("message", tg.events.NewMessage)
        self.add_module_event_handler("message_edit", tg.events.MessageEdited)
        self.add_module_event_handler("message_delete", tg.events.MessageDeleted)
        self.add_module_event_handler("message_read", tg.events.MessageRead)
        self.add_module_event_handler("chat_action", tg.events.ChatAction)
        self.add_module_event_handler("user_update", tg.events.UserUpdate)

        self.log.info("Bot is ready")

        # Catch up on missed events now that handlers have been registered
        self.log.info("Catching up on missed events")
        await self.client.catch_up()
        self.log.info("Finished catching up")

    async def run(self: "Bot") -> None:
        # Start client
        try:
            await self.start()
        except KeyboardInterrupt:
            self.log.warning("Received interrupt while connecting")

        # Request updates, then idle until disconnected and stop when done
        try:
            # noinspection PyProtectedMember
            await self.client._run_until_disconnected()
        finally:
            await self.stop()

    def add_module_event_handler(self: "Bot", name: str, event_type: Type[EventType]) -> None:
        if name not in self.listeners:
            return

        async def event_handler(event: EventType) -> None:
            await self.dispatch_event(name, event)

        self.client.add_event_handler(event_handler, event_type())

    # Flexible response function with filtering, truncation, redaction, etc.
    async def respond(
        self: "Bot",
        msg: tg.custom.Message,
        text: Optional[str] = None,
        *,
        mode: Optional[str] = None,
        redact: Optional[bool] = None,
        response: Optional[tg.custom.Message] = None,
        **kwargs: Any,
    ) -> tg.custom.Message:
        # Read redaction setting from config
        if redact is None:
            redact = self.config["bot"]["redact_responses"]

        # Filter text
        if text is not None:
            # Redact sensitive information if enabled and known
            if redact:
                tg_config: Mapping[str, str] = self.config["telegram"]
                api_id = str(tg_config["api_id"])
                api_hash = tg_config["api_hash"]

                if api_id in text:
                    text = text.replace(api_id, "[REDACTED]")
                if api_hash in text:
                    text = text.replace(api_hash, "[REDACTED]")
                if self.user.phone is not None and self.user.phone in text:
                    text = text.replace(self.user.phone, "[REDACTED]")

            # Truncate messages longer than Telegram's 4096-character length limit
            text = util.tg.truncate(text)

        # Default to disabling link previews in responses
        if "link_preview" not in kwargs:
            kwargs["link_preview"] = False

        # Use selected response mode if not overridden by invoker
        if mode is None:
            mode = self.config["bot"]["response_mode"]

        if mode == "edit":
            return await msg.edit(text=text, **kwargs)
        elif mode == "reply":
            if response is not None:
                # Already replied, so just edit the existing reply to reduce spam
                return await response.edit(text=text, **kwargs)
            else:
                # Reply since we haven't done so yet
                return await msg.reply(text, **kwargs)
        elif mode == "repost":
            if response is not None:
                # Already reposted, so just edit the existing reply to reduce spam
                return await response.edit(text=text, **kwargs)
            else:
                # Repost since we haven't done so yet
                response = await msg.respond(text, reply_to=msg.reply_to_msg_id, **kwargs)
                await msg.delete()
                return response
        else:
            raise ValueError(f"Unknown response mode '{mode}'")
