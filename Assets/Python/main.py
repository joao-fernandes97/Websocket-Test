"""
main.py
_______
Entry point.  Wire signal sources, processors, and the GUI together here.
This file is the only place you need to edit when adding/removing components.
"""

import sys

# Debug / console

DEBUG = True
PORT  = 8000

if not DEBUG and sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Imports

from core import server
from signals.lsl_source import LSLSignalSource
from processors.bpm_processor import BPMProcessor
from processors.rmssd_processor import RMSSDProcessor
from gui.app import App

# Signal sources
# Swap or add sources here
# index 0 in Plux is a timestamp channel

ecg_source = LSLSignalSource(
    stream_name   = "OpenSignals",
    channel_index = 1,        # 0-based; adjust to match device layout
    sampling_rate = 1000,
    window_seconds= 5,
)
ecg_source.start()

rsp_source = LSLSignalSource(
    stream_name   = "OpenSignals",
    channel_index = 2,        # 0-based; adjust to match device layout
    sampling_rate = 1000,
    window_seconds= 5,
)
rsp_source.start()

# Processors
# Each processor contributes:
#   * One or more HTTP routes  (via get_routes())
#   * An optional GUI panel    (via create_panel())

processors = [
    BPMProcessor(ecg_source, window_seconds=5),
    RMSSDProcessor(rsp_source, window_seconds=10),
]

# Register all routes with the shared FastAPI app
for proc in processors:
    for path, handler in proc.get_routes():
        server.register_route(path, handler)
    proc.start()

# LSL lifecycle markers - push to recording whenever the server toggles
server.on_start(lambda: ecg_source.push_marker("Server Start"))
server.on_stop( lambda: ecg_source.push_marker("Server Stop"))

if __name__ == "__main__":
    App(processors=processors, debug=DEBUG, port=PORT).mainloop()