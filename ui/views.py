# demo/ui/views.py
"""
Dashboard View Container – routes the main content area.
Matches the visual specification:
  - Left column (~75%): 4 KPI cards → Chart → Logs
  - Right column (~25%): PLC Connection card → Sensor Simulator card
Handles live/simulation visual feedback (breathing dots, chart glow).
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from .chart_widget import ChartWidget
from .log_widget import LogWidget
from .status_cards import KPICard
from .widgets import PLCCard, SensorSimCard
from .theme import COLOR_GREEN, COLOR_AMBER


class DashboardView(QWidget):
    """
    Main container for all dashboard widgets.
    Exposes child widgets for external updates (data, mode, etc.).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)

        # ========== LEFT COLUMN (75%) ==========
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        # 1. KPI Row (4 cards)
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)

        # RAM card gets an amber status dot per visual spec 4.3
        self.temp_card = KPICard(
            "Temperature", "°C", "DB1_TEMP",
            metadata=["Setpoint: --", "Tag: DB1_TEMP"],
            dot_color=COLOR_GREEN
        )
        self.cpu_card = KPICard(
            "CPU Usage", "%", "DB1_CPU",
            metadata=["Cores: 8", "Tag: DB1_CPU"],
            dot_color=COLOR_GREEN
        )
        self.ram_card = KPICard(
            "RAM Usage", "%", "DB1_RAM",
            metadata=["Free: 3.2 GB", "Tag: DB1_RAM"],
            dot_color=COLOR_AMBER      # explicit amber dot
        )
        self.hb_card = KPICard(
            "Heartbeat", "", "DB1_HB",
            metadata=["Freq: 2 Hz", "Tag: DB1_HB"],
            dot_color=COLOR_GREEN
        )

        for card in (self.temp_card, self.cpu_card, self.ram_card, self.hb_card):
            kpi_row.addWidget(card)
        left_col.addLayout(kpi_row)

        # 2. Chart
        self.chart = ChartWidget()
        left_col.addWidget(self.chart, stretch=3)

        # 3. System Logs
        self.logs = LogWidget()
        left_col.addWidget(self.logs, stretch=1)

        left_widget = QWidget()
        left_widget.setLayout(left_col)
        main_layout.addWidget(left_widget, stretch=3)

        # ========== RIGHT COLUMN (25%) ==========
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        self.plc_card = PLCCard()
        right_col.addWidget(self.plc_card)

        self.sim_card = SensorSimCard()
        right_col.addWidget(self.sim_card)

        right_col.addStretch()

        right_widget = QWidget()
        right_widget.setLayout(right_col)
        right_widget.setMaximumWidth(320)
        main_layout.addWidget(right_widget, stretch=1)

    def set_live_mode(self, live: bool) -> None:
        """
        Toggle visual feedback for LIVE vs SIMULATION data.
        - Breathing animation on status dots (only in LIVE)
        - Faint cyan glow on chart line (only in LIVE)
        """
        for card in (self.temp_card, self.cpu_card, self.ram_card, self.hb_card):
            card.set_live(live)
        self.chart.set_live_visuals(live)