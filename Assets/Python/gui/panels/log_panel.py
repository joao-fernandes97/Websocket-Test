"""
gui/panels/log_panel.py
───────────────────────
Scrollable debug log panel.
Not tied to any specific processor — drains the shared log_queue.
Instantiated directly by App when debug=True.
"""

import tkinter as tk

from core.logging_utils import log_lock, log_queue
from gui.panels.base import BasePanel
from gui.theme import THEME


class LogPanel(BasePanel):
    """Displays the rolling log_queue in a read-only text widget."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self._last_len = 0
        self._build()

    def _build(self) -> None:
        t = THEME

        header = tk.Frame(self, bg=t["ACCENT"])
        header.pack(fill="x")
        tk.Label(
            header, text="  Debug Log",
            bg=t["ACCENT"], fg=t["TEXT_DIM"],
            font=("Helvetica", 8, "bold"),
            anchor="w", pady=4,
        ).pack(fill="x")

        log_frame = tk.Frame(self, bg=t["LOG_BG"])
        log_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self._text = tk.Text(
            log_frame,
            bg=t["LOG_BG"], fg=t["LOG_FG"],
            font=("Courier", 8),
            height=12, width=72,
            relief="flat",
            state="disabled",
            yscrollcommand=scrollbar.set,
            wrap="word",
        )
        self._text.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        scrollbar.config(command=self._text.yview)

    # ── BasePanel ──────────────────────────────────────────────────────────

    def update(self) -> None:
        with log_lock:
            current_len = len(log_queue)
            if current_len == self._last_len:
                return
            new_lines      = list(log_queue)[self._last_len:]
            self._last_len = current_len

        self._text.config(state="normal")
        for line in new_lines:
            self._text.insert("end", line + "\n")
        self._text.see("end")
        self._text.config(state="disabled")