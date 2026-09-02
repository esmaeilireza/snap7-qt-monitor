# demo/ui/chart_widget.py
"""
Real‑time Temperature Monitoring Chart using pyqtgraph.

Visual Spec Compliance:
  - Cyan line (2px) with subtle gradient area fill fading to transparent.
  - Amber dashed horizontal setpoint line.
  - Axes: Y‑axis 0–100 (step 20), X‑axis 0–60 seconds (step 10).
  - Faint horizontal gridlines.
  - LIVE mode: faint cyan glow/shadow on the active chart line (via shadowPen).
  - SIM mode: glow disabled.
  - Legend (top‑right): "Actual" (cyan) and "Setpoint" (amber dashed).
"""

import numpy as np
from collections import deque
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
import pyqtgraph as pg

from .theme import (
    COLOR_PANEL, COLOR_ACCENT, COLOR_AMBER, COLOR_CHART_GRID,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, FONT_UI
)


class ChartWidget(QFrame):
    """Temperature chart with real‑time data and setpoint overlay."""

    MAX_POINTS = 120  # 60 seconds at 2 Hz

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # ----- Header: Title + Legend -----
        header = QHBoxLayout()
        title = QLabel("Real-Time Temperature Monitoring")
        title.setStyleSheet(
            f"font-size: 16px; font-weight: 600; color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_UI};"
        )
        header.addWidget(title)
        header.addStretch()

        # Legend
        legend_box = QHBoxLayout()
        legend_box.setSpacing(12)

        actual_dot = QLabel("—")
        actual_dot.setStyleSheet(f"color:{COLOR_ACCENT}; font-size:16px; font-weight:bold;")
        actual_lbl = QLabel("Actual")
        actual_lbl.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY}; font-size:12px; font-family: {FONT_UI};")

        sp_dot = QLabel("- -")
        sp_dot.setStyleSheet(f"color:{COLOR_AMBER}; font-size:16px; font-weight:bold;")
        sp_lbl = QLabel("Setpoint")
        sp_lbl.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY}; font-size:12px; font-family: {FONT_UI};")

        legend_box.addWidget(actual_dot)
        legend_box.addWidget(actual_lbl)
        legend_box.addWidget(sp_dot)
        legend_box.addWidget(sp_lbl)
        header.addLayout(legend_box)
        layout.addLayout(header)

        # ----- PyQtGraph Setup -----
        pg.setConfigOptions(antialias=True, background=COLOR_PANEL, foreground=COLOR_TEXT_SECONDARY)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=False, y=True, alpha=0.15)
        self.plot_widget.setYRange(0, 100)
        self.plot_widget.setXRange(0, self.MAX_POINTS)

        # Axes styling
        axis_pen = pg.mkPen(COLOR_CHART_GRID, width=1)
        text_pen = pg.mkPen(COLOR_TEXT_SECONDARY)

        self.plot_widget.getAxis('left').setLabel("Temp (°C)", color=COLOR_TEXT_SECONDARY)
        self.plot_widget.getAxis('bottom').setLabel("Time (s)", color=COLOR_TEXT_SECONDARY)
        self.plot_widget.getAxis('left').setPen(axis_pen)
        self.plot_widget.getAxis('bottom').setPen(axis_pen)
        self.plot_widget.getAxis('left').setTextPen(text_pen)
        self.plot_widget.getAxis('bottom').setTextPen(text_pen)

        # Ticks: Y 0–100 step 20, X 0–60s step 10
        self.plot_widget.getAxis('left').setTicks([[(i, str(i)) for i in range(0, 101, 20)]])
        self.plot_widget.getAxis('bottom').setTicks([[(i, str(int(i * 0.5))) for i in range(0, 121, 20)]])

        self.plot_widget.hideButtons()

        # ----- Data Buffers -----
        self.temp_data = deque(maxlen=self.MAX_POINTS)
        self.sp_data = deque(maxlen=self.MAX_POINTS)

        # ----- Actual Line (cyan) with gradient fill -----
        self.actual_curve = self.plot_widget.plot(
            pen=pg.mkPen(COLOR_ACCENT, width=2),
            fillLevel=0,
            fillBrush=pg.mkColor(COLOR_ACCENT + "18"),  # subtle cyan with alpha
        )
        self._glow_active = False

        # ----- Setpoint Line (amber dashed) -----
        self.sp_curve = self.plot_widget.plot(
            pen=pg.mkPen(COLOR_AMBER, width=1.5, style=Qt.DashLine),
        )

        layout.addWidget(self.plot_widget)

    def add_point(self, temp: float, setpoint: float) -> None:
        """Append a new data point and update the chart."""
        self.temp_data.append(temp)
        self.sp_data.append(setpoint)
        x = np.arange(len(self.temp_data))
        self.actual_curve.setData(x, list(self.temp_data))
        self.sp_curve.setData(x, list(self.sp_data))

    def set_live_visuals(self, live: bool) -> None:
        """
        Enable or disable the cyan glow on the chart line.
        Glow is active only when receiving real LIVE data.
        """
        if live and not self._glow_active:
            # Thicker pen with a shadow/glow effect
            self.actual_curve.setPen(pg.mkPen(COLOR_ACCENT, width=2.5))
            self.actual_curve.setShadowPen(pg.mkPen(COLOR_ACCENT + "66", width=6))
            self._glow_active = True
        elif not live and self._glow_active:
            self.actual_curve.setPen(pg.mkPen(COLOR_ACCENT, width=2))
            self.actual_curve.setShadowPen(None)
            self._glow_active = False