"""
processors/rmssd_processor.py
___________________________
Reads RSP samples from a BaseSignalSource, detects R-peaks with NeuroKit2,
and computes root-mean-squared standard deviation (RMSSD).

Exposes:
  GET /rmssd  →  {"rmssd": 1647.71}

GUI:  RMSSDPanel (gui/panels/rmssd_panel.py)
"""

import threading
import time

import neurokit2 as nk
import numpy as np

from core.logging_utils import log
from processors.base import BaseProcessor
from signals.base import BaseSignalSource


class RMSSDProcessor(BaseProcessor):
    """RRV → RMSSD via NeuroKit2 R-peak detection."""

    name = "RMSSD"

    def __init__(
        self,
        source: BaseSignalSource,
        window_seconds: float = 5.0,
        poll_interval:  float = 0.2,
    ) -> None:
        self._source        = source
        self._window_secs   = window_seconds
        self._poll_interval = poll_interval

        self._rmssd:  float          = 0.0
        self._lock: threading.Lock = threading.Lock()

        self._thread:     threading.Thread | None = None
        self._stop_event: threading.Event         = threading.Event()

    # Public metric

    @property
    def rmssd(self) -> float:
        with self._lock:
            return self._rmssd

    # BaseProcessor

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="rmssd-processor"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def get_routes(self) -> list[tuple[str, callable]]:
        return [("/rmssd", self._api_rmssd)]

    def create_panel(self, parent):
        from gui.panels.rmssd_panel import RMSSDPanel
        return RMSSDPanel(parent, self)

    # API handler

    def _api_rmssd(self) -> dict:
        return {"rmssd": self.rmssd}

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

            #TODO: This isn't working
            try:
                rsp, info = nk.rsp_process(window_values, sampling_rate=sr)
                rpeaks_idx = info["RSP_Peaks"]

                if len(rpeaks_idx) >= 2:
                    rmssd = nk.rsp_rrv(rsp)["RRV_RMSSD"].iloc(0)

                    with self._lock:
                        self.rmssd = rmssd

                    log(
                        f"[RMSSDProcessor] RMSSD={rmssd}"
                        f"  R-peaks={len(rpeaks_idx)}"
                    )
                else:
                    log(f"[RMSSDProcessor] not enough R-peaks ({len(rpeaks_idx)})")

            except Exception as e:
                log(f"[RMSSDProcessor] error: {e}")