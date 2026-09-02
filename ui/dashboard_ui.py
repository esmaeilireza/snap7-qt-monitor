# demo/ui/dashboard_ui.py
"""
Main Window – Central widget, layout management, keyboard shortcuts.
All sidebar items now display real data (Live or Simulated).
Added a functional Settings page to configure PLC connection parameters.
"""

import time
import configparser
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QLabel, QLineEdit, QComboBox, QPushButton, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QShortcut, QKeySequence

from .theme import GLOBAL_QSS, COLOR_TEXT_PRIMARY, COLOR_BG_DEEP, COLOR_TEXT_SECONDARY
from .asset_panel import AssetPanel
from .views import DashboardView
from .widgets import HeaderBar, FooterBar, ToastNotification


class SimpleDataPage(QWidget):
    """A generic page that displays data from the PLC worker."""

    def __init__(self, title: str, fields: list, parent=None):
        super().__init__(parent)
        self.title = title
        self.fields = fields
        self.data = {field: "--" for field in fields}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 24px; font-weight: 600; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title_label)

        self.info_label = QLabel()
        self.info_label.setStyleSheet(f"""
            font-size: 18px;
            color: {COLOR_TEXT_SECONDARY};
            font-family: 'JetBrains Mono', monospace;
            padding: 20px;
            background-color: {COLOR_BG_DEEP};
            border-radius: 8px;
        """)
        self.info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.info_label)
        layout.addStretch()

    def update_data(self, data_dict: dict):
        for key in self.fields:
            if key in data_dict:
                self.data[key] = data_dict[key]
        self._refresh_display()

    def _refresh_display(self):
        lines = [f"{key}: {value}" for key, value in self.data.items()]
        self.info_label.setText("\n".join(lines))


class SettingsPage(QWidget):
    """
    Settings page for PLC connection parameters.
    Saves changes to config.ini and emits a signal to apply them.
    """

    settings_applied = Signal(dict)  # emits {"ip": ..., "rack": ..., "slot": ..., "port": ..., "mode": ...}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = Path(__file__).parent.parent / "config.ini"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 24px; font-weight: 600; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        # Form
        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignRight)

        # Load current config
        config = configparser.ConfigParser()
        if self.config_file.exists():
            config.read(self.config_file)
        else:
            config.add_section("PLC")

        self.ip_edit = QLineEdit(config.get("PLC", "ip", fallback="127.0.0.1"))
        self.ip_edit.setStyleSheet("background-color: #0d1420; border: 1px solid #1d2836; border-radius: 4px; padding: 6px; color: white;")

        self.rack_edit = QLineEdit(config.get("PLC", "rack", fallback="0"))
        self.rack_edit.setStyleSheet("background-color: #0d1420; border: 1px solid #1d2836; border-radius: 4px; padding: 6px; color: white;")

        self.slot_edit = QLineEdit(config.get("PLC", "slot", fallback="1"))
        self.slot_edit.setStyleSheet("background-color: #0d1420; border: 1px solid #1d2836; border-radius: 4px; padding: 6px; color: white;")

        self.port_edit = QLineEdit(config.get("PLC", "port", fallback="102"))
        self.port_edit.setStyleSheet("background-color: #0d1420; border: 1px solid #1d2836; border-radius: 4px; padding: 6px; color: white;")

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["simulated", "live"])
        current_mode = config.get("PLC", "mode", fallback="simulated")
        self.mode_combo.setCurrentText(current_mode)
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #0d1420;
                color: white;
                border: 1px solid #1d2836;
                border-radius: 4px;
                padding: 6px;
            }
            QComboBox:hover { border-color: #00c2ff; }
        """)

        form.addRow("IP Address:", self.ip_edit)
        form.addRow("Rack:", self.rack_edit)
        form.addRow("Slot:", self.slot_edit)
        form.addRow("Port:", self.port_edit)
        form.addRow("Default Mode:", self.mode_combo)

        layout.addLayout(form)

        # Save button
        save_btn = QPushButton("Apply Settings")
        save_btn.setProperty("class", "apply-btn")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()

    def _save_settings(self):
        """Save settings to config.ini and emit signal with new values."""
        try:
            ip = self.ip_edit.text().strip()
            rack = int(self.rack_edit.text().strip())
            slot = int(self.slot_edit.text().strip())
            port = int(self.port_edit.text().strip())
            mode = self.mode_combo.currentText().lower()

            # Validate
            if not ip:
                raise ValueError("IP address cannot be empty")
            if rack < 0 or rack > 7:
                raise ValueError("Rack must be between 0 and 7")
            if slot < 0 or slot > 7:
                raise ValueError("Slot must be between 0 and 7")
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")

            # Save to config.ini
            config = configparser.ConfigParser()
            if self.config_file.exists():
                config.read(self.config_file)
            if not config.has_section("PLC"):
                config.add_section("PLC")

            config.set("PLC", "ip", ip)
            config.set("PLC", "rack", str(rack))
            config.set("PLC", "slot", str(slot))
            config.set("PLC", "port", str(port))
            config.set("PLC", "mode", mode)

            with open(self.config_file, "w") as f:
                config.write(f)

            # Emit signal
            self.settings_applied.emit({
                "ip": ip,
                "rack": rack,
                "slot": slot,
                "port": port,
                "mode": mode,
            })

            QMessageBox.information(self, "Settings Saved",
                                    f"Settings saved successfully!\n\n"
                                    f"IP: {ip}\nRack: {rack}\nSlot: {slot}\nPort: {port}\nMode: {mode}\n\n"
                                    "The changes have been applied.")

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Please check your input:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{str(e)}")


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""

    demo_toggled = Signal(bool)
    mode_changed = Signal(str)   # emits "live" or "simulated"
    settings_applied = Signal(dict)  # forwards settings from SettingsPage

    def __init__(self, build_info: dict, parent=None):
        super().__init__(parent)
        self.build_info = build_info
        self.setWindowTitle("S7 SCADA - Fork-Integrated Industrial Dashboard")
        self.resize(1440, 900)
        self.setMinimumSize(1024, 600)
        self.setStyleSheet(GLOBAL_QSS)

        self._demo_mode = False
        self._uptime_start = time.time()
        self._current_mode = "simulated"

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Header
        self.header = HeaderBar(build_info)
        root_layout.addWidget(self.header)

        self.header.mode_changed.connect(self.mode_changed.emit)
        self.mode_changed.connect(lambda mode: setattr(self, '_current_mode', mode))

        # 2. Body: Sidebar + Stacked Content
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = AssetPanel()
        body.addWidget(self.sidebar)

        # ---- STACKED WIDGET ----
        self.stacked_widget = QStackedWidget()

        # Page 0: Main Dashboard
        self.dashboard_view = DashboardView()
        self.stacked_widget.addWidget(self.dashboard_view)

        # Page 1: PLC Data
        self.plc_data_page = SimpleDataPage(
            "PLC Data - Live Tags",
            ["Temperature (°C)", "CPU (%)", "RAM (%)", "Heartbeat", "Setpoint (°C)", "Mode"]
        )
        self.stacked_widget.addWidget(self.plc_data_page)

        # Page 2: Sensors
        self.sensors_page = SimpleDataPage(
            "Sensor Data",
            ["Temperature (°C)", "Setpoint (°C)", "Mode"]
        )
        self.stacked_widget.addWidget(self.sensors_page)

        # Page 3: System Metrics
        self.metrics_page = SimpleDataPage(
            "System Metrics",
            ["CPU Usage (%)", "RAM Usage (%)", "Uptime (s)", "Mode"]
        )
        self.stacked_widget.addWidget(self.metrics_page)

        # Page 4: Logs
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(20, 20, 20, 20)
        self.logs_page = self.dashboard_view.logs
        log_layout.addWidget(self.logs_page)
        self.stacked_widget.addWidget(log_container)

        # Page 5: Settings (real settings page)
        self.settings_page = SettingsPage()
        self.settings_page.settings_applied.connect(self.settings_applied.emit)
        self.stacked_widget.addWidget(self.settings_page)

        body.addWidget(self.stacked_widget, stretch=1)

        body_widget = QWidget()
        body_widget.setLayout(body)
        root_layout.addWidget(body_widget, stretch=1)

        # 3. Footer
        self.footer = FooterBar(build_info)
        root_layout.addWidget(self.footer)

        # Toast overlay
        self.toast = ToastNotification(self)
        self.toast.setParent(self)

        # ---- Connect sidebar navigation ----
        self.sidebar.nav_selected.connect(self.switch_view)

        # ---- Demo Mode (Ctrl+Shift+D) ----
        demo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        demo_shortcut.activated.connect(self.toggle_demo_mode)

        # Uptime timer
        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._update_uptime)
        self._uptime_timer.start(1000)

        # Store current data
        self._current_data = {
            "temp": 0.0,
            "cpu": 0.0,
            "ram": 0.0,
            "hb": 0,
            "setpoint": 0.0,
            "live": False
        }

    def switch_view(self, view_name: str) -> None:
        """Switch the stacked widget to the page corresponding to the sidebar item."""
        index_map = {
            "dashboard": 0,
            "plc_data": 1,
            "sensors": 2,
            "system_metrics": 3,
            "logs": 4,
            "settings": 5,
        }
        index = index_map.get(view_name, 0)
        self.stacked_widget.setCurrentIndex(index)

        page_name = view_name.replace("_", " ").title()
        self.dashboard_view.logs.log("INFO", "NAV", f"Switched to: {page_name}")

    def update_all_pages(self, data: dict):
        """Update ALL pages with new data."""
        self._current_data = data

        if self._current_mode == "live" and not data.get("live", False):
            plc_data = {
                "Temperature (°C)": "--",
                "CPU (%)": "--",
                "RAM (%)": "--",
                "Heartbeat": "--",
                "Setpoint (°C)": "--",
                "Mode": "LIVE (NO DATA)",
            }
            sensors_data = {
                "Temperature (°C)": "--",
                "Setpoint (°C)": "--",
                "Mode": "LIVE (NO DATA)",
            }
            metrics_data = {
                "CPU Usage (%)": "--",
                "RAM Usage (%)": "--",
                "Uptime (s)": "--",
                "Mode": "LIVE (NO DATA)",
            }
        else:
            mode_str = "LIVE" if data.get("live", False) else "SIMULATED"
            plc_data = {
                "Temperature (°C)": f"{data['temp']:.2f}",
                "CPU (%)": f"{data['cpu']:.2f}",
                "RAM (%)": f"{data['ram']:.2f}",
                "Heartbeat": str(data['hb']),
                "Setpoint (°C)": f"{data['setpoint']:.2f}",
                "Mode": mode_str,
            }
            sensors_data = {
                "Temperature (°C)": f"{data['temp']:.2f}",
                "Setpoint (°C)": f"{data['setpoint']:.2f}",
                "Mode": mode_str,
            }
            metrics_data = {
                "CPU Usage (%)": f"{data['cpu']:.2f}",
                "RAM Usage (%)": f"{data['ram']:.2f}",
                "Uptime (s)": str(int(time.time() - self._uptime_start)),
                "Mode": mode_str,
            }

        self.plc_data_page.update_data(plc_data)
        self.sensors_page.update_data(sensors_data)
        self.metrics_page.update_data(metrics_data)

    def set_mode_ui(self, mode: str):
        """Sync the header combo box with the current mode."""
        self.header.set_mode(mode)
        self._current_mode = mode

    def toggle_demo_mode(self) -> None:
        self._demo_mode = not self._demo_mode
        self.header.show_demo_badge(self._demo_mode)
        self.demo_toggled.emit(self._demo_mode)
        state = "ACTIVATED" if self._demo_mode else "DEACTIVATED"
        self.dashboard_view.logs.log("INFO", "SYSTEM", f"Demo mode {state}")

    @property
    def demo_mode(self) -> bool:
        return self._demo_mode

    def show_toast(self, message: str, duration_ms: int = 3000) -> None:
        self.toast.show_message(message, duration_ms)
        self.toast.adjustSize()
        x = self.width() - self.toast.width() - 20
        y = self.height() - self.toast.height() - 50
        self.toast.move(x, y)

    def _update_uptime(self) -> None:
        elapsed = int(time.time() - self._uptime_start)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        uptime_str = f"{h:02d}:{m:02d}:{s:02d}"
        dpi = self.devicePixelRatioF()
        plc = self.dashboard_view.plc_card
        ip = plc.fields["IP Address"].text()
        rack = plc.fields["Rack"].text()
        slot = plc.fields["Slot"].text()
        self.footer.update_info(ip, rack, slot, dpi, uptime_str)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.toast.isVisible():
            x = self.width() - self.toast.width() - 20
            y = self.height() - self.toast.height() - 50
            self.toast.move(x, y)