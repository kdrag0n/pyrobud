import os
import traceback

from . import async_helpers, config, db, sentry, tg, time, version, system, git


run_sync = async_helpers.run_sync


def find_prefixed_funcs(obj, prefix):
    results = []

    for sym in dir(obj):
        if sym.startswith(prefix):
            name = sym[len(prefix) :]
            func = getattr(obj, sym)
            if not callable(func):
                continue

            results.append((name, func))

    return results


def format_exception(exp):
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
