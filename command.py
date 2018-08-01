'''Command class'''

from typing import Callable, Union, NewType, Tuple
import pyrogram as tg

CommandFunc = NewType('CommandFunc', Callable[[tg.Message], Union[None, str]])
CommandDecorator = NewType('CommandDecorator', Callable[[CommandFunc], CommandFunc])

Func = CommandFunc
Decorator = CommandDecorator

def desc(_desc: str) -> CommandDecorator:
    def desc_decorator(func: CommandFunc) -> CommandFunc:
        func.description: str = _desc
        return func

    return desc_decorator

def alias(*aliases: Tuple[str]) -> CommandDecorator:
    def alias_decorator(func: CommandFunc) -> CommandFunc:
        if not hasattr(func, 'aliases'):
            func.aliases: List[str] = []

        func.aliases.extend(aliases)
        return func

    return alias_decorator
