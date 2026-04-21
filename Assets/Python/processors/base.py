"""
processors/base.py
__________________________
Abstract base class for all signal processors.

HOW TO ADD A NEW PROCESSOR
__________________________
1. Create a new file, e.g.  processors/hrv_processor.py
2. Subclass BaseProcessor:
3. Register it in main.py:
        processors = [BPMProcessor(ecg_source), HRVProcessor(ecg_source)]
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