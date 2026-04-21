"""
gui/panels/base.py
__________________
Abstract base class for all processor GUI panels.

HOW TO ADD A NEW PANEL
______________________
1. Create a new file, e.g.  gui/panels/hrv_panel.py
2. Subclass BasePanel:
3. Return it from your processor's create_panel()

The App will call update() every POLL_MS ms and call on_server_start/stop()
on lifecycle events automatically.
"""

import tkinter as tk
from abc import ABC, abstractmethod

from gui.theme import THEME


class BasePanel(tk.Frame, ABC):
    """Self-contained GUI widget for a single processor."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=THEME["BG"], **kwargs)

    # Abstract

    @abstractmethod
    def update(self) -> None:
        """
        Refresh display from latest processor state.
        Called by App every POLL_MS milliseconds.
        Keep this fast — no blocking I/O.
        """

    # Optional hooks

    def on_server_start(self) -> None:
        """Called when the HTTP server starts. Override to enable live display."""

    def on_server_stop(self) -> None:
        """Called when the HTTP server stops. Override to reset display."""