import logging


def desc(_desc):
    def desc_decorator(func):
        func.cmd_description = _desc
        return func

    return desc_decorator


def alias(*aliases):
    def alias_decorator(func):
        if not hasattr(func, "cmd_aliases"):
            func.cmd_aliases = []

        func.cmd_aliases.extend(aliases)
        return func

    return alias_decorator


def error_level(_level):
    def level_decorator(func):
        func.cmd_error_level = _level
        return func

    return level_decorator


class Info:
    def __init__(self, name, module, func):
        self.name = name
        self.desc = getattr(func, "cmd_description", None)
        self.aliases = getattr(func, "cmd_aliases", [])
        self.error_level = getattr(func, "cmd_error_level", logging.ERROR)
        self.module = module
        self.func = func
