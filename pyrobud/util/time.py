import time
from typing import Union


def usec() -> int:
    return int(time.time() * 1000000)


def msec() -> int:
    return int(usec() / 1000)


def sec() -> int:
    return int(time.time())


def format_duration_us(t_us: Union[int, float]) -> str:
    t_us = int(t_us)

    t_ms = t_us / 1000
    t_s = t_ms / 1000
    t_m = t_s / 60
    t_h = t_m / 60
    t_d = t_h / 24

    if t_d >= 1:
        rem_h = t_h % 24
        return "%dd %dh" % (t_d, rem_h)

    if t_h >= 1:
        rem_m = t_m % 60
        return "%dh %dm" % (t_h, rem_m)

    if t_m >= 1:
        rem_s = t_s % 60
        return "%dm %ds" % (t_m, rem_s)

    if t_s >= 10:
        return "%d sec" % t_s

    if t_ms >= 10:
        return "%d ms" % t_ms

    return "%d μs" % t_us
