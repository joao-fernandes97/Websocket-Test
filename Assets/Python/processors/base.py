"""
processors/base.py
──────────────────
Abstract base class for all signal processors.

HOW TO ADD A NEW PROCESSOR
──────────────────────────
1. Create a new file, e.g.  processors/hrv_processor.py
2. Subclass BaseProcessor:

    class HRVProcessor(BaseProcessor):
        name = "HRV"

        def __init__(self, source: BaseSignalSource):
            self._source = source
            self._hrv    = 0.0
            self._lock   = threading.Lock()
            self._thread: threading.Thread | None = None
            self._stop   = threading.Event()

        def start(self):
            self._stop.clear()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

        def stop(self):
            self._stop.set()

        def get_routes(self):
            return [("/hrv", self._api_hrv)]

        def _api_hrv(self):
            with self._lock:
                return {"hrv_rmssd": self._hrv}

        def create_panel(self, parent):
            from gui.panels.hrv_panel import HRVPanel
            return HRVPanel(parent, self)

        def _worker(self):
            while not self._stop.is_set():
                ...  # read self._source.buffer, compute, update self._hrv

3. Register it in main.py:
        processors = [BPMProcessor(ecg_source), HRVProcessor(ecg_source)]
   That's it — routes and GUI panel are picked up automatically.
"""

import tkinter as tk
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.panels.base import BasePanel
    from signals.base import BaseSignalSource


class BaseProcessor(ABC):
    """
    Reads from a BaseSignalSource, computes a metric, exposes it via HTTP,
    and optionally provides a GUI panel.
    """

    name: str = "unnamed_processor"

    @abstractmethod
    def start(self) -> None:
        """Launch background computation thread."""

    @abstractmethod
    def stop(self) -> None:
        """Signal background thread to exit."""

    @abstractmethod
    def get_routes(self) -> list[tuple[str, callable]]:
        """
        Return (path, handler) pairs for FastAPI registration.

        Example:
            return [("/bpm", self._api_bpm), ("/bpm/raw", self._api_raw)]
        """
        return []

    def create_panel(self, parent: tk.Widget) -> "BasePanel | None":
        """
        Return a GUI panel Frame for this processor, or None.

        Override in processors that want a visible widget in the main window.
        The App will call panel.update() every POLL_MS and notify it of
        server start/stop via on_server_start() / on_server_stop().
        """
        return None