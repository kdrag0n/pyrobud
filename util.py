import time
from datetime import datetime

def time_us():
    return time.time() * 1000000

def time_ms():
    return time_us() / 1000.0
