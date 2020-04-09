import os
import traceback
from typing import Any, Callable, List, Optional, Sequence, Tuple

from . import async_helpers, config, db, git, image, sentry, system, text, tg, time, version

INPUT_YES = (
    "y",
    "yes",
    "true",
    "t",
    "on",
    "enable",
    "enabled",
    "active",
    "activate",
    "activated",
)

run_sync = async_helpers.run_sync


def find_prefixed_funcs(obj: Any, prefix: str) -> Sequence[Tuple[str, Callable]]:
    results = []

    for sym in dir(obj):
        if sym.startswith(prefix):
            name = sym[len(prefix) :]
            func = getattr(obj, sym)
            if not callable(func):
                continue

            results.append((name, func))

    return results


def format_exception(exp: BaseException, tb: Optional[List[traceback.FrameSummary]] = None) -> str:
    if tb is None:
        tb = traceback.extract_tb(exp.__traceback__)

    # Replace absolute paths with relative paths
    cwd = os.getcwd()
    for frame in tb:
        if cwd in frame.filename:
            frame.filename = os.path.relpath(frame.filename)

    stack = "".join(traceback.format_list(tb))
    msg = str(exp)
    if msg:
        msg = ": " + msg

    return f"Traceback (most recent call last):\n{stack}{type(exp).__name__}{msg}"
