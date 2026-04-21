"""
core/logging_utils.py
_____________________
Thread-safe log queue. All modules call log() to emit messages;
the GUI LogPanel drains log_queue on its poll cycle.

Nothing here needs changing when adding new processors or sources.
"""

import collections
import threading
import time

log_queue: collections.deque[str] = collections.deque(maxlen=200)
log_lock = threading.Lock()


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    with log_lock:
        log_queue.append(line)