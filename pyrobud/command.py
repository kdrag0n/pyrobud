from typing import Any, Callable, List, Optional, TYPE_CHECKING, Coroutine, Union, Sequence

import telethon as tg

if TYPE_CHECKING:
    from .bot import Bot

CommandFunc = Union[
    Callable[..., Coroutine[Any, Any, None]], Callable[..., Coroutine[Any, Any, Optional[str]]],
]
Decorator = Callable[[CommandFunc], CommandFunc]


def desc(_desc: str) -> Decorator:
    def desc_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_description", _desc)
        return func

    return desc_decorator


def usage(_usage: str, optional: bool = False, reply: bool = False) -> Decorator:
    def usage_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_usage", _usage)
        setattr(func, "_cmd_usage_optional", optional)
        setattr(func, "_cmd_usage_reply", reply)
        return func

    return usage_decorator


def alias(*aliases: str) -> Decorator:
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
    msg: tg.custom.Message
    segments: Sequence[str]
    cmd_len: int
    invoker: str

    response: Optional[tg.custom.Message]
    input: str
    parsed_input: str
    args: Sequence[str]

    def __init__(self, bot: "Bot", msg: tg.custom.Message, segments: Sequence[str], cmd_len: int) -> None:
        self.bot = bot
        self.msg = msg
        self.segments = segments
        self.cmd_len = cmd_len
        self.invoker = segments[0]

        # Response message to be filled later
        self.response = None
        # Single argument string (unparsed, i.e. complete with Markdown formatting symbols)
        self.input = self.msg.text[self.cmd_len :]
        # Single argument string (parsed, i.e. plain text)
        self.parsed_input = self.msg.raw_text[self.cmd_len :]

    # Lazily resolve expensive fields
    def __getattr__(self, name: str) -> Any:
        if name == "args":
            return self._get_args()
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # Argument segments
    def _get_args(self) -> Sequence[str]:
        self.args = self.segments[1:]
        return self.args

    # Convenience alias for Bot.respond()
    async def respond(
        self, text: Optional[str] = None, *, mode: Optional[str] = None, **kwargs: Any
    ) -> tg.custom.Message:
        self.response = await self.bot.respond(self.msg, text, mode=mode, response=self.response, **kwargs)
        return self.response
