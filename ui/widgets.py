# demo/ui/widgets.py
"""
Header, Footer, PLC Connection Card, Sensor Simulator Card, Toast Notification.
Implements dark industrial theme, micro-interactions, and fallback pulse effects.
Now includes a mode selection combo box in the header.
"""

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QSlider, QPushButton, QGraphicsOpacityEffect, QComboBox
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer
from .theme import (
    COLOR_BG_DEEP, COLOR_ACCENT, COLOR_ACCENT_SOFT, COLOR_AMBER,
    COLOR_GREEN, COLOR_RED, COLOR_BORDER, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_TEXT_FAINT, FONT_MONO
)


class HeaderBar(QFrame):
    """Top bar: Logo, title, status pill, build metadata, demo badge, and mode selector."""
    
    mode_changed = Signal(str)  # emits "live" or "simulated"

    def __init__(self, build_info: dict, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setStyleSheet(f"""
            background-color: {COLOR_BG_DEEP};
            border-bottom: 1px solid #1a2332;
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        # Logo (hexagon glyph)
        logo = QLabel("⬡")
        logo.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 28px; background: transparent;")
        layout.addWidget(logo)

        # Title
        name = QLabel("S7 SCADA")
        name.setStyleSheet("font-size: 20px; font-weight: 700; color: white; letter-spacing: 1px; background: transparent;")
        layout.addWidget(name)

        sep = QLabel("|")
        sep.setStyleSheet(f"color: {COLOR_TEXT_FAINT}; margin: 0 4px; background: transparent;")
        layout.addWidget(sep)

        subtitle = QLabel("Fork-Integrated Industrial Dashboard")
        subtitle.setStyleSheet(f"font-size: 14px; color: {COLOR_TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(subtitle)

        layout.addStretch()

        # Demo badge (hidden by default)
        self.demo_badge = QLabel("🎬 DEMO MODE")
        self.demo_badge.setStyleSheet(f"""
            background-color: {COLOR_AMBER};
            color: #000;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 10px;
        """)
        self.demo_badge.hide()
        layout.addWidget(self.demo_badge)

        # ---- Mode Selector ComboBox ----
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["SIMULATED", "LIVE"])
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #0d1420;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                font-family: {FONT_MONO};
            }}
            QComboBox:hover {{
                border-color: {COLOR_ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
        """)
        self.mode_combo.currentTextChanged.connect(self._on_mode_selected)
        layout.addWidget(self.mode_combo)

        # Status pill (EMBEDDED (TCP 102))
        self.pill = QFrame()
        self.pill.setProperty("class", "status-pill")
        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(12, 4, 12, 4)
        self.pill_text = QLabel("EMBEDDED (TCP 102)")
        self.pill_text.setProperty("class", "status-pill-text")
        pill_layout.addWidget(self.pill_text)
        layout.addWidget(self.pill)

        # Build metadata
        branch = build_info.get("branch", "main")
        commit = build_info.get("commit", "8f3a2c9")[:7]
        sha = build_info.get("dll_sha", "e3b0c44298fc1c14")[:16]
        meta = QLabel(f"branch: {branch} | commit: {commit} | sha256: {sha}")
        meta.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_FAINT}; font-family: {FONT_MONO}; margin-left: 16px; background: transparent;")
        layout.addWidget(meta)

    def _on_mode_selected(self, text: str):
        """Emit the mode signal when the combo changes."""
        mode = "live" if text == "LIVE" else "simulated"
        self.mode_changed.emit(mode)

    def set_mode(self, mode: str):
        """Set the combo box to match the given mode (used for initial sync)."""
        if mode == "live":
            self.mode_combo.setCurrentText("LIVE")
        else:
            self.mode_combo.setCurrentText("SIMULATED")

    def set_demo_badge(self, visible: bool) -> None:
        """Show/hide the DEMO MODE badge."""
        self.demo_badge.setVisible(visible)

    # --------------------------------------------------------------
    #  NEW METHOD: Dynamically update the status pill text
    # --------------------------------------------------------------
    def update_pill(self, text: str) -> None:
        """
        Dynamically update the status pill text.
        Example: header_bar.update_pill("CONNECTED | 192.168.1.10")
        """
        self.pill_text.setText(text)


class FooterBar(QFrame):
    """Bottom bar: connection info, uptime, and personal branding."""

    def __init__(self, build_info: dict, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setStyleSheet(f"""
            background-color: {COLOR_BG_DEEP};
            border-top: 1px solid #1a2332;
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        self.info_label = QLabel(
            "Connected to -- | Rack: -- | Slot: -- | DPI Scale: 1.0x | Uptime: 00:00:00 | S7 SCADA v2.4.1"
        )
        self.info_label.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_FAINT}; font-family: {FONT_MONO}; background: transparent;")
        layout.addWidget(self.info_label)

        layout.addStretch()

        # Personal branding (clickable)
        branding = QLabel(
            '<a href="https://linkedin.com/in/esmaeilireza" style="color:#7dd3fc; text-decoration:none;">'
        )
        branding.setStyleSheet(f"font-size: 12px; font-family: {FONT_MONO}; background: transparent;")
        branding.setTextInteractionFlags(Qt.TextBrowserInteraction)
        branding.setOpenExternalLinks(True)
        layout.addWidget(branding)

    def update_info(self, ip: str, rack: int, slot: int, dpi_scale: float, uptime_str: str) -> None:
        """Refresh the footer metadata."""
        self.info_label.setText(
            f"Connected to {ip} | Rack: {rack} | Slot: {slot} | "
            f"DPI Scale: {dpi_scale:.1f}x | Uptime: {uptime_str} | S7 SCADA v2.4.1"
        )


class PLCCard(QFrame):
    """Right rail top: PLC connection parameters and status with fallback animation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("PLC Connection")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLOR_TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(title)

        # Definition list
        self.fields = {}
        for label_text in ("IP Address", "Rack", "Slot", "Port"):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"font-size: 14px; color: {COLOR_TEXT_SECONDARY}; background: transparent;")
            val = QLabel("--")
            val.setStyleSheet(f"font-size: 14px; color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_MONO}; background: transparent;")
            val.setAlignment(Qt.AlignRight)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            layout.addLayout(row)
            self.fields[label_text] = val

        layout.addSpacing(12)

        # Status row (dot + label + value)
        status_row = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {COLOR_GREEN}; font-size: 12px; background: transparent;")
        status_lbl = QLabel("Status:")
        status_lbl.setStyleSheet(f"font-size: 14px; color: {COLOR_TEXT_SECONDARY}; background: transparent;")
        self.status_val = QLabel("Connected")
        self.status_val.setStyleSheet(f"font-size: 14px; color: {COLOR_GREEN}; font-weight: 600; background: transparent;")
        status_row.addWidget(self.status_dot)
        status_row.addWidget(status_lbl)
        status_row.addWidget(self.status_val)
        status_row.addStretch()
        layout.addLayout(status_row)

        # Internal state for fallback pulse animation
        self._fallback_active = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_fallback_dot)
        self._pulse_state = False

    def update_connection(self, ip: str, rack: int, slot: int, port: int,
                          connected: bool, fallback: bool = False) -> None:
        """Update displayed parameters and connection status."""
        self.fields["IP Address"].setText(str(ip))
        self.fields["Rack"].setText(str(rack))
        self.fields["Slot"].setText(str(slot))
        self.fields["Port"].setText(str(port))

        if fallback:
            self._fallback_active = True
            self.status_val.setText("FALLBACK: SIMULATOR ACTIVE")
            self.status_val.setStyleSheet(f"font-size: 13px; color: {COLOR_AMBER}; font-weight: 600; background: transparent;")
            # Start pulse animation
            if not self._pulse_timer.isActive():
                self._pulse_timer.start(500)   # pulse every 500ms
        else:
            self._fallback_active = False
            self._pulse_timer.stop()
            if connected:
                self.status_dot.setStyleSheet(f"color: {COLOR_GREEN}; font-size: 12px; background: transparent;")
                self.status_val.setText("Connected")
                self.status_val.setStyleSheet(f"font-size: 14px; color: {COLOR_GREEN}; font-weight: 600; background: transparent;")
            else:
                self.status_dot.setStyleSheet(f"color: {COLOR_RED}; font-size: 12px; background: transparent;")
                self.status_val.setText("Disconnected")
                self.status_val.setStyleSheet(f"font-size: 14px; color: {COLOR_RED}; font-weight: 600; background: transparent;")

    def _pulse_fallback_dot(self) -> None:
        """Pulse the status dot between amber and darker amber for fallback indication."""
        self._pulse_state = not self._pulse_state
        color = "#f59e0b" if self._pulse_state else "#b45309"  # lighter / darker amber
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 14px; background: transparent;")


class SensorSimCard(QFrame):
    """Right rail bottom: setpoint input, slider, and primary CTA."""

    apply_clicked = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Sensor Simulator")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLOR_TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(title)

        # Input row
        sp_row = QHBoxLayout()
        sp_label = QLabel("Temp Setpoint")
        sp_label.setStyleSheet(f"font-size: 14px; color: {COLOR_TEXT_SECONDARY}; background: transparent;")
        self.sp_input = QLineEdit("65.5")
        self.sp_input.setProperty("class", "sim-input")
        self.sp_input.setFixedWidth(100)
        self.sp_input.setAlignment(Qt.AlignRight)
        sp_row.addWidget(sp_label)
        sp_row.addStretch()
        sp_row.addWidget(self.sp_input)
        layout.addLayout(sp_row)

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(65)
        self.slider.setCursor(Qt.PointingHandCursor)
        self.slider.valueChanged.connect(self._on_slider_change)
        layout.addWidget(self.slider)

        # Primary CTA (the only saturated element)
        apply_btn = QPushButton("Apply Changes")
        apply_btn.setProperty("class", "apply-btn")
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(apply_btn)

    def _on_slider_change(self, value: int) -> None:
        """Update the input field when slider moves."""
        self.sp_input.setText(f"{float(value):.1f}")

    def _on_apply(self) -> None:
        """Emit the setpoint value when Apply is clicked."""
        try:
            val = float(self.sp_input.text())
            self.apply_clicked.emit(val)
        except ValueError:
            pass

    def set_setpoint(self, value: float) -> None:
        """Update both input and slider without triggering signals."""
        self.sp_input.blockSignals(True)
        self.slider.blockSignals(True)
        self.sp_input.setText(f"{value:.1f}")
        self.slider.setValue(int(round(value)))
        self.sp_input.blockSignals(False)
        self.slider.blockSignals(False)


class ToastNotification(QFrame):
    """
    Bottom-right overlay notification.
    Displays short messages with a fade-in/fade-out animation.
    Should be placed on top of other widgets (e.g., using a QStackedWidget).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "toast")
        self.setFixedHeight(48)
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        self.label = QLabel("")
        self.label.setStyleSheet(f"color: {COLOR_AMBER}; font-size: 13px; font-family: {FONT_MONO}; background: transparent;")
        layout.addWidget(self.label)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)

    def show_message(self, text: str, duration_ms: int = 3000) -> None:
        """Display a toast message for the given duration."""
        self.label.setText(text)
        self.show()
        self.raise_()
        self._opacity.setOpacity(1.0)
        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self) -> None:
        """Fade out and hide the toast."""
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        try:
            self._anim.finished.disconnect()
        except RuntimeError:
            pass
        self._anim.finished.connect(self.hide)
        self._anim.start()