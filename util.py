'''Utility functions'''

from datetime import datetime
import time

def time_us() -> float:
    return time.time() * 1000000

def time_ms() -> float:
    return time_us() / 1000.0
