import asyncio
import bisect
from typing import TYPE_CHECKING, Any, MutableMapping, MutableSequence

from .. import module, util
from ..listener import Listener, ListenerFunc
from .bot_mixin_base import MixinBase

if TYPE_CHECKING:
    from .bot import Bot


class EventDispatcher(MixinBase):
    # Initialized during instantiation
    listeners: MutableMapping[str, MutableSequence[Listener]]

    def __init__(self: "Bot", **kwargs: Any) -> None:
        # Initialize listener map
        self.listeners = {}

        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    def register_listener(
        self: "Bot",
        mod: module.Module,
        event: str,
        func: ListenerFunc,
        priority: int = 100,
    ) -> None:
        listener = Listener(event, func, mod, priority)

        if event in self.listeners:
            bisect.insort(self.listeners[event], listener)
        else:
            self.listeners[event] = [listener]

        self.update_module_events()

    def unregister_listener(self: "Bot", listener: Listener) -> None:
        self.listeners[listener.event].remove(listener)
        # Remove list if empty
        if not self.listeners[listener.event]:
            del self.listeners[listener.event]

        self.update_module_events()

    def register_listeners(self: "Bot", mod: module.Module) -> None:
        for event, func in util.find_prefixed_funcs(mod, "on_"):
            done = True
            try:
                self.register_listener(
                    mod, event, func, priority=getattr(func, "_listener_priority", 100)
                )
                done = True
            finally:
                if not done:
                    self.unregister_listeners(mod)

    def unregister_listeners(self: "Bot", mod: module.Module) -> None:
        # Can't unregister while iterating, so collect listeners to unregister afterwards
        to_unreg = []

        for lst in self.listeners.values():
            for listener in lst:
                if listener.module == mod:
                    to_unreg.append(listener)

        # Actually unregister the listeners
        for listener in to_unreg:
            self.unregister_listener(listener)

    async def dispatch_event(
        self: "Bot", event: str, *args: Any, wait: bool = True, **kwargs: Any
    ) -> None:
        tasks = set()

        try:
            listeners = self.listeners[event]
        except KeyError:
            return None

        if not listeners:
            return

        for lst in listeners:
            task = self.loop.create_task(lst.func(*args, **kwargs))
            tasks.add(task)

        self.log.debug("Dispatching event '%s' with data %s", event, args)
        if wait:
            await asyncio.wait(tasks)

    async def log_stat(self: "Bot", stat: str) -> None:
        await self.dispatch_event("stat_event", stat, wait=False)
