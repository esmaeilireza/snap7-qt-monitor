#!/usr/bin/env python
"""
Production-Grade Snap7 Server - with dynamic memory updates.
"""

import argparse
import json
import logging
import signal
import sys
import time
import struct
import threading
from pathlib import Path
from typing import Dict, Optional

import yaml
import snap7
from snap7 import server
from snap7.type import SrvArea, SrvEvent

# Import our sensor simulators
try:
    from sensor_simulator import TemperatureSensorSimulator, SystemMetricsSimulator
except ImportError:
    # Fallback: define dummy simulators if not available (should not happen)
    class TemperatureSensorSimulator:
        def __init__(self, setpoint=65.5):
            self.setpoint = setpoint
            self._last = setpoint
        def read(self):
            import random, math, time
            self._last = self.setpoint + math.sin(time.time()) * 0.5 + random.gauss(0, 0.1)
            return self._last
        def set_setpoint(self, val):
            self.setpoint = float(val)

    class SystemMetricsSimulator:
        def __init__(self, cpu_base=12.0, mem_base=45.0):
            self.cpu_base = cpu_base
            self.mem_base = mem_base
        def get_metrics(self):
            import random, math, time
            return {
                "cpu": self.cpu_base + math.sin(time.time() * 0.5) * 5 + random.gauss(0, 0.5),
                "memory": self.mem_base + math.cos(time.time() * 0.3) * 3 + random.gauss(0, 0.5)
            }

# ----------------------------------------------------------------------
# S7 Area Constants (mapping to SrvArea enum)
# ----------------------------------------------------------------------
S7_AREA_DB = SrvArea.DB
S7_AREA_PE = SrvArea.PE
S7_AREA_PA = SrvArea.PA
S7_AREA_MK = SrvArea.MK

# Offsets in DB1 (matching fork_bridge.py)
DB1_TEMP_OFFSET = 0
DB1_CPU_OFFSET = 4
DB1_RAM_OFFSET = 8
DB1_SETPOINT_OFFSET = 12
DB1_HEARTBEAT_OFFSET = 16

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"

def setup_logging(verbose: bool = False, log_file: Optional[str] = None):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FMT))
    root_logger.addHandler(console)
    if log_file:
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        fh.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FMT))
        root_logger.addHandler(fh)
    return logging.getLogger("Snap7Server")

def get_logger():
    return logging.getLogger("Snap7Server")

logger = get_logger()

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
DEFAULT_CONFIG = {
    "server": {"port": 102, "rack": 0, "slot": 1, "authentication": {"enabled": False, "token": ""}},
    "memory": {"inputs_size": 128, "outputs_size": 128, "flags_size": 256,
               "db_blocks": {"1": {"size": 1024, "init": {"0": {"type": "real", "value": 123.45}}}}},
    "persistence": {"enabled": False, "file": "plc_state.json"},
    "logging": {"file": "snap7_server.log"},
    "dynamics": {"enabled": True, "update_interval_ms": 500}  # NEW SECTION
}

def load_config(config_path: Optional[str] = None) -> dict:
    config = DEFAULT_CONFIG.copy()
    if config_path and Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
            def merge(base, updates):
                for k, v in updates.items():
                    base_key = str(k) if not isinstance(k, str) else k
                    if base_key in base and isinstance(base[base_key], dict) and isinstance(v, dict):
                        merge(base[base_key], v)
                    else:
                        base[base_key] = v
            merge(config, user_config)
    return config

# ----------------------------------------------------------------------
# Memory Manager
# ----------------------------------------------------------------------
class MemoryManager:
    def __init__(self, config: dict):
        self.inputs = bytearray(config["memory"]["inputs_size"])
        self.outputs = bytearray(config["memory"]["outputs_size"])
        self.flags = bytearray(config["memory"]["flags_size"])
        self.dbs: Dict[int, bytearray] = {}

        for db_num_str, db_cfg in config["memory"]["db_blocks"].items():
            db_num = int(db_num_str)
            size = db_cfg.get("size", 1024)
            self.dbs[db_num] = bytearray(size)
            for offset_str, value_cfg in db_cfg.get("init", {}).items():
                offset = int(offset_str)
                typ = value_cfg.get("type", "byte")
                val = value_cfg["value"]
                if typ == "real":
                    struct.pack_into('>f', self.dbs[db_num], offset, float(val))
                elif typ == "int":
                    struct.pack_into('>h', self.dbs[db_num], offset, int(val))
                elif typ == "dint":
                    struct.pack_into('>i', self.dbs[db_num], offset, int(val))
                elif typ == "byte":
                    self.dbs[db_num][offset] = int(val)
                else:
                    get_logger().warning(f"Unsupported type {typ} for DB{db_num} offset {offset}")

    def get_db(self, db_num: int) -> bytearray:
        if db_num not in self.dbs:
            self.dbs[db_num] = bytearray(1024)
            get_logger().info(f"Auto-created DB{db_num}")
        return self.dbs[db_num]

    def read(self, area: int, start: int, count: int, db_num: int = 0) -> bytes:
        if area == S7_AREA_DB:
            db = self.get_db(db_num)
            if start + count > len(db):
                db.extend(b'\x00' * (start + count - len(db)))
            return db[start:start+count]
        elif area == S7_AREA_PE:
            return self.inputs[start:start+count]
        elif area == S7_AREA_PA:
            return self.outputs[start:start+count]
        elif area == S7_AREA_MK:
            return self.flags[start:start+count]
        else:
            raise ValueError(f"Unsupported read area: {area:#x}")

    def write(self, area: int, start: int, data: bytes, db_num: int = 0):
        if area == S7_AREA_DB:
            db = self.get_db(db_num)
            end = start + len(data)
            if end > len(db):
                db.extend(b'\x00' * (end - len(db)))
            db[start:end] = data
        elif area == S7_AREA_PE:
            self.inputs[start:start+len(data)] = data
        elif area == S7_AREA_PA:
            self.outputs[start:start+len(data)] = data
        elif area == S7_AREA_MK:
            self.flags[start:start+len(data)] = data
        else:
            raise ValueError(f"Unsupported write area: {area:#x}")

    def save_state(self, filepath: str):
        state = {
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "flags": list(self.flags),
            "dbs": {str(k): list(v) for k, v in self.dbs.items()}
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        get_logger().info(f"State saved to {filepath}")

    def load_state(self, filepath: str):
        if not Path(filepath).exists():
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)
        self.inputs = bytearray(state.get("inputs", self.inputs))
        self.outputs = bytearray(state.get("outputs", self.outputs))
        self.flags = bytearray(state.get("flags", self.flags))
        for db_num_str, db_data in state.get("dbs", {}).items():
            self.dbs[int(db_num_str)] = bytearray(db_data)
        get_logger().info(f"State loaded from {filepath}")

    def register_with_server(self, srv: server.Server):
        """Register all memory areas with the Snap7 server."""
        log = get_logger()
        for db_num, db_data in self.dbs.items():
            srv.register_area(SrvArea.DB, db_num, db_data)
            log.info(f"Registered DB{db_num} (size={len(db_data)})")
        srv.register_area(SrvArea.PE, 0, self.inputs)
        log.info(f"Registered PE (Inputs, size={len(self.inputs)})")
        srv.register_area(SrvArea.PA, 0, self.outputs)
        log.info(f"Registered PA (Outputs, size={len(self.outputs)})")
        srv.register_area(SrvArea.MK, 0, self.flags)
        log.info(f"Registered MK (Flags, size={len(self.flags)})")

# ----------------------------------------------------------------------
# Simulated PLC Server with dynamic updates
# ----------------------------------------------------------------------
class SimulatedPLC:
    def __init__(self, config: dict, memory: MemoryManager):
        self.memory = memory
        self.config = config
        self._persist_file = config["persistence"].get("file")
        self._persist_enabled = config["persistence"].get("enabled", False)
        self._server = server.Server(log=True)
        self._running = False
        self._update_thread = None
        self._dynamic_enabled = config.get("dynamics", {}).get("enabled", True)
        self._update_interval = config.get("dynamics", {}).get("update_interval_ms", 500) / 1000.0

        if self._persist_enabled and self._persist_file and Path(self._persist_file).exists():
            self.memory.load_state(self._persist_file)

        # Register all memory areas with the server
        self.memory.register_with_server(self._server)

        # Set up event callbacks for logging (not for data handling)
        self._server.set_events_callback(self._on_event)
        self._server.set_read_events_callback(self._on_read_event)

        # Create simulator instances for dynamic updates
        if self._dynamic_enabled:
            self._temp_sim = TemperatureSensorSimulator(setpoint=65.5)
            self._sys_sim = SystemMetricsSimulator()
            get_logger().info("Dynamic updates enabled (using sensor simulators)")
        else:
            self._temp_sim = None
            self._sys_sim = None

        get_logger().info(f"PLC ready (rack={config['server']['rack']}, slot={config['server']['slot']})")

    def _on_event(self, event: SrvEvent):
        event_text = self._server.event_text(event)
        get_logger().debug(f"Server event: {event_text} (code={event.EvtCode:#08x})")

    def _on_read_event(self, event: SrvEvent):
        get_logger().debug(f"Read event: code={event.EvtCode:#08x}, params=({event.EvtParam1}, {event.EvtParam2}, {event.EvtParam3}, {event.EvtParam4})")

    def _update_loop(self):
        """Background thread: writes new simulated values to DB1 at regular intervals."""
        get_logger().info("Dynamic update loop started.")
        heartbeat = 0
        while self._running:
            try:
                # Get DB1 bytearray
                db1 = self.memory.get_db(1)
                # Ensure size is at least 17 bytes (offset 16 + 1)
                if len(db1) < 17:
                    db1.extend(b'\x00' * (17 - len(db1)))

                # Read new values from simulators
                temp = self._temp_sim.read()
                metrics = self._sys_sim.get_metrics()
                cpu = metrics["cpu"]
                ram = metrics["memory"]
                setpoint = self._temp_sim.setpoint  # use the setpoint from temp sim

                # Pack into DB1
                struct.pack_into('>f', db1, DB1_TEMP_OFFSET, float(temp))
                struct.pack_into('>f', db1, DB1_CPU_OFFSET, float(cpu))
                struct.pack_into('>f', db1, DB1_RAM_OFFSET, float(ram))
                struct.pack_into('>f', db1, DB1_SETPOINT_OFFSET, float(setpoint))

                # Heartbeat byte
                heartbeat = (heartbeat + 1) % 256
                db1[DB1_HEARTBEAT_OFFSET] = heartbeat

                # Optional: log occasional updates
                # get_logger().debug(f"Updated DB1: temp={temp:.2f}, cpu={cpu:.2f}, ram={ram:.2f}, hb={heartbeat}")

            except Exception as e:
                get_logger().error(f"Error in update loop: {e}")

            time.sleep(self._update_interval)

    def start(self, port: int = 102):
        self._server.start(tcp_port=port)
        self._running = True

        # Start the dynamic update thread if enabled
        if self._dynamic_enabled and self._temp_sim is not None:
            self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self._update_thread.start()
            get_logger().info("Dynamic update thread started.")

    def stop(self):
        self._running = False
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=2.0)
        if self._running and self._persist_enabled and self._persist_file:
            self.memory.save_state(self._persist_file)
        self._server.stop()
        self._running = False

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Path to YAML config")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--no-dynamics", action="store_true", help="Disable dynamic updates")
    args = parser.parse_args()

    config = load_config(args.config)
    log_file = config["logging"].get("file")
    setup_logging(args.verbose, log_file)

    if args.persist:
        config["persistence"]["enabled"] = True
    if args.no_dynamics:
        config["dynamics"]["enabled"] = False

    memory = MemoryManager(config)
    plc = SimulatedPLC(config, memory)

    def signal_handler(sig, frame):
        get_logger().info("Shutting down...")
        plc.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    port = config["server"].get("port", 102)
    try:
        get_logger().info(f"Starting Snap7 server on 0.0.0.0:{port}")
        plc.start(port)
        get_logger().info("Server running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except Exception as e:
        get_logger().error(f"Server error: {e}")
        plc.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()