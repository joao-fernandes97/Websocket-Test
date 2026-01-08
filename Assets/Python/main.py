import time
import threading
import neurokit2 as nk
import numpy as np
from fastapi import FastAPI

app = FastAPI()

# Config
SAMPLING_RATE = 250
WINDOW_SECONDS = 5

# Simulated ECG
ecg_signal = nk.ecg_simulate(duration=120, sampling_rate=SAMPLING_RATE)
signals, info = nk.ecg_process(ecg_signal, sampling_rate=SAMPLING_RATE)

rpeaks = info["ECG_R_Peaks"]
rpeak_times = rpeaks / SAMPLING_RATE
signal_duration = rpeak_times[-1]

# Shared State
current_bpm = 0.0
lock = threading.Lock()

start_time = time.monotonic()

#background processing loop
def bpm_worker():
    global current_bpm

    while True:
        elapsed = time.monotonic() - start_time

        #peaks that have already happened
        recent_peaks = rpeak_times[rpeak_times <= elapsed]

        #keep only peaks in the window
        recent_peaks = recent_peaks[
            recent_peaks >= elapsed-WINDOW_SECONDS
        ]

        if len(recent_peaks) >= 2:
            rr_intervals = np.diff(recent_peaks)
            mean_rr = np.mean(rr_intervals)
            bpm = 60.0/mean_rr
        else:
            bpm = current_bpm #old latest value if we cant compute a new one

        with lock:
            current_bpm = round(float(bpm), 2)

        time.sleep(0.2) # 5Hz processing rate

#start thread
threading.Thread(target=bpm_worker, daemon=True).start()

#REST server
@app.get("/bpm")
def get_bpm():
    with lock:
        return {"bpm": current_bpm}

