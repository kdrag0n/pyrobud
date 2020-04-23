from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional, Sequence, Union

import telethon as tg

from . import util

if TYPE_CHECKING:
    from .core import Bot

CommandFunc = Union[
    Callable[..., Coroutine[Any, Any, None]],
    Callable[..., Coroutine[Any, Any, Optional[str]]],
]
Decorator = Callable[[CommandFunc], CommandFunc]


def desc(_desc: str) -> Decorator:
    """Sets description on a command function."""

    def desc_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_description", _desc)
        return func

    return desc_decorator


def usage(_usage: str, optional: bool = False, reply: bool = False) -> Decorator:
    """Sets argument usage help on a command function."""

    def usage_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_usage", _usage)
        setattr(func, "_cmd_usage_optional", optional)
        setattr(func, "_cmd_usage_reply", reply)
        return func

    return usage_decorator


def alias(*aliases: str) -> Decorator:
    """Sets aliases on a command function."""

    def alias_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_aliases", aliases)
        return func

    return alias_decorator


class Command:
    name: str
    desc: str
    usage: str
    usage_optional: bool
    usage_reply: bool
    aliases: Sequence[str]
    module: Any
    func: CommandFunc

    def __init__(self, name: str, mod: Any, func: CommandFunc) -> None:
        self.name = name
        self.desc = getattr(func, "_cmd_description", None)
        self.usage = getattr(func, "_cmd_usage", None)
        self.usage_optional = getattr(func, "_cmd_usage_optional", False)
        self.usage_reply = getattr(func, "_cmd_usage_reply", False)
        self.aliases = getattr(func, "_cmd_aliases", [])
        self.module = mod
        self.func = func


# Command invocation context
class Context:
    bot: "Bot"
    message: tg.custom.Message
    segments: Sequence[str]
    cmd_len: int
    invoker: str

    response: Optional[tg.custom.Message]
    response_mode: Optional[str]
    input: str
    plain_input: str
    args: Sequence[str]

    def __init__(
        self,
        bot: "Bot",
        message: tg.custom.Message,
        segments: Sequence[str],
        cmd_len: int,
    ) -> None:
        self.bot = bot
        self.message = message
        self.segments = segments
        self.cmd_len = cmd_len
        self.invoker = segments[0]

        # Response message to be filled later
        self.response = None
        self.response_mode = None
        # Single argument string (unparsed, i.e. complete with Markdown formatting symbols)
        self.input = self.message.text[self.cmd_len :]
        # Single argument string (parsed, i.e. plain text)
        self.plain_input = self.message.raw_text[self.cmd_len :]

    # Lazily resolve expensive fields
    def __getattr__(self, name: str) -> Any:
        if name == "args":
            return self._get_args()

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    # Argument segments
    def _get_args(self) -> Sequence[str]:
        self.args = self.segments[1:]
        return self.args

    # Wrapper for Bot.respond()
    async def respond(
        self,
        text: Optional[str] = None,
        *,
        mode: Optional[str] = None,
        overflow: Optional[str] = None,
        max_pages: Optional[int] = None,
        redact: Optional[bool] = None,
        message: Optional[tg.custom.Message] = None,
        reuse_response: bool = False,
        **kwargs: Any,
    ) -> tg.custom.Message:
        if overflow is None:
            overflow = self.bot.config["bot"]["overflow_mode"]

        # Handle splitting early because it requires persistent state
        if text and overflow == "split":
            return await self.respond_split(
                text,
                mode=mode,
                max_pages=max_pages,
                redact=redact,
                message=message,
                reuse_response=reuse_response,
                **kwargs,
            )

        self.response = await self.bot.respond(
            message or self.message,
            text,
            mode=mode,
            redact=redact,
            response=self.response
            if reuse_response and mode == self.response_mode
            else None,
            **kwargs,
        )
        self.response_mode = mode
        return self.response

    async def respond_split(
        self,
        text: str,
        *,
        max_pages: Optional[int] = None,
        redact: Optional[bool] = None,
        **kwargs: Any,
    ) -> tg.custom.Message:
        if redact is None:
            redact = self.bot.config["bot"]["redact_responses"]

        if max_pages is None:
            max_pages = self.bot.config["bot"]["overflow_page_limit"]

        if redact:
            # Redact before splitting in case the sensitive content is on a message boundary
            text = self.bot.redact_message(text)

        pages_sent = 0
        last_msg = None
        while pages_sent < max_pages:
            # Make sure that there's an ellipsis placed at both the beginning and end,
            # depending on whether there's more content to be shown
            # The conditions are a bit complex, so just use a primitive LUT for now
            if len(text) <= 4096:
                # Low remaining content might require no ellipses
                if pages_sent == 0:
                    page = text[: util.tg.MESSAGE_CHAR_LIMIT]
                    ellipsis_chars = 0
                else:
                    page = "..." + text[: util.tg.MESSAGE_CHAR_LIMIT - 3]
                    ellipsis_chars = 3
            elif pages_sent == max_pages - 1:
                # Last page should use the standard truncation path if it's too large
                if pages_sent == 0:
                    page = text
                    ellipsis_chars = 0
                else:
                    page = "..." + text
                    ellipsis_chars = 3
            else:
                # Remaining content in other pages might need two ellipses
                if pages_sent == 0:
                    page = text[: util.tg.MESSAGE_CHAR_LIMIT - 3] + "..."
                    ellipsis_chars = 3
                else:
                    page = "..." + text[: util.tg.MESSAGE_CHAR_LIMIT - 6] + "..."
                    ellipsis_chars = 6

            last_msg = await self.respond_multi(page, **kwargs)
            text = text[util.tg.MESSAGE_CHAR_LIMIT - ellipsis_chars :]
            pages_sent += 1

        return last_msg

    async def respond_multi(
        self,
        *args: Any,
        mode: Optional[str] = None,
        message: Optional[tg.custom.Message] = None,
        reuse_response: bool = False,
        **kwargs: Any,
    ) -> tg.custom.Message:
        # First response is the same
        if self.response:
            # After that, force a reply to the previous response
            if mode is None:
                mode = "reply"

            if message is None:
                message = self.response

            if reuse_response is None:
                reuse_response = False

        return await self.respond(
            *args, mode=mode, message=message, reuse_response=reuse_response, **kwargs
        )
