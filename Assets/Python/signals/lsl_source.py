"""
signals/lsl_source.py
─────────────────────
Reads from a pylsl stream (default: "OpenSignals") into a ring buffer.

Configurable parameters
───────────────────────
stream_name    — LSL stream name to connect to (must match OpenSignals config)
channel_index  — 0-based index of the channel to ingest (e.g. 1 for ECG on port 2)
sampling_rate  — expected samples/s (used by processors; does not resample)
window_seconds — ring buffer depth in seconds (+ 2 s headroom)

Also owns a LSL marker outlet so lifecycle events can be timestamped in
recordings alongside the raw signal data.
"""

import collections
import threading
import time

from pylsl import StreamInfo, StreamInlet, StreamOutlet, resolve_streams

from core.logging_utils import log
from signals.base import BaseSignalSource


class LSLSignalSource(BaseSignalSource):
    """Ingests one channel of an LSL stream into a time-stamped ring buffer."""

    name = "LSL / OpenSignals"

    def __init__(
        self,
        stream_name: str = "OpenSignals",
        channel_index: int = 1,
        sampling_rate: int = 1000,
        window_seconds: int = 5,
    ) -> None:
        self._stream_name    = stream_name
        self._channel_index  = channel_index
        self._sampling_rate  = sampling_rate
        self._max_buf_secs   = window_seconds + 2

        self._buf:  collections.deque = collections.deque()
        self._lock: threading.Lock    = threading.Lock()

        self._thread:     threading.Thread | None = None
        self._stop_event: threading.Event         = threading.Event()

        # LSL marker outlet — push event labels back to the recording
        _info = StreamInfo(
            "ToolMarkerStream", "Markers", 1, 0, "string", "biosignal_tool"
        )
        self._outlet = StreamOutlet(_info)

    # ── BaseSignalSource ───────────────────────────────────────────────────

    @property
    def sampling_rate(self) -> int:
        return self._sampling_rate

    @property
    def buffer(self) -> collections.deque:
        return self._buf

    @property
    def buffer_lock(self) -> threading.Lock:
        return self._lock

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="lsl-source"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    # ── Marker output ──────────────────────────────────────────────────────

    def push_marker(self, label: str) -> None:
        """Push a timestamped string marker to the LSL outlet."""
        try:
            self._outlet.push_sample([label])
        except Exception as e:
            log(f"[LSLSignalSource] marker push failed: {e}")

    # ── Background worker ──────────────────────────────────────────────────

    def _worker(self) -> None:
        log(f"[LSLSignalSource] Searching for '{self._stream_name}' …")

        try:
            streams = resolve_streams(wait_time=2.0)
        except Exception as e:
            log(f"[LSLSignalSource] resolve_streams() failed: {e}")
            return

        log(f"[LSLSignalSource] Found {len(streams)} stream(s) on the network:")
        for s in streams:
            log(
                f"  • name='{s.name()}'  type='{s.type()}'"
                f"  ch={s.channel_count()}  rate={s.nominal_srate()} Hz"
            )

        targets = [s for s in streams if s.name() == self._stream_name]
        if not targets:
            log(
                f"[LSLSignalSource] ERROR: No '{self._stream_name}' stream found. "
                "Is OpenSignals running and streaming?"
            )
            return

        log(f"[LSLSignalSource] Connecting to '{targets[0].name()}' …")
        try:
            inlet = StreamInlet(targets[0])
        except Exception as e:
            log(f"[LSLSignalSource] StreamInlet() failed: {e}")
            return

        self.push_marker("Stream Started")

        # Diagnostic: block until first sample confirms data is flowing
        log("[LSLSignalSource] Waiting for first sample (5 s timeout) …")
        sample, ts = inlet.pull_sample(timeout=5.0)
        if sample is None:
            log("[LSLSignalSource] ERROR: No sample in 5 s — stream not sending data.")
            return
        log(f"[LSLSignalSource] First sample OK: ts={ts:.3f}  values={sample}")

        log(f"[LSLSignalSource] Ingesting ch[{self._channel_index}] …")
        sample_count = 0
        last_report  = time.monotonic()

        try:
            while not self._stop_event.is_set():
                samples, timestamps = inlet.pull_chunk(timeout=1.0, max_samples=32)
                now = time.monotonic()

                # Periodic diagnostic log
                if now - last_report >= 1.0:
                    with self._lock:
                        buf_len = len(self._buf)
                    log(
                        f"[LSLSignalSource] tick — chunk={len(timestamps)}"
                        f"  total={sample_count}  buf={buf_len}"
                    )
                    last_report = now

                if not timestamps:
                    continue

                # Temp channel value log (remove when channel layout confirmed)
                log(
                    f"[LSLSignalSource] ch0={samples[-1][0]:.2f}"
                    f"  ch1={samples[-1][1]:.2f}"
                )

                with self._lock:
                    for _ts, sample in zip(timestamps, samples):
                        self._buf.append((now, sample[self._channel_index]))

                    # Trim samples older than our window
                    cutoff = now - self._max_buf_secs
                    while self._buf and self._buf[0][0] < cutoff:
                        self._buf.popleft()

                    sample_count += len(timestamps)

        except Exception as e:
            log(f"[LSLSignalSource] Worker error: {e}")
        finally:
            inlet.close_stream()
            log("[LSLSignalSource] Stream closed.")