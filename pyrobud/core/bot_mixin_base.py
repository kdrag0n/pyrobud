from typing import TYPE_CHECKING, Any

MixinBase: Any
if TYPE_CHECKING:
    from .bot import Bot

    MixinBase = Bot
else:
    import abc

    MixinBase = abc.ABC
