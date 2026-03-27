"""
gui/panels/base.py
──────────────────
Abstract base class for all processor GUI panels.

HOW TO ADD A NEW PANEL
──────────────────────
1. Create a new file, e.g.  gui/panels/hrv_panel.py
2. Subclass BasePanel:

    from gui.panels.base import BasePanel
    from gui.theme import THEME

    class HRVPanel(BasePanel):
        def __init__(self, parent, processor):
            super().__init__(parent)
            self._processor = processor
            self._active    = False
            self._build()

        def _build(self):
            t = THEME
            container = tk.Frame(self, bg=t["PANEL"])
            container.pack(fill="x", padx=20, pady=10, ipady=12)

            tk.Label(container, text="HRV (RMSSD)", bg=t["PANEL"],
                     fg=t["TEXT_DIM"], font=("Helvetica", 8, "bold")).pack()

            self._label = tk.Label(container, text="--", bg=t["PANEL"],
                                   fg=t["GREEN"], font=("Helvetica", 36, "bold"))
            self._label.pack()

            tk.Label(container, text="ms", bg=t["PANEL"],
                     fg=t["TEXT_DIM"], font=("Helvetica", 8)).pack()

        def on_server_start(self): self._active = True

        def on_server_stop(self):
            self._active = False
            self._label.config(text="--")

        def update(self):
            if self._active:
                v = self._processor.hrv_rmssd
                self._label.config(text=f"{v:.1f}" if v else "--")

3. Return it from your processor's create_panel():

    def create_panel(self, parent):
        from gui.panels.hrv_panel import HRVPanel
        return HRVPanel(parent, self)

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

    # ── Abstract ───────────────────────────────────────────────────────────

    @abstractmethod
    def update(self) -> None:
        """
        Refresh display from latest processor state.
        Called by App every POLL_MS milliseconds.
        Keep this fast — no blocking I/O.
        """

    # ── Optional hooks ─────────────────────────────────────────────────────

    def on_server_start(self) -> None:
        """Called when the HTTP server starts. Override to enable live display."""

    def on_server_stop(self) -> None:
        """Called when the HTTP server stops. Override to reset display."""