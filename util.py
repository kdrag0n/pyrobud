'''Utility functions'''

from datetime import datetime
import time

def time_ms() -> float:
    now = datetime.now()
    return time.mktime(now.timetuple()) + now.microsecond / 1000.0

def time_us() -> float:
    now = datetime.now()
    return time.mktime(now.timetuple()) + now.microsecond
