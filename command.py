'''Command class'''

from typing import Callable, Union, NewType
import pyrogram as tg

CommandFunc = NewType('CommandFunc', Callable[[tg.Message], Union[None, str]])
CommandDecorator = NewType('CommandDecorator', Callable[[CommandFunc], CommandFunc])

Func = CommandFunc
Decorator = CommandDecorator

def desc(_desc: str) -> Callable[[str], CommandDecorator]:
    def desc_decorator(func: CommandFunc) -> CommandDecorator:
        func.description: str = _desc
        return func

    return desc_decorator
