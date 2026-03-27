"""
gui/app.py
──────────
Main Tkinter application window.

Responsibilities:
  • Render the chrome (title bar, status row, endpoint list, Start/Stop buttons)
  • Discover panels from processors and stack them between status and buttons
  • Run a single poll loop that drives panel.update() for every registered panel
  • Notify panels of server lifecycle events (start / stop)

The App knows nothing about specific biometrics — all signal-specific logic
lives in processors and their panels.

EXTENDING THE WINDOW
────────────────────
To add a new panel, add its processor in main.py.  The App will automatically:
  • Call processor.create_panel(self) and insert the result
  • Include the processor's routes in the endpoint label
  • Drive panel.update() on every poll tick
  • Call panel.on_server_start/stop() on lifecycle changes
"""

import tkinter as tk

from core import server
from core.network_utils import get_local_ip
from gui.panels.base import BasePanel
from gui.theme import THEME


class App(tk.Tk):
    POLL_MS = 400  # drives all panel.update() calls

    def __init__(
        self,
        processors: list,
        debug: bool = False,
        port: int   = 8000,
    ) -> None:
        super().__init__()
        self.title("BioSignal Server")
        self.resizable(False, False)
        self.configure(bg=THEME["BG"])

        self._processors = processors
        self._panels:    list[BasePanel] = []
        self._debug      = debug
        self._port       = port
        self._running    = False

        self._build_ui()
        self._schedule_poll()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        t = THEME

        # Title bar
        header = tk.Frame(self, bg=t["ACCENT"])
        header.pack(fill="x")
        tk.Label(
            header, text="  BioSignal Server",
            bg=t["ACCENT"], fg=t["TEXT_LIGHT"],
            font=("Helvetica", 13, "bold"),
            anchor="w", pady=10,
        ).pack(fill="x")

        # Status indicator
        status_row = tk.Frame(self, bg=t["BG"])
        status_row.pack(fill="x", padx=20, pady=(16, 4))

        tk.Label(
            status_row, text="Status",
            bg=t["BG"], fg=t["TEXT_DIM"],
            font=("Helvetica", 9),
        ).pack(side="left")

        self._dot = tk.Label(
            status_row, text="●",
            bg=t["BG"], fg=t["RED"],
            font=("Helvetica", 14),
        )
        self._dot.pack(side="left", padx=(8, 4))

        self._status_label = tk.Label(
            status_row, text="Stopped",
            bg=t["BG"], fg=t["RED"],
            font=("Helvetica", 10, "bold"),
        )
        self._status_label.pack(side="left")

        # ── Processor panels (dynamically inserted) ────────────────────────
        for proc in self._processors:
            panel = proc.create_panel(self)
            if panel is not None:
                panel.pack(fill="x")
                self._panels.append(panel)

        # Endpoint list
        ip         = get_local_ip()
        route_strs = [
            f"http://{ip}:{self._port}{path}"
            for proc in self._processors
            for path, _ in proc.get_routes()
        ]
        info_row = tk.Frame(self, bg=t["BG"])
        info_row.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(
            info_row, text="Endpoints:",
            bg=t["BG"], fg=t["TEXT_DIM"],
            font=("Helvetica", 9),
        ).pack(side="left")
        tk.Label(
            info_row, text="  " + "   ".join(route_strs),
            bg=t["BG"], fg=t["TEXT_LIGHT"],
            font=("Courier", 9),
        ).pack(side="left")

        # Start / Stop buttons
        btn_row = tk.Frame(self, bg=t["BG"])
        btn_row.pack(pady=(4, 20), padx=20, fill="x")

        btn_cfg = dict(
            font=("Helvetica", 11, "bold"),
            relief="flat", cursor="hand2",
            width=10, pady=8,
        )
        self._start_btn = tk.Button(
            btn_row, text="▶  Start",
            bg=t["GREEN"], fg=t["BG"],
            activebackground=t["GREEN_DARK"], activeforeground=t["BG"],
            command=self._on_start, **btn_cfg,
        )
        self._start_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self._stop_btn = tk.Button(
            btn_row, text="■  Stop",
            bg=t["RED"], fg=t["TEXT_LIGHT"],
            activebackground=t["RED_DARK"], activeforeground=t["TEXT_LIGHT"],
            state="disabled", command=self._on_stop, **btn_cfg,
        )
        self._stop_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

        # Debug log panel (last, so it expands to fill remaining height)
        if self._debug:
            from gui.panels.log_panel import LogPanel
            log_panel = LogPanel(self)
            log_panel.pack(fill="both", expand=True)
            self._panels.append(log_panel)

    # ── Button callbacks ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._running = True
        server.start_server(self._port)
        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._set_status("Running", THEME["GREEN"])
        for panel in self._panels:
            panel.on_server_start()

    def _on_stop(self) -> None:
        self._running = False
        server.stop_server()
        self._start_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._set_status("Stopped", THEME["RED"])
        for panel in self._panels:
            panel.on_server_stop()

    def _on_close(self) -> None:
        server.stop_server()
        self.destroy()

    # ── Poll loop ──────────────────────────────────────────────────────────

    def _schedule_poll(self) -> None:
        self.after(self.POLL_MS, self._poll)

    def _poll(self) -> None:
        for panel in self._panels:
            try:
                panel.update()
            except Exception:
                pass
        self.after(self.POLL_MS, self._poll)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _set_status(self, text: str, colour: str) -> None:
        self._dot.config(fg=colour)
        self._status_label.config(text=text, fg=colour)