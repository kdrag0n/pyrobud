import logging


def desc(_desc):
    def desc_decorator(func):
        func.description = _desc
        return func

    return desc_decorator


def alias(*aliases):
    def alias_decorator(func):
        if not hasattr(func, "aliases"):
            func.aliases = []

        func.aliases.extend(aliases)
        return func

    return alias_decorator


def error_level(_level):
    def level_decorator(func):
        func.error_level = _level
        return func

    return level_decorator


class Info:
    def __init__(self, name, module, func):
        self.name = name
        self.desc = getattr(func, "description", None)
        self.aliases = getattr(func, "aliases", [])
        self.error_level = getattr(func, "error_level", logging.ERROR)
        self.module = module
        self.func = func
