import time
import threading
import subprocess
import sys
import os
import tkinter as tk
import socket
from tkinter import font as tkfont
import neurokit2 as nk
import numpy as np
import uvicorn
import collections
from fastapi import FastAPI
from pylsl import StreamInlet, resolve_stream

# Close Console Window after startup
if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Get IPv4 adress
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI()

SAMPLING_RATE = 250
WINDOW_SECONDS = 5

MAX_BUFFER_SECONDS = WINDOW_SECONDS + 2
ecg_buffer = collections.deque()
buffer_lock = threading.Lock()

#ecg_signal = nk.ecg_simulate(duration=120, sampling_rate=SAMPLING_RATE)
#signals, info = nk.ecg_process(ecg_signal, sampling_rate=SAMPLING_RATE)

#rpeaks = info["ECG_R_Peaks"]
#rpeak_times = rpeaks / SAMPLING_RATE

current_bpm = 0.0
bpm_lock = threading.Lock()
start_time = None          # set when server actually starts

# ---------------------------------------------------------------------------
# LSL ingestion thread — replaces ecg_simulate + static rpeaks
# ---------------------------------------------------------------------------
def lsl_worker():
    print("Looking for an available OpenSignals stream...")
    streams = resolve_stream("name", "OpenSignals")
    inlet = StreamInlet(streams[0])
    print("Stream found. Ingesting samples...")

    try:
        while True:
            # pull_chunk is more efficient than pull_sample in a tight loop
            samples, timestamps = inlet.pull_chunk(timeout=1.0, max_samples=32)
            if timestamps:
                now = time.monotonic()
                with buffer_lock:
                    for ts, sample in zip(timestamps, samples):
                        # sample is a list — index 0 is typically ECG channel
                        # Adjust the index to match your OpenSignals channel layout
                        ecg_buffer.append((now, sample[0]))

                    # Evict samples older than the window we care about
                    cutoff = now - MAX_BUFFER_SECONDS
                    while ecg_buffer and ecg_buffer[0][0] < cutoff:
                        ecg_buffer.popleft()
    except Exception as e:
        print(f"LSL worker error: {e}")
        inlet.close_stream()


# ---------------------------------------------------------------------------
# BPM calculation thread — same logic, now reads from ecg_buffer
# ---------------------------------------------------------------------------
def bpm_worker():
    global current_bpm
    import neurokit2 as nk

    while True:
        time.sleep(0.2)

        with buffer_lock:
            if len(ecg_buffer) < SAMPLING_RATE * 2:
                # Not enough data yet
                continue
            times, values = zip(*ecg_buffer)

        times = np.array(times)
        values = np.array(values)

        # Only analyse the most recent WINDOW_SECONDS of data
        now = times[-1]
        mask = times >= (now - WINDOW_SECONDS)
        window_values = values[mask]

        if len(window_values) < SAMPLING_RATE:
            continue

        try:
            _, info = nk.ecg_process(window_values, sampling_rate=SAMPLING_RATE)
            rpeaks_idx = info["ECG_R_Peaks"]

            if len(rpeaks_idx) >= 2:
                # Convert peak indices → monotonic timestamps
                rpeak_times = times[mask][rpeaks_idx]
                rr_intervals = np.diff(rpeak_times)
                mean_rr = np.mean(rr_intervals)
                bpm = round(60.0 / mean_rr, 2)

                with bpm_lock:
                    current_bpm = bpm

        except Exception as e:
            print(f"BPM calculation error: {e}")


threading.Thread(target=lsl_worker, daemon=True).start()
threading.Thread(target=bpm_worker, daemon=True).start()


@app.get("/bpm")
def get_bpm():
    with bpm_lock:
        return {"bpm": current_bpm}


# ---------------------------------------------------------------------------
# Server runner  (runs uvicorn in the same process on a background thread)
# ---------------------------------------------------------------------------

server_thread = None
uvicorn_server = None   # uvicorn.Server instance so we can stop it cleanly


def run_server():
    global uvicorn_server, start_time
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="error")
    uvicorn_server = uvicorn.Server(config)
    start_time = time.monotonic()
    uvicorn_server.run()          # blocks until server.should_exit is True


def start_server():
    global server_thread
    if server_thread and server_thread.is_alive():
        return
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()


def stop_server():
    global uvicorn_server, start_time
    if uvicorn_server:
        uvicorn_server.should_exit = True
    start_time = None


# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------

class App(tk.Tk):
    POLL_MS = 500          # how often the GUI refreshes BPM / status

    # colour palette
    BG          = "#1a1a2e"
    PANEL       = "#16213e"
    ACCENT      = "#0f3460"
    GREEN       = "#4ecca3"
    RED         = "#e94560"
    TEXT_LIGHT  = "#eaeaea"
    TEXT_DIM    = "#888888"

    def __init__(self):
        super().__init__()
        self.title("BioSignal Server")
        self.resizable(False, False)
        self.configure(bg=self.BG)

        self._running = False
        self._build_ui()
        self._poll()

        # graceful close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        pad = dict(padx=20, pady=10)

        # --- title bar ---
        header = tk.Frame(self, bg=self.ACCENT)
        header.pack(fill="x")
        tk.Label(
            header, text="  BioSignal Server", bg=self.ACCENT,
            fg=self.TEXT_LIGHT, font=("Helvetica", 13, "bold"),
            anchor="w", pady=10
        ).pack(fill="x")

        # --- status row ---
        status_frame = tk.Frame(self, bg=self.BG)
        status_frame.pack(fill="x", padx=20, pady=(16, 4))

        tk.Label(status_frame, text="Status", bg=self.BG,
                 fg=self.TEXT_DIM, font=("Helvetica", 9)).pack(side="left")

        self._dot = tk.Label(status_frame, text="●", bg=self.BG,
                             fg=self.RED, font=("Helvetica", 14))
        self._dot.pack(side="left", padx=(8, 4))

        self._status_label = tk.Label(
            status_frame, text="Stopped", bg=self.BG,
            fg=self.RED, font=("Helvetica", 10, "bold")
        )
        self._status_label.pack(side="left")

        # --- BPM display ---
        bpm_frame = tk.Frame(self, bg=self.PANEL, bd=0)
        bpm_frame.pack(fill="x", padx=20, pady=10, ipady=16)

        tk.Label(bpm_frame, text="LIVE BPM", bg=self.PANEL,
                 fg=self.TEXT_DIM, font=("Helvetica", 8, "bold")).pack()

        self._bpm_label = tk.Label(
            bpm_frame, text="--", bg=self.PANEL,
            fg=self.GREEN, font=("Helvetica", 48, "bold")
        )
        self._bpm_label.pack()

        tk.Label(bpm_frame, text="beats per minute", bg=self.PANEL,
                 fg=self.TEXT_DIM, font=("Helvetica", 8)).pack()

        # --- endpoint info ---
        info_frame = tk.Frame(self, bg=self.BG)
        info_frame.pack(fill="x", padx=20, pady=(0, 10))

        local_ip = get_local_ip()
        endpoint = f"http://{local_ip}:8000/bpm"
        
        tk.Label(info_frame, text="Endpoint:", bg=self.BG,
                 fg=self.TEXT_DIM, font=("Helvetica", 9)).pack(side="left")
        tk.Label(info_frame, text=f"  {endpoint}",
                 bg=self.BG, fg=self.TEXT_LIGHT,
                 font=("Courier", 9)).pack(side="left")

        # --- buttons ---
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=(4, 20), padx=20, fill="x")

        btn_cfg = dict(
            font=("Helvetica", 11, "bold"),
            relief="flat", cursor="hand2",
            width=10, pady=8
        )

        self._start_btn = tk.Button(
            btn_frame, text="▶  Start",
            bg=self.GREEN, fg=self.BG,
            activebackground="#3ab88f", activeforeground=self.BG,
            command=self._on_start, **btn_cfg
        )
        self._start_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self._stop_btn = tk.Button(
            btn_frame, text="■  Stop",
            bg=self.RED, fg=self.TEXT_LIGHT,
            activebackground="#c73a52", activeforeground=self.TEXT_LIGHT,
            state="disabled", command=self._on_stop, **btn_cfg
        )
        self._stop_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

    # ----------------------------------------------------------- callbacks --

    def _on_start(self):
        self._running = True
        start_server()
        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._set_status("Running", self.GREEN)

    def _on_stop(self):
        self._running = False
        stop_server()
        self._start_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._bpm_label.config(text="--")
        self._set_status("Stopped", self.RED)

    def _on_close(self):
        stop_server()
        self.destroy()

    # ---------------------------------------------------------------- poll --

    def _poll(self):
        """Refresh the BPM display every POLL_MS milliseconds."""
        if self._running:
            with lock:
                bpm = current_bpm
            self._bpm_label.config(text=f"{bpm:.1f}" if bpm else "--")

        self.after(self.POLL_MS, self._poll)

    # --------------------------------------------------------------- utils --

    def _set_status(self, text, colour):
        self._dot.config(fg=colour)
        self._status_label.config(text=text, fg=colour)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    App().mainloop()