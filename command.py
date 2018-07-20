'''Command class'''

from typing import Callable, Union
import pyrogram as tg


def desc(_desc: str) -> Callable[[str], Callable[[Callable[[tg.Message], Union[None, str]]], Callable[[tg.Message], Union[None, str]]]]:
    def desc_decorator(func: Callable[[tg.Message], Union[None, str]]) -> Callable[[Callable[[tg.Message], Union[None, str]]], Callable[[tg.Message], Union[None, str]]]:
        func.description: str = _desc
        return func

    return desc_decorator
