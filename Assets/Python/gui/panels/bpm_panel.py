"""
gui/panels/bpm_panel.py
_______________________
Large numeric BPM display driven by a BPMProcessor.
Registered automatically when BPMProcessor.create_panel() is called.
"""

import tkinter as tk

from gui.panels.base import BasePanel
from gui.theme import THEME


class BPMPanel(BasePanel):
    """Displays live BPM as a large number."""

    def __init__(self, parent: tk.Widget, processor) -> None:
        super().__init__(parent)
        self._processor = processor
        self._active    = False
        self._build()

    def _build(self) -> None:
        t = THEME
        container = tk.Frame(self, bg=t["PANEL"], bd=0)
        container.pack(fill="x", padx=20, pady=10, ipady=16)

        tk.Label(
            container, text="LIVE BPM",
            bg=t["PANEL"], fg=t["TEXT_DIM"],
            font=("Helvetica", 8, "bold"),
        ).pack()

        self._value_label = tk.Label(
            container, text="--",
            bg=t["PANEL"], fg=t["GREEN"],
            font=("Helvetica", 48, "bold"),
        )
        self._value_label.pack()

        tk.Label(
            container, text="beats per minute",
            bg=t["PANEL"], fg=t["TEXT_DIM"],
            font=("Helvetica", 8),
        ).pack()

    # BasePanel

    def on_server_start(self) -> None:
        self._active = True

    def on_server_stop(self) -> None:
        self._active = False
        self._value_label.config(text="--")

    def update(self) -> None:
        if not self._active:
            return
        bpm = self._processor.bpm
        self._value_label.config(text=f"{bpm:.1f}" if bpm else "--")