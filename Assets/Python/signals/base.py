"""
signals/base.py
───────────────
Abstract base class for all signal sources.

HOW TO ADD A NEW SOURCE
───────────────────────
1. Create a new file, e.g.  signals/my_device_source.py
2. Subclass BaseSignalSource and implement every abstract member:

    class MyDeviceSource(BaseSignalSource):
        name = "My Device"

        def __init__(self, ...):
            self._buf  = collections.deque()
            self._lock = threading.Lock()
            self._sr   = 500          # samples per second
            ...

        @property
        def sampling_rate(self): return self._sr

        @property
        def buffer(self): return self._buf

        @property
        def buffer_lock(self): return self._lock

        def start(self): ...   # launch background thread
        def stop(self):  ...   # signal thread to exit

3. Optionally expose push_marker(label) if your device has an event outlet.
4. Instantiate it in main.py and pass it to your processors.

The buffer must contain (monotonic_timestamp: float, value: float) tuples,
newest at the right end (collections.deque append / popleft).
"""

import collections
import threading
from abc import ABC, abstractmethod


class BaseSignalSource(ABC):
    """Captures raw samples into a thread-safe ring buffer."""

    name: str = "unnamed_source"

    # ── Abstract interface ─────────────────────────────────────────────────

    @property
    @abstractmethod
    def sampling_rate(self) -> int:
        """Nominal samples per second."""

    @property
    @abstractmethod
    def buffer(self) -> collections.deque:
        """
        Ring buffer of (monotonic_timestamp, sample_value) tuples.
        Processors read from this under buffer_lock.
        """

    @property
    @abstractmethod
    def buffer_lock(self) -> threading.Lock:
        """Lock that guards buffer."""

    @abstractmethod
    def start(self) -> None:
        """Begin capturing and filling buffer."""

    @abstractmethod
    def stop(self) -> None:
        """Signal background thread to exit."""