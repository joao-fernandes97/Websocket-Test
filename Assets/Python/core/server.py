"""
core/server.py
──────────────
FastAPI app singleton + uvicorn lifecycle management.

Processors call register_route() once at startup to expose their endpoints.
The GUI calls start_server() / stop_server() on button press.

Lifecycle hooks (on_start / on_stop) let any module react to server
start/stop without coupling it to the GUI (used for LSL markers, etc.).

Nothing here needs changing when adding new processors.
"""

import threading
from typing import Callable

import uvicorn
from fastapi import FastAPI

from core.logging_utils import log

# ── Singleton app ──────────────────────────────────────────────────────────

_app = FastAPI()
_uvicorn_server: uvicorn.Server | None = None
_server_thread: threading.Thread | None = None

_start_callbacks: list[Callable] = []
_stop_callbacks:  list[Callable] = []


def get_app() -> FastAPI:
    return _app


# ── Route registration ─────────────────────────────────────────────────────

def register_route(path: str, handler: Callable, methods: list[str] | None = None) -> None:
    """
    Add a GET endpoint to the shared FastAPI app.

    Processors call this once during setup:
        server.register_route("/bpm", my_bpm_handler)
    """
    _app.add_api_route(path, handler, methods=methods or ["GET"])
    log(f"[server] registered route {path}")


# ── Lifecycle hooks ────────────────────────────────────────────────────────

def on_start(callback: Callable) -> None:
    """Register a zero-argument callback to run when the server starts."""
    _start_callbacks.append(callback)


def on_stop(callback: Callable) -> None:
    """Register a zero-argument callback to run when the server stops."""
    _stop_callbacks.append(callback)


# ── Start / stop ───────────────────────────────────────────────────────────

def start_server(port: int = 8000) -> None:
    global _uvicorn_server, _server_thread

    if _server_thread and _server_thread.is_alive():
        return

    def _run() -> None:
        global _uvicorn_server
        cfg = uvicorn.Config(_app, host="0.0.0.0", port=port, log_level="error")
        _uvicorn_server = uvicorn.Server(cfg)
        log(f"[server] FastAPI started on port {port}")
        _uvicorn_server.run()

    _server_thread = threading.Thread(target=_run, daemon=True, name="uvicorn")
    _server_thread.start()

    for cb in _start_callbacks:
        try:
            cb()
        except Exception as e:
            log(f"[server] on_start callback error: {e}")


def stop_server() -> None:
    global _uvicorn_server
    if _uvicorn_server:
        _uvicorn_server.should_exit = True
    log("[server] stopped.")

    for cb in _stop_callbacks:
        try:
            cb()
        except Exception as e:
            log(f"[server] on_stop callback error: {e}")