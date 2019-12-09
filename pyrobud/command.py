import logging

from . import util


def desc(_desc):
    def desc_decorator(func):
        func.cmd_description = _desc
        return func

    return desc_decorator


def usage(_usage, optional=False, reply=False):
    def usage_decorator(func):
        func.cmd_usage = _usage
        func.cmd_usage_optional = optional
        func.cmd_usage_reply = reply
        return func

    return usage_decorator


def alias(*aliases):
    def alias_decorator(func):
        if not hasattr(func, "cmd_aliases"):
            func.cmd_aliases = []

        func.cmd_aliases.extend(aliases)
        return func

    return alias_decorator


class Info:
    def __init__(self, name, module, func):
        self.name = name
        self.desc = getattr(func, "cmd_description", None)
        self.usage = getattr(func, "cmd_usage", None)
        self.usage_optional = getattr(func, "cmd_usage_optional", False)
        self.usage_reply = getattr(func, "cmd_usage_reply", False)
        self.aliases = getattr(func, "cmd_aliases", [])
        self.module = module
        self.func = func


# Command invocation context
class Context:
    def __init__(self, bot, msg, segments, cmd_len):
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
    def __getattr__(self, name):
        if name == "args":
            return self._get_args()
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    # Argument segments
    def _get_args(self):
        self.args = self.segments[1:]
        return self.args

    # Convenience alias for Bot.respond()
    async def respond(self, text, *, mode=None, **kwargs):
        self.response = await self.bot.respond(self.msg, text, mode=mode, response=self.response, **kwargs)
        return self.response
