from typing import Any, Callable

ListenerFunc = Any
Decorator = Callable[[ListenerFunc], ListenerFunc]


def priority(_prio: int) -> Decorator:
    """Sets priority on the given listener function."""

    def prio_decorator(func: ListenerFunc) -> ListenerFunc:
        setattr(func, "_listener_priority", _prio)
        return func

    return prio_decorator


class Listener:
    event: str
    func: ListenerFunc
    module: Any
    priority: int

    def __init__(self, event: str, func: ListenerFunc, mod: Any, prio: int) -> None:
        self.event = event
        self.func = func
        self.module = mod
        self.priority = prio

    def __lt__(self, other: "Listener") -> bool:
        return self.priority < other.priority
