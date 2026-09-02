# demo/ui/status_cards.py
"""
KPI Status Cards: Temperature, CPU, RAM, Heartbeat

Features:
  - Breathing animation on status dots when in LIVE mode (disabled in SIM)
  - 46px value, 12px mono metadata
  - 8px status dot (green by default, amber for RAM card)
  - Support for metadata updates and live mode toggling
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt
from .theme import COLOR_GREEN, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, FONT_MONO, FONT_UI


class BreathingDot(QLabel):
    """An 8‑10px circle that can breathe (opacity animation) when in LIVE mode."""

    def __init__(self, color: str = COLOR_GREEN, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._base_color = color
        self._live = False
        self._anim: QPropertyAnimation | None = None
        self._update_style()

    def _update_style(self) -> None:
        """Apply the current base color and circular shape."""
        self.setStyleSheet(f"""
            background-color: {self._base_color};
            border-radius: 5px;
        """)

    def set_color(self, color: str) -> None:
        """Change the dot's static color (used for fallback amber on RAM card)."""
        self._base_color = color
        self._update_style()

    def set_live(self, live: bool) -> None:
        """
        Enable or disable the breathing animation.
        Called by DashboardView when data source changes.
        """
        if live == self._live:
            return
        self._live = live
        if live:
            self._start_breathing()
        else:
            self._stop_breathing()

    def _start_breathing(self) -> None:
        """Start a continuous opacity oscillation (1.0 → 0.4 → 1.0) over 1.5s."""
        if self._anim:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(1500)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.4)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.start()

    def _stop_breathing(self) -> None:
        """Stop animation and reset opacity to fully opaque."""
        if self._anim:
            self._anim.stop()
            self._anim = None
        self.setWindowOpacity(1.0)


class KPICard(QWidget):
    """
    KPI card anatomy (top to bottom):
      1. Status dot (8px) + label (14px gray)
      2. Huge value (46px white semibold) + unit (20px gray)
      3. Two metadata lines (12px gray, mono for tags)
    """

    def __init__(
        self,
        title: str,
        unit: str,
        tag: str,
        metadata: list,
        dot_color: str = COLOR_GREEN,
        parent=None
    ):
        super().__init__(parent)
        self.setProperty("class", "panel")
        self.unit = unit
        self.tag = tag

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(4)

        # 1. Top row: dot + label
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.dot = BreathingDot(dot_color)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"font-size: 14px; color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_UI};")
        top_row.addWidget(self.dot)
        top_row.addWidget(self.title_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        # 2. Value row
        val_row = QHBoxLayout()
        val_row.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        val_row.setSpacing(4)

        self.value_label = QLabel("--")
        self.value_label.setProperty("class", "kpi-value")

        self.unit_label = QLabel(unit)
        self.unit_label.setProperty("class", "kpi-unit")

        val_row.addWidget(self.value_label)
        val_row.addWidget(self.unit_label)
        val_row.addStretch()
        layout.addLayout(val_row)

        layout.addSpacing(8)

        # 3. Metadata lines (exactly two)
        self.meta_labels = []
        for line in metadata:
            lbl = QLabel(line)
            lbl.setProperty("class", "meta")
            layout.addWidget(lbl)
            self.meta_labels.append(lbl)

        layout.addStretch()

    def update_value(self, value: float | None) -> None:
        """Update the displayed numeric value, formatting appropriately."""
        if value is None:
            self.value_label.setText("--")
        elif self.unit in ("%", "°C"):
            self.value_label.setText(f"{value:.1f}")
        else:
            self.value_label.setText(str(int(value)))

    def set_live(self, live: bool) -> None:
        """Forward live mode to the breathing dot."""
        self.dot.set_live(live)

    def set_status_color(self, color: str) -> None:
        """Change the status dot's base color (e.g., for fallback)."""
        self.dot.set_color(color)

    def update_metadata(self, line1: str, line2: str) -> None:
        """Update the two metadata lines (used for setpoint, free memory, etc.)."""
        if len(self.meta_labels) >= 2:
            self.meta_labels[0].setText(line1)
            self.meta_labels[1].setText(line2)