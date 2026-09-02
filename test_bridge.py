#!/usr/bin/env python3
"""
Enhanced Connectivity Test for Snap7 Server.
Tests connection, read/write of multiple data types, and includes retry logic.
"""
import sys
import configparser
import argparse
import time
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import fork_bridge as fb
except ImportError as e:
    print(f"[ERROR] Could not import fork_bridge: {e}", flush=True)
    sys.exit(1)

# Constants for S7 areas (DB = 0x84)
S7_AREA_DB = 0x84

DEFAULT_IP = "127.0.0.1"
DEFAULT_RACK = 0
DEFAULT_SLOT = 1
DEFAULT_PORT = 102

def load_config():
    config_file = Path(__file__).parent / "config.ini"
    if config_file.exists():
        config = configparser.ConfigParser()
        config.read(config_file)
        if config.has_section("PLC"):
            ip = config.get("PLC", "ip", fallback=DEFAULT_IP)
            rack = config.getint("PLC", "rack", fallback=DEFAULT_RACK)
            slot = config.getint("PLC", "slot", fallback=DEFAULT_SLOT)
            port = config.getint("PLC", "port", fallback=DEFAULT_PORT)
            return ip, rack, slot, port
    return DEFAULT_IP, DEFAULT_RACK, DEFAULT_SLOT, DEFAULT_PORT

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip")
    parser.add_argument("--rack", type=int)
    parser.add_argument("--slot", type=int)
    parser.add_argument("--port", type=int)
    return parser.parse_args()

def retry_operation(func, max_retries=3, delay=0.5):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay * (2 ** attempt))
    return None

def find_lowlevel_methods(client):
    """
    Try to locate a write and read method that can handle raw bytes to/from a DB.
    Returns a tuple (write_func, read_func) or raises RuntimeError.
    """
    # List of possible method names (and paths) to try
    candidates = [
        # Direct methods
        ('db_write', 'db_read'),
        ('write_area', 'read_area'),
        ('write_db', 'read_db'),
        ('write', 'read'),      # might be generic but check signature
        # If client wraps a snap7 client
        ('_client.db_write', '_client.db_read'),
        ('_client.write_area', '_client.read_area'),
    ]

    for write_name, read_name in candidates:
        # Try to get the callable
        try:
            if '.' in write_name:
                parts = write_name.split('.')
                obj = client
                for part in parts:
                    obj = getattr(obj, part)
                write_func = obj
            else:
                write_func = getattr(client, write_name)

            if '.' in read_name:
                parts = read_name.split('.')
                obj = client
                for part in parts:
                    obj = getattr(obj, part)
                read_func = obj
            else:
                read_func = getattr(client, read_name)

            # Quick test: we don't call them, just assume they exist
            return write_func, read_func
        except AttributeError:
            continue

    # If we get here, no method found – print available methods for debugging
    print("[DEBUG] Available methods on ForkClient:")
    for attr in dir(client):
        if not attr.startswith('_'):
            print(f"  {attr}")
    raise RuntimeError("No suitable low-level read/write methods found. "
                       "Please check the available methods and adjust the patch accordingly.")

def patch_client(client):
    """
    Add typed read/write methods (INT, DINT, BOOL) using the found low-level methods.
    """
    write_raw, read_raw = find_lowlevel_methods(client)

    # Determine if the method expects (area, db, offset, data) or (db, offset, data)
    # We'll try to call with a dummy call to see which signature works.
    # Since we don't want to actually write, we'll use a try/except with a small test.
    # But we can't easily test without side effects – instead we'll define both patterns
    # and let the user configure if needed, or we can just use the (area, db, offset, data) 
    # pattern as that is standard for write_area and db_write often takes (db, offset, data).
    # We'll try (db, offset, data) first because it's common for db_write.
    # If that fails, we'll fall back to (area, db, offset, data).
    
    # We'll define wrapper functions that try the (db, offset, data) signature.
    def write_db(db, offset, data):
        try:
            # Try db_write style (db, offset, data)
            return write_raw(db, offset, data)
        except TypeError:
            # Fallback to write_area style (area, db, offset, data)
            return write_raw(S7_AREA_DB, db, offset, data)

    def read_db(db, offset, size):
        try:
            return read_raw(db, offset, size)
        except TypeError:
            return read_raw(S7_AREA_DB, db, offset, size)

    # Define typed methods
    def write_int(db, offset, value):
        data = struct.pack('>h', value)
        return write_db(db, offset, data)

    def read_int(db, offset):
        data = read_db(db, offset, 2)
        return struct.unpack('>h', data)[0]

    def write_dint(db, offset, value):
        data = struct.pack('>i', value)
        return write_db(db, offset, data)

    def read_dint(db, offset):
        data = read_db(db, offset, 4)
        return struct.unpack('>i', data)[0]

    def write_bool(db, offset, value):
        data = bytes([1 if value else 0])
        return write_db(db, offset, data)

    def read_bool(db, offset):
        data = read_db(db, offset, 1)
        return data[0] != 0

    client.write_int = write_int
    client.read_int = read_int
    client.write_dint = write_dint
    client.read_dint = read_dint
    client.write_bool = write_bool
    client.read_bool = read_bool

    return client

def main() -> int:
    print("=" * 60, flush=True)
    print("S7 Bridge – Enhanced Connectivity Test", flush=True)
    print("=" * 60, flush=True)

    print("\n[1] Checking Snap7 library...", flush=True)
    if not fb.SNAP7_AVAILABLE:
        print("   [FAIL] python-snap7 is NOT installed or not found.", flush=True)
        print("   Please install: pip install python-snap7", flush=True)
        print("   Also ensure the Snap7 DLL is in your PATH.", flush=True)
        return 1
    print("   [OK] python-snap7 is available.", flush=True)

    args = parse_args()
    cfg_ip, cfg_rack, cfg_slot, cfg_port = load_config()
    ip = args.ip or cfg_ip
    rack = args.rack if args.rack is not None else cfg_rack
    slot = args.slot if args.slot is not None else cfg_slot
    port = args.port if args.port is not None else cfg_port

    print(f"\n[2] Target PLC: {ip}:{port} | Rack: {rack} | Slot: {slot}", flush=True)

    print(f"\n[3] Connecting to {ip}:{port}...", flush=True)
    client = fb.ForkClient(send_timeout_ms=2000, recv_timeout_ms=2000)

    # Patch missing typed methods
    try:
        client = patch_client(client)
        print("   [OK] Client patched with typed methods.", flush=True)
    except Exception as e:
        print(f"   [FAIL] Could not patch client: {e}", flush=True)
        return 1

    # Retry connection
    def connect():
        return client.connect(ip, rack, slot, port)

    try:
        connected = retry_operation(connect, max_retries=3)
        if not connected:
            print("   [FAIL] Connection FAILED after retries.", flush=True)
            return 1
        print("   [OK] Connected successfully.", flush=True)
    except Exception as e:
        print(f"   [FAIL] Connection failed: {e}", flush=True)
        return 1

    # Test each data type
    test_cases = [
        ("REAL", fb.DB1_TEMP_OFFSET, 123.456, lambda: client.write_real(1, fb.DB1_TEMP_OFFSET, 123.456),
         lambda: client.read_real(1, fb.DB1_TEMP_OFFSET)),
        ("INT", 10, 32767, lambda: client.write_int(1, 10, 32767),
         lambda: client.read_int(1, 10)),
        ("DINT", 20, 2147483647, lambda: client.write_dint(1, 20, 2147483647),
         lambda: client.read_dint(1, 20)),
        ("BOOL", 30, True, lambda: client.write_bool(1, 30, True),
         lambda: client.read_bool(1, 30)),
    ]

    print("\n[4] Testing read/write operations...", flush=True)
    all_passed = True
    for name, offset, value, write_func, read_func in test_cases:
        print(f"\n   Testing {name} at offset {offset}:", flush=True)
        try:
            # Write with retry
            retry_operation(lambda: write_func(), max_retries=2)
            print("      [OK] Write OK", flush=True)
        except Exception as e:
            print(f"      [FAIL] Write failed: {e}", flush=True)
            all_passed = False
            continue

        try:
            read_val = retry_operation(lambda: read_func(), max_retries=2)
            print(f"      Read value: {read_val} (expected {value})", flush=True)
            if isinstance(value, float):
                if abs(read_val - value) < 0.001:
                    print("      [OK] Match", flush=True)
                else:
                    print("      [FAIL] Mismatch", flush=True)
                    all_passed = False
            else:
                if read_val == value:
                    print("      [OK] Match", flush=True)
                else:
                    print("      [FAIL] Mismatch", flush=True)
                    all_passed = False
        except Exception as e:
            print(f"      [FAIL] Read failed: {e}", flush=True)
            all_passed = False

    print("\n[5] Cleaning up...", flush=True)
    client.close()
    print("[OK] Done – clean shutdown!", flush=True)

    if not all_passed:
        print("\n[WARN] Some tests failed. Check the server configuration and logs.", flush=True)
        return 1
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"UNHANDLED EXCEPTION: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)