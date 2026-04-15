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
from pylsl import StreamInlet, resolve_streams, StreamInfo, StreamOutlet

DEBUG  = True
# Close Console Window after startup
if not DEBUG and sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# ---------------------------------------------------------------------------
# Thread-safe log queue — workers push strings, GUI drains it, kind of
# ---------------------------------------------------------------------------
log_queue = collections.deque(maxlen=200)
log_lock = threading.Lock()

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)                          # still visible if console is open
    with log_lock:
        log_queue.append(line)


# Get IPv4 adress
def get_local_ip():
    try:
        ip_addresses = socket.gethostbyname_ex(socket.gethostname())[2]
        filtered_ips = [
            ip for ip in ip_addresses 
            if not ip.startswith("127.") #loopback
            and not ip.startswith("169.254.")] #link-local
        first_ip = filtered_ips[:1]
        return(first_ip[0])
        #s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #s.connect(("8.8.8.8", 80))
        #ip = s.getsockname()[0]
        #s.close()
        #return ip
    except Exception:
        return "127.0.0.1"

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI()

SAMPLING_RATE = 1000
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
# LSL output stream definition
# ---------------------------------------------------------------------------

outStreamInfo = StreamInfo('ToolMarkerStream', 'Markers', 1, 0, 'string', 'testStream')

outlet = StreamOutlet(outStreamInfo)

# ---------------------------------------------------------------------------
# LSL input thread
# ---------------------------------------------------------------------------
def lsl_worker():
    log("LSL worker started. Searching for OpenSignals stream...")
    try:
        streams = resolve_streams(wait_time=2.0)
    except Exception as e:
        log(f"resolve_streams() failed: {e}")
        return
    
    log(f"Found {len(streams)} stream(s) on the network:")
    for s in streams:
        log(f"  • name='{s.name()}'  type='{s.type()}'  "
            f"channels={s.channel_count()}  rate={s.nominal_srate()} Hz")

    os_streams = [s for s in streams if s.name() == "OpenSignals"]

    if not os_streams:
        log("ERROR: No 'OpenSignals' stream found. Is OpenSignals running and streaming?")
        return
    
    log(f"Connecting to '{os_streams[0].name()}' ...")
    try:
        inlet = StreamInlet(os_streams[0])
    except Exception as e:
        log(f"StreamInlet() failed: {e}")
        return
    else:
        outlet.push_sample(['Stream Started'])

    # --- diagnostic: try a single blocking pull first ---
    log("Waiting for first sample (blocking, 5s timeout)...")
    sample, ts = inlet.pull_sample(timeout=5.0)
    if sample is None:
        log("ERROR: No sample received after 5s. Stream is not sending data.")
        return
    log(f"First sample received: ts={ts:.3f}  values={sample}")
    
    log("Connected. Ingesting samples...")
    sample_count = 0
    last_report = time.monotonic()
    
    try:
        while True:
            # pull_chunk is more efficient than pull_sample in a tight loop
            samples, timestamps = inlet.pull_chunk(timeout=1.0, max_samples=32)
            
            now = time.monotonic()
                
            # Report every second regardless of whether data arrived
            if now - last_report >= 1.0:
                with buffer_lock:
                    buf_len = len(ecg_buffer)
                log(f"LSL tick — chunk_size={len(timestamps)}  "
                    f"total_samples={sample_count}  buffer={buf_len}")
                last_report = now

            if not timestamps:
                continue

            #temp logging
            if timestamps:
                ch0 = samples[-1][0]
                ch1 = samples[-1][1]
                log(f"ch0={ch0:.2f}  ch1={ch1:.2f}")
                
            with buffer_lock:
                for ts, sample in zip(timestamps, samples):
                    # Adjust the index to match your OpenSignals channel layout probably gonna need to let this be set in GUI?
                    ecg_buffer.append((now, sample[1]))

                # Discard samples older than the window we care about
                cutoff = now - MAX_BUFFER_SECONDS
                while ecg_buffer and ecg_buffer[0][0] < cutoff:
                    ecg_buffer.popleft()

                sample_count += len(timestamps)

    except Exception as e:
        print(f"LSL worker error: {e}")
        inlet.close_stream()


# ---------------------------------------------------------------------------
# BPM calculation thread
# ---------------------------------------------------------------------------
def bpm_worker():
    global current_bpm
    import neurokit2 as nk

    while True:
        time.sleep(0.2)

        with buffer_lock:
            buf_len = len(ecg_buffer)
            if buf_len < SAMPLING_RATE * 2:
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
                
                log(f"BPM: {bpm}  (R-peaks={len(rpeaks_idx)}  "
                    f"mean_RR={mean_rr*1000:.1f}ms)")

            else:
                log(f"BPM: not enough R-peaks detected ({len(rpeaks_idx)})")

        except Exception as e:
            log(f"BPM calculation error: {e}")


threading.Thread(target=lsl_worker, daemon=True).start()
threading.Thread(target=bpm_worker, daemon=True).start()


@app.get("/bpm")
def get_bpm():
    with bpm_lock:
        return {"bpm": current_bpm}


# ---------------------------------------------------------------------------
# Server runner, same process, background thread
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
    log("FastAPI server started on port 8000")
    uvicorn_server.run()          # blocks until server.should_exit is True


def start_server():
    global server_thread
    if server_thread and server_thread.is_alive():
        return
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    outlet.push_sample(['Server Start'])


def stop_server():
    global uvicorn_server, start_time
    if uvicorn_server:
        uvicorn_server.should_exit = True
    start_time = None
    log("Server stopped.")
    outlet.push_sample(['Server Stop'])


# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------

class App(tk.Tk):
    POLL_MS = 500          # how often the GUI refreshes BPM / status
    LOG_POLL_MS = 300

    # colour palette
    BG          = "#1a1a2e"
    PANEL       = "#16213e"
    ACCENT      = "#0f3460"
    GREEN       = "#4ecca3"
    RED         = "#e94560"
    TEXT_LIGHT  = "#eaeaea"
    TEXT_DIM    = "#888888"
    LOG_BG      = "#0d0d1a"
    LOG_FG      = "#7ecfa0"

    def __init__(self):
        super().__init__()
        self.title("BioSignal Server")
        self.resizable(False, False)
        self.configure(bg=self.BG)

        self._running = False
        self._build_ui()
        self._poll()
        self._poll_log()

        # graceful close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----- UI -----------------------------------------------------------

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

        # --- debug log panel (only shown when DEBUG=True) ---
        if DEBUG:
            log_header = tk.Frame(self, bg=self.ACCENT)
            log_header.pack(fill="x", padx=0, pady=(4, 0))
            tk.Label(
                log_header, text="  Debug Log", bg=self.ACCENT,
                fg=self.TEXT_DIM, font=("Helvetica", 8, "bold"),
                anchor="w", pady=4
            ).pack(fill="x")

            log_frame = tk.Frame(self, bg=self.LOG_BG)
            log_frame.pack(fill="both", expand=True, padx=0, pady=0)

            scrollbar = tk.Scrollbar(log_frame)
            scrollbar.pack(side="right", fill="y")

            self._log_text = tk.Text(
                log_frame,
                bg=self.LOG_BG, fg=self.LOG_FG,
                font=("Courier", 8),
                height=12, width=72,
                relief="flat",
                state="disabled",
                yscrollcommand=scrollbar.set,
                wrap="word"
            )
            self._log_text.pack(side="left", fill="both", expand=True, padx=6, pady=4)
            scrollbar.config(command=self._log_text.yview)

            self._last_log_len = 0
        else:
            self._log_text = None

    # ---- callbacks ---------------------------------------------------------

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

    # ---- poll --------------------------------------------------------------

    def _poll(self):
        """Refresh the BPM display every POLL_MS milliseconds."""
        if self._running:
            with bpm_lock:
                bpm = current_bpm
            self._bpm_label.config(text=f"{bpm:.1f}" if bpm else "--")

        self.after(self.POLL_MS, self._poll)

    def _poll_log(self):
        """Drain log_queue into the Text widget."""
        if self._log_text is not None:
            with log_lock:
                current_len = len(log_queue)
                if current_len != self._last_log_len:
                    # Grab only new lines
                    new_lines = list(log_queue)[self._last_log_len:]
                    self._last_log_len = current_len

                    self._log_text.config(state="normal")
                    for line in new_lines:
                        self._log_text.insert("end", line + "\n")
                    self._log_text.see("end")   # auto-scroll
                    self._log_text.config(state="disabled")

        self.after(self.LOG_POLL_MS, self._poll_log)

    # ----- utils ------------------------------------------------------------

    def _set_status(self, text, colour):
        self._dot.config(fg=colour)
        self._status_label.config(text=text, fg=colour)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    App().mainloop()