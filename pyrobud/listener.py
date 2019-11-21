def priority(_prio):
    def prio_decorator(func):
        func.listener_priority = _prio
        return func

    return prio_decorator
