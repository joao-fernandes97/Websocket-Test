"""
processors/bpm_processor.py
───────────────────────────
Reads ECG samples from a BaseSignalSource, detects R-peaks with NeuroKit2,
and computes mean heart rate (BPM).

Exposes:
  GET /bpm  →  {"bpm": 72.3}

GUI:  BPMPanel (gui/panels/bpm_panel.py)
"""

import threading
import time

import neurokit2 as nk
import numpy as np

from core.logging_utils import log
from processors.base import BaseProcessor
from signals.base import BaseSignalSource


class BPMProcessor(BaseProcessor):
    """ECG → BPM via NeuroKit2 R-peak detection."""

    name = "BPM"

    def __init__(
        self,
        source: BaseSignalSource,
        window_seconds: float = 5.0,
        poll_interval:  float = 0.2,
    ) -> None:
        self._source        = source
        self._window_secs   = window_seconds
        self._poll_interval = poll_interval

        self._bpm:  float          = 0.0
        self._lock: threading.Lock = threading.Lock()

        self._thread:     threading.Thread | None = None
        self._stop_event: threading.Event         = threading.Event()

    # Public metric

    @property
    def bpm(self) -> float:
        with self._lock:
            return self._bpm

    # BaseProcessor

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="bpm-processor"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def get_routes(self) -> list[tuple[str, callable]]:
        return [("/bpm", self._api_bpm)]

    def create_panel(self, parent):
        from gui.panels.bpm_panel import BPMPanel
        return BPMPanel(parent, self)

    # API handler

    def _api_bpm(self) -> dict:
        return {"bpm": self.bpm}

    # Background worker

    def _worker(self) -> None:
        sr = self._source.sampling_rate

        while not self._stop_event.is_set():
            time.sleep(self._poll_interval)

            # Snapshot the buffer under the lock, then release immediately
            with self._source.buffer_lock:
                if len(self._source.buffer) < sr * 2:
                    continue
                times, values = zip(*self._source.buffer)

            times  = np.array(times)
            values = np.array(values)

            # Analyse only the most recent window
            now  = times[-1]
            mask = times >= (now - self._window_secs)
            window_values = values[mask]

            if len(window_values) < sr:
                continue

            try:
                _, info = nk.ecg_process(window_values, sampling_rate=sr)
                rpeaks_idx = info["ECG_R_Peaks"]

                if len(rpeaks_idx) >= 2:
                    rpeak_times  = times[mask][rpeaks_idx]
                    rr_intervals = np.diff(rpeak_times)
                    mean_rr      = np.mean(rr_intervals)
                    bpm          = round(60.0 / mean_rr, 2)

                    with self._lock:
                        self._bpm = bpm

                    log(
                        f"[BPMProcessor] BPM={bpm}"
                        f"  R-peaks={len(rpeaks_idx)}"
                        f"  mean_RR={mean_rr * 1000:.1f} ms"
                    )
                else:
                    log(f"[BPMProcessor] not enough R-peaks ({len(rpeaks_idx)})")

            except Exception as e:
                log(f"[BPMProcessor] error: {e}")