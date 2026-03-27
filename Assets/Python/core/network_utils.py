"""
core/network_utils.py
─────────────────────
Small networking helpers shared by the server and GUI.
"""

import socket


def get_local_ip() -> str:
    """Return the machine's primary LAN IPv4 address, fallback to loopback."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"