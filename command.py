import pyrogram as tg

def desc(_desc):
    def desc_decorator(func):
        func.description = _desc
        return func

    return desc_decorator

def alias(*aliases):
    def alias_decorator(func):
        if not hasattr(func, 'aliases'):
            func.aliases = []

        func.aliases.extend(aliases)
        return func

    return alias_decorator

class Info():
    def __init__(self, name, module, func):
        self.name = name
        self.desc = getattr(func, 'description', None)
        self.aliases = getattr(func, 'aliases', [])
        self.module = module
        self.func = func
