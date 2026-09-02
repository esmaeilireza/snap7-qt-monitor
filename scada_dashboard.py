#!/usr/bin/env python3
# demo/scada_dashboard.py
"""
S7 SCADA v2.4.1 – Production Industrial Dashboard

"""

import sys
import configparser
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

# ============================================================================
# DPI AWARENESS – Let Qt handle it; remove manual ctypes calls
# ============================================================================

from PySide6.QtWidgets import QApplication, QPushButton, QSpinBox, QLineEdit
from PySide6.QtCore import Qt, QObject, Signal, QThread, QTimer
# QShortcut and QKeySequence are in QtGui, not QtCore
from PySide6.QtGui import QShortcut, QKeySequence

# ----------------------------------------------------------------------------
# UI module – ensure the package is correctly initialised
# ----------------------------------------------------------------------------
try:
    from ui.dashboard_ui import MainWindow
except ImportError as e:
    MainWindow = None
    print(f"[WARN] ui.dashboard_ui not found – UI will not be displayed. ({e})")

from sensor_simulator import TemperatureSensorSimulator, SystemMetricsSimulator

# ----------------------------------------------------------------------------
# Snap7 / fork_bridge – fail gracefully if not installed or missing
# ----------------------------------------------------------------------------
try:
    from fork_bridge import (
        ForkClient,
        DB1_TEMP_OFFSET,
        DB1_CPU_OFFSET,
        DB1_RAM_OFFSET,
        DB1_HEARTBEAT_OFFSET,
        DB1_SETPOINT_OFFSET,
        SNAP7_AVAILABLE,
    )
except ImportError as e:
    SNAP7_AVAILABLE = False
    ForkClient = None
    print(f"[CRITICAL] fork_bridge import failed: {e}")
    print("[INFO] Application will run in SIMULATION-ONLY mode.")

CONFIG_FILE = Path(__file__).parent / "config.ini"

# ============================================================================
# CONFIGURATION LOADER
# ============================================================================
def load_config() -> configparser.ConfigParser:
    """Load or create config.ini with default PLC parameters."""
    config = configparser.ConfigParser()
    if not CONFIG_FILE.exists():
        print(f"[INFO] Creating default config at {CONFIG_FILE}")
        config.add_section("PLC")
        config.set("PLC", "ip", "127.0.0.1")
        config.set("PLC", "rack", "0")
        config.set("PLC", "slot", "1")
        config.set("PLC", "port", "102")
        config.set("PLC", "mode", "simulated")
        config.set("PLC", "poll_interval_ms", "500")
        with open(CONFIG_FILE, "w") as f:
            config.write(f)
    else:
        config.read(CONFIG_FILE)
    return config


def gather_build_info() -> Dict[str, str]:
    """Return build metadata for header/footer display."""
    return {
        "branch": "main",
        "commit": "8f3a2c9",
        "dll_sha": "e3b0c44298fc1c14",
        "version": "v2.4.1",
        "dll_rel": "snap7-x64.dll",
    }

# ============================================================================
# PLC WORKER THREAD
# ============================================================================
class PLCWorker(QObject):
    """Background worker for all PLC read/write operations."""
    data_received = Signal(dict)                # {temp, cpu, ram, hb, setpoint, live}
    connection_status = Signal(bool, bool)      # (connected, fallback_active)
    log_message = Signal(str, str, str)         # (level, source, message)

    def __init__(self, ip: str, rack: int, slot: int, port: int,
                 temp_sim: TemperatureSensorSimulator,
                 sys_sim: SystemMetricsSimulator,
                 poll_interval_ms: int = 500):
        super().__init__()
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.port = port
        self.temp_sim = temp_sim
        self.sys_sim = sys_sim
        self.poll_interval = poll_interval_ms / 1000.0

        self._running = True
        self._mode = "simulated"
        self._client: Optional[ForkClient] = None
        self._was_connected = False
        self._fallback_active = False
        self._heartbeat_counter = 0
        self._reconnect_attempt = 0

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "simulated":
            self._was_connected = False
            self._fallback_active = False
            self.connection_status.emit(False, False)
            self.log_message.emit("INFO", "SYSTEM", "Mode switched to SIMULATION")
        else:
            self.log_message.emit("INFO", "SYSTEM", "Mode switched to LIVE SNAP7")

    def stop(self) -> None:
        self._running = False

    def write_setpoint(self, value: float) -> None:
        if self._mode == "live" and self._client and self._was_connected:
            try:
                self._client.write_real(1, DB1_SETPOINT_OFFSET, value)
                self.log_message.emit("INFO", "PLC", f"Setpoint written: {value:.1f}°C")
            except Exception as e:
                self.log_message.emit("ERROR", "PLC", f"Setpoint write failed: {e}")
        else:
            self.temp_sim.set_setpoint(value)
            self.log_message.emit("INFO", "SIM", f"Simulator setpoint updated: {value:.1f}°C")

    def run(self) -> None:
        self.log_message.emit("INFO", "WORKER",
                              f"Polling started | Target: {self.ip}:{self.port} (interval {self.poll_interval*1000:.0f}ms)")

        while self._running:
            try:
                is_live = (self._mode == "live" and SNAP7_AVAILABLE and ForkClient is not None)

                if is_live:
                    if not self._client:
                        self._client = ForkClient()

                    if not self._was_connected:
                        ok = self._client.connect(self.ip, self.rack, self.slot, self.port)
                        if ok:
                            self._was_connected = True
                            self._fallback_active = False
                            self._reconnect_attempt = 0
                            self.connection_status.emit(True, False)
                            self.log_message.emit("INFO", "PLC", f"CONNECTED to {self.ip}:{self.port}")
                        else:
                            self._reconnect_attempt += 1
                            if not self._fallback_active:
                                self._fallback_active = True
                                self.connection_status.emit(False, True)
                                self.log_message.emit("WARN", "PLC", "Connection refused – fallback activated")

                    if self._was_connected:
                        try:
                            temp = self._client.read_real(1, DB1_TEMP_OFFSET)
                            cpu  = self._client.read_real(1, DB1_CPU_OFFSET)
                            ram  = self._client.read_real(1, DB1_RAM_OFFSET)
                            hb   = self._client.read_byte(1, DB1_HEARTBEAT_OFFSET)
                            sp   = self._client.read_real(1, DB1_SETPOINT_OFFSET)

                            self.data_received.emit({
                                "temp": temp,
                                "cpu": cpu,
                                "ram": ram,
                                "hb": hb,
                                "setpoint": sp,
                                "live": True
                            })

                            if self._fallback_active:
                                self._fallback_active = False
                                self.connection_status.emit(True, False)
                                self.log_message.emit("INFO", "PLC", "Connection RESTORED")
                        except Exception as e:
                            self._was_connected = False
                            if not self._fallback_active:
                                self._fallback_active = True
                                self.connection_status.emit(False, True)
                                self.log_message.emit("ERROR", "PLC", f"Read exception: {e}")

                if not is_live or self._fallback_active:
                    temp = self.temp_sim.read()
                    metrics = self.sys_sim.get_metrics()
                    self._heartbeat_counter = (self._heartbeat_counter + 1) % 256

                    self.data_received.emit({
                        "temp": temp,
                        "cpu": metrics["cpu"],
                        "ram": metrics["memory"],
                        "hb": self._heartbeat_counter,
                        "setpoint": self.temp_sim.setpoint,
                        "live": False
                    })

            except Exception as e:
                self.log_message.emit("ERROR", "WORKER", f"Unhandled exception: {e}")

            time.sleep(self.poll_interval)

        if self._client:
            try:
                self._client.disconnect()
                self.log_message.emit("INFO", "WORKER", "Snap7 client disconnected")
            except Exception:
                pass

# ============================================================================
# SIGNAL HANDLERS
# ============================================================================
def on_data(window, data: dict):
    """Update the main dashboard view (KPIs and chart) with the new data."""
    if not window or not hasattr(window, 'dashboard_view'):
        return

    view = window.dashboard_view
    current_mode = getattr(window, '_current_mode', 'simulated')

    # Determine if we should display the data or show "--"
    if current_mode == "live" and not data.get("live", False):
        # In LIVE mode but data is from simulation (fallback or no connection)
        # Show "--" on all KPIs and do NOT update chart
        view.temp_card.update_value(None)
        view.cpu_card.update_value(None)
        view.ram_card.update_value(None)
        view.hb_card.update_value(None)
        # Still update the live mode flag (this disables breathing/glow)
        view.set_live_mode(False)
        # Do NOT add point to chart
    else:
        # Normal: display the received values
        view.temp_card.update_value(data["temp"])
        view.cpu_card.update_value(data["cpu"])
        view.ram_card.update_value(data["ram"])
        view.hb_card.update_value(data["hb"])
        view.set_live_mode(data.get("live", False))
        view.chart.add_point(data["temp"], data["setpoint"])
        view.sim_card.set_setpoint(data["setpoint"])

def on_connection(window, connected: bool, fallback: bool,
                  ip: str, rack: int, slot: int, port: int):
    if window and hasattr(window, 'dashboard_view'):
        view = window.dashboard_view
        view.plc_card.update_connection(ip, rack, slot, port, connected, fallback)
        if fallback:
            window.show_toast("PLC Unreachable - Switched to Safe Simulation", 3000)
            view.logs.log("WARN", "SYSTEM", "FALLBACK: Simulator engaged")

def on_demo_toggle(temp_sim, sys_sim, active: bool):
    temp_sim.set_demo_mode(active)
    sys_sim.set_demo_mode(active)

def on_mode_change(worker, mode: str):
    """Slot for mode change from UI."""
    worker.set_mode(mode)

# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================
def parse_args():
    parser = argparse.ArgumentParser(description="S7 SCADA Dashboard")
    parser.add_argument("--simulate", "-s", action="store_true",
                        help="Force simulation mode")
    parser.add_argument("--ip", help="Override PLC IP")
    parser.add_argument("--rack", type=int, help="Override rack")
    parser.add_argument("--slot", type=int, help="Override slot")
    parser.add_argument("--port", type=int, help="Override port")
    return parser.parse_args()

# ============================================================================
# MAIN
# ============================================================================
def main():
    args = parse_args()

    print("=" * 70)
    print("  S7 SCADA v2.4.1 – Industrial Dashboard")
    print("=" * 70)

    # ---- High‑DPI: set policy BEFORE creating the app ----
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("S7 SCADA")
    app.setOrganizationName("IndustrialHMI")

    # ---- Config ----
    config = load_config()
    ip = args.ip or config.get("PLC", "ip")
    rack = args.rack if args.rack is not None else config.getint("PLC", "rack")
    slot = args.slot if args.slot is not None else config.getint("PLC", "slot")
    port = args.port if args.port is not None else config.getint("PLC", "port")
    initial_mode = "simulated" if args.simulate else config.get("PLC", "mode", fallback="simulated")
    poll_interval = config.getint("PLC", "poll_interval_ms", fallback=500)

    build_info = gather_build_info()

    # ---- Simulators ----
    temp_sim = TemperatureSensorSimulator(setpoint=65.5)
    sys_sim = SystemMetricsSimulator()

    # ---- Main Window ----
    if MainWindow is None:
        print("[ERROR] UI module missing – cannot display dashboard.")
        return 1
    window = MainWindow(build_info)

    # ---- Helper to update the header pill (expects an integer port) ----
    def update_header_port(new_port: int):
        if hasattr(window, 'header') and hasattr(window.header, 'update_pill'):
            window.header.update_pill(f"EMBEDDED (TCP {new_port})")

    # ---- Initial update of the header pill ----
    update_header_port(port)

    # ---- Connect settings apply to update header ----
    # If MainWindow provides a dedicated signal, use it (but extract only the port)
    if hasattr(window, 'settings_applied'):
        # Assuming the signal emits a dict with a 'port' key
        window.settings_applied.connect(lambda settings: update_header_port(settings.get('port', 102)))
    else:
        # Otherwise, find the "Apply Settings" button and attach a handler
        apply_btn = window.findChild(QPushButton, "applyButton")
        if apply_btn:
            # Attempt to locate the port input widget (spinbox or line edit)
            port_widget = window.findChild(QSpinBox, "portSpinBox") or window.findChild(QLineEdit, "portLineEdit")
            if port_widget:
                def on_apply_from_widget():
                    # Get the current port value from the widget
                    if hasattr(port_widget, 'value'):
                        new_port = port_widget.value()
                    else:
                        try:
                            new_port = int(port_widget.text())
                        except ValueError:
                            new_port = 102  # fallback
                    update_header_port(new_port)
                apply_btn.clicked.connect(on_apply_from_widget)
            else:
                # Fallback: read the updated config file after apply
                def on_apply_from_config():
                    cfg = load_config()
                    new_port = cfg.getint("PLC", "port", fallback=102)
                    update_header_port(new_port)
                apply_btn.clicked.connect(on_apply_from_config)

    # ---- PLC Worker ----
    worker = PLCWorker(ip, rack, slot, port, temp_sim, sys_sim, poll_interval)
    worker_thread = QThread()
    worker.moveToThread(worker_thread)

    worker.data_received.connect(lambda d: on_data(window, d))
    worker.data_received.connect(lambda d: window.update_all_pages(d))   # update all pages
    worker.connection_status.connect(
        lambda c, fb: on_connection(window, c, fb, ip, rack, slot, port)
    )
    worker.log_message.connect(window.dashboard_view.logs.log)
    window.dashboard_view.sim_card.apply_clicked.connect(worker.write_setpoint)

    # ---- Connect mode change from UI ----
    window.mode_changed.connect(lambda mode: on_mode_change(worker, mode))

    # ---- Demo Mode (Ctrl+Shift+D) ----
    demo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), window)
    demo_shortcut.activated.connect(lambda: toggle_demo_mode(window, temp_sim, sys_sim))

    # ---- Start thread ----
    worker_thread.started.connect(worker.run)
    worker_thread.finished.connect(worker.deleteLater)
    worker_thread.start()

    # Set initial mode and update UI combo
    worker.set_mode(initial_mode)
    window.set_mode_ui(initial_mode)  # sync the combo box

    # ---- Initial logs ----
    logs = window.dashboard_view.logs
    logs.log("INFO", "SYSTEM", f"S7 SCADA initialized | Mode: {initial_mode.upper()}")
    logs.log("INFO", "SYSTEM", f"Target: {ip}:{port} | Rack:{rack} | Slot:{slot}")
    logs.log("INFO", "BUILD", f"Branch: {build_info['branch']} | Commit: {build_info['commit']}")
    if not SNAP7_AVAILABLE:
        logs.log("WARN", "SYSTEM", "python-snap7 NOT FOUND – forced simulation mode")
    else:
        logs.log("INFO", "SYSTEM", "Snap7 library loaded successfully")

    window.show()
    print("[OK] Dashboard displayed. Entering Qt event loop...")

    ret = app.exec()

    # ---- Shutdown ----
    print("[INFO] Shutting down...")
    worker.stop()
    worker_thread.quit()
    worker_thread.wait(3000)
    print("[OK] Clean shutdown complete.")
    sys.exit(ret)


def toggle_demo_mode(window, temp_sim, sys_sim):
    active = getattr(window, '_demo_active', False)
    new_state = not active
    window._demo_active = new_state
    temp_sim.set_demo_mode(new_state)
    sys_sim.set_demo_mode(new_state)
    if hasattr(window, 'header'):
        window.header.set_demo_badge(new_state)
    if hasattr(window, 'dashboard_view'):
        window.dashboard_view.logs.log(
            "INFO", "SYSTEM", f"Demo Mode {'ACTIVATED' if new_state else 'DEACTIVATED'}"
        )


if __name__ == "__main__":
    main()