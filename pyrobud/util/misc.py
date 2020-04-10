from typing import Any, Callable, Sequence, Tuple


def find_prefixed_funcs(obj: Any, prefix: str) -> Sequence[Tuple[str, Callable]]:
    """Finds functions with symbol names matching the prefix on the given object."""

    results = []

    for sym in dir(obj):
        if sym.startswith(prefix):
            name = sym[len(prefix) :]
            func = getattr(obj, sym)
            if not callable(func):
                continue

            results.append((name, func))

    return results
