from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
    Type,
    Union,
)

import sentry_sdk
import telethon as tg

from .. import util
from .bot_mixin_base import MixinBase

if TYPE_CHECKING:
    from .bot import Bot

TelegramConfig = Mapping[str, Union[int, str]]
EventType: Any = tg.events.common.EventBuilder
TgEventHandler = Callable[[EventType], Coroutine[Any, Any, None]]


class TelegramBot(MixinBase):
    # Initialized during instantiation
    tg_config: TelegramConfig
    _mevent_handlers: MutableMapping[str, Tuple[TgEventHandler, EventType]]
    loaded: bool

    # Initialized during startup
    client: tg.TelegramClient
    prefix: str
    user: tg.types.User
    uid: int
    start_time_us: int

    def __init__(self: "Bot", **kwargs: Any) -> None:
        self.tg_config = self.config["telegram"]
        self._mevent_handlers = {}
        self.loaded = False

        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    async def init_client(self: "Bot") -> None:
        # Get Telegram parameters from config and check types
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
        self.client = tg.TelegramClient(
            session_name, api_id, api_hash, connection_retries=10, retry_delay=5
        )

    async def start(self: "Bot") -> None:
        self.log.info("Starting")
        await self.init_client()

        # Load prefix
        self.prefix = await self.db.get("prefix", self.config["bot"]["default_prefix"])

        # Register core command handler
        self.client.add_event_handler(
            self.on_command,
            tg.events.NewMessage(outgoing=True, func=self.command_predicate),
        )

        # Load modules
        self.load_all_modules()
        await self.dispatch_event("load")
        self.loaded = True

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

        self.log.info("Bot is ready")

        # Catch up on missed events now that handlers have been registered
        self.log.info("Catching up on missed events")
        await self.client.catch_up()
        self.log.info("Finished catching up")

    async def run(self: "Bot") -> None:
        try:
            # Start client
            try:
                await self.start()
            except KeyboardInterrupt:
                self.log.warning("Received interrupt while connecting")
                return

            # Request updates, then idle until disconnected
            await self.client.run_until_disconnected()
        finally:
            # Make sure we stop when done
            await self.stop()

    def update_module_event(
        self: "Bot", name: str, event_type: Type[EventType]
    ) -> None:
        if name in self.listeners:
            # Add if there ARE listeners and it's NOT already registered
            if name not in self._mevent_handlers:

                async def event_handler(event: EventType) -> None:
                    await self.dispatch_event(name, event)

                handler_info = (event_handler, event_type())
                self.client.add_event_handler(*handler_info)
                self._mevent_handlers[name] = handler_info
        elif name in self._mevent_handlers:
            # Remove if there are NO listeners and it's ALREADY registered
            self.client.remove_event_handler(*self._mevent_handlers[name])
            del self._mevent_handlers[name]

    def update_module_events(self: "Bot") -> None:
        self.update_module_event("message", tg.events.NewMessage)
        self.update_module_event("message_edit", tg.events.MessageEdited)
        self.update_module_event("message_delete", tg.events.MessageDeleted)
        self.update_module_event("message_read", tg.events.MessageRead)
        self.update_module_event("chat_action", tg.events.ChatAction)
        self.update_module_event("user_update", tg.events.UserUpdate)

    @property
    def events_activated(self: "Bot") -> int:
        return len(self._mevent_handlers)

    def redact_message(self, text: str) -> str:
        tg_config: Mapping[str, str] = self.config["telegram"]
        api_id = str(tg_config["api_id"])
        api_hash = tg_config["api_hash"]

        if api_id in text:
            text = text.replace(api_id, "[REDACTED]")
        if api_hash in text:
            text = text.replace(api_hash, "[REDACTED]")
        if self.user.phone is not None and self.user.phone in text:
            text = text.replace(self.user.phone, "[REDACTED]")

        return text

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
                text = self.redact_message(text)

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

        if mode == "reply":
            if response is not None:
                # Already replied, so just edit the existing reply to reduce spam
                return await response.edit(text=text, **kwargs)

            # Reply since we haven't done so yet
            return await msg.reply(text, **kwargs)

        if mode == "repost":
            if response is not None:
                # Already reposted, so just edit the existing reply to reduce spam
                return await response.edit(text=text, **kwargs)

            # Repost since we haven't done so yet
            response = await msg.respond(text, reply_to=msg.reply_to_msg_id, **kwargs)
            await msg.delete()
            return response

        raise ValueError(f"Unknown response mode '{mode}'")
