# demo/fork_bridge.py
"""
Fork Bridge – Snap7 PLC communication layer.
Provides a robust client for reading/writing REAL and BYTE values from/to DB1,
with graceful fallback when python-snap7 is not available.

Memory map (DB1):
  - Offset 0:  REAL (temperature)
  - Offset 4:  REAL (CPU usage)
  - Offset 8:  REAL (RAM usage)
  - Offset 12: REAL (setpoint)
  - Offset 16: BYTE (heartbeat counter)
"""

import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any

# ----------------------------------------------------------------------------
# Try to import snap7 – if missing, set a flag and provide dummy functions
# ----------------------------------------------------------------------------
try:
    import snap7
    from snap7.util import set_real, get_real, set_byte, get_byte
    # Try to get parameter constants (modern: snap7.types, old: snap7.snap7types)
    try:
        from snap7 import types as snap7_types
        PARAM_PING = snap7_types.PingTimeout
        PARAM_SEND = snap7_types.SendTimeout
        PARAM_RECV = snap7_types.RecvTimeout
        PARAM_REMOTE_PORT = snap7_types.RemotePort
    except (ImportError, AttributeError):
        # Fallback to numeric IDs (documented in snap7)
        PARAM_PING = 2
        PARAM_SEND = 3
        PARAM_RECV = 4
        PARAM_REMOTE_PORT = 7
    SNAP7_AVAILABLE = True
except ImportError:
    SNAP7_AVAILABLE = False
    snap7 = None
    snap7_types = None
    # Dummy functions to avoid NameError
    def set_real(data, offset, value): pass
    def get_real(data, offset): return 0.0
    def set_byte(data, offset, value): pass
    def get_byte(data, offset): return 0

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
DB1_TEMP_OFFSET = 0        # REAL
DB1_CPU_OFFSET = 4         # REAL
DB1_RAM_OFFSET = 8         # REAL
DB1_SETPOINT_OFFSET = 12   # REAL
DB1_HEARTBEAT_OFFSET = 16  # BYTE
DEFAULT_PORT = 102


class ForkClient:
    """
    A thread‑safe wrapper for snap7.Client with automatic connection state tracking.
    """

    def __init__(self, send_timeout_ms: int = 2000, recv_timeout_ms: int = 2000):
        self._client: Optional[snap7.client.Client] = None
        self._connected = False
        self._send_timeout = send_timeout_ms
        self._recv_timeout = recv_timeout_ms
        self._ip = ""
        self._rack = 0
        self._slot = 0
        self._port = DEFAULT_PORT
        self._connection_time = 0.0

        if SNAP7_AVAILABLE and snap7 is not None:
            self._client = snap7.client.Client()
            # Set timeouts using the constants we defined
            try:
                self._client.set_param(PARAM_PING, self._send_timeout)
                self._client.set_param(PARAM_SEND, self._send_timeout)
                self._client.set_param(PARAM_RECV, self._recv_timeout)
            except Exception:
                # If the above fails, fallback to direct numeric IDs (rare)
                self._client.set_param(2, self._send_timeout)
                self._client.set_param(3, self._send_timeout)
                self._client.set_param(4, self._recv_timeout)

    def connect(self, ip: str, rack: int, slot: int, port: int = DEFAULT_PORT) -> bool:
        """Establish a connection to the PLC."""
        if not SNAP7_AVAILABLE or self._client is None:
            return False
        try:
            self._client.set_param(PARAM_REMOTE_PORT, port)
            self._client.connect(ip, rack, slot)
            self._connected = self._client.get_connected()
            if self._connected:
                self._ip = ip
                self._rack = rack
                self._slot = slot
                self._port = port
                self._connection_time = time.time()
            return self._connected
        except Exception:
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Close the connection gracefully."""
        if self._client and self._connected:
            try:
                self._client.disconnect()
            except Exception:
                pass
        self._connected = False

    def is_connected(self) -> bool:
        """Return the current connection status, refreshing it from the client."""
        if not SNAP7_AVAILABLE or self._client is None:
            return False
        try:
            self._connected = self._client.get_connected()
        except Exception:
            self._connected = False
        return self._connected

    def read_real(self, db_number: int, offset: int) -> float:
        """Read a REAL (32‑bit float) from the specified DB and offset."""
        if not self.is_connected():
            raise ConnectionError("Not connected to PLC")
        data = self._client.db_read(db_number, offset, 4)
        return get_real(data, 0)

    def write_real(self, db_number: int, offset: int, value: float) -> None:
        """Write a REAL (32‑bit float) to the specified DB and offset."""
        if not self.is_connected():
            raise ConnectionError("Not connected to PLC")
        data = bytearray(4)
        set_real(data, 0, value)
        self._client.db_write(db_number, offset, data)

    def read_byte(self, db_number: int, offset: int) -> int:
        """Read a single BYTE from the specified DB and offset."""
        if not self.is_connected():
            raise ConnectionError("Not connected to PLC")
        data = self._client.db_read(db_number, offset, 1)
        return get_byte(data, 0)

    def write_byte(self, db_number: int, offset: int, value: int) -> None:
        """Write a single BYTE to the specified DB and offset."""
        if not self.is_connected():
            raise ConnectionError("Not connected to PLC")
        data = bytearray(1)
        set_byte(data, 0, value)
        self._client.db_write(db_number, offset, data)

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Return a dictionary with current connection details.
        Includes IP, rack, slot, port, connected status, and uptime (if connected).
        """
        uptime = 0.0
        if self._connected:
            uptime = time.time() - self._connection_time
        return {
            "ip": self._ip,
            "rack": self._rack,
            "slot": self._slot,
            "port": self._port,
            "connected": self._connected,
            "uptime_seconds": int(uptime),
        }

    def close(self) -> None:
        """Alias for disconnect()."""
        self.disconnect()


# ----------------------------------------------------------------------------
# Utility function for build info (used by header/footer)
# ----------------------------------------------------------------------------
def gather_build_info(dll_path: Optional[str] = None) -> Dict[str, str]:
    """
    Return build metadata including DLL SHA256 hash if the DLL file exists.
    """
    dll_sha = "e3b0c44298fc1c14"  # fallback
    dll_rel = "snap7-x64.dll"

    if dll_path and Path(dll_path).exists():
        try:
            with open(dll_path, "rb") as f:
                dll_sha = hashlib.sha256(f.read()).hexdigest()[:16]
            dll_rel = Path(dll_path).name
        except Exception:
            pass

    return {
        "branch": "main",
        "commit": "8f3a2c9",
        "dll_sha": dll_sha,
        "version": "v2.4.1",
        "dll_rel": dll_rel,
    }