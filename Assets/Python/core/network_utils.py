"""
core/network_utils.py
_____________________
Small networking helpers shared by the server and GUI.
"""

import socket


def get_local_ip() -> str:
    """Return the machine's primary LAN IPv4 address, fallback to loopback."""
    try:
        ip_addresses = socket.gethostbyname_ex(socket.gethostname())[2]
        filtered_ips = [
            ip for ip in ip_addresses
            if not ip.startswith("127.")        #loopback
            and not ip.startswith("169.254.")]  #link-local
        first_ip = filtered_ips[:1]
        return first_ip[0]
    except Exception:
        return "127.0.0.1"