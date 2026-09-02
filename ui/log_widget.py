# demo/ui/log_widget.py
"""
System Logs Terminal Panel
Matches Visual Spec:
  - Near-black background (#080b10)
  - Monospace typography
  - Color-coded log levels: INFO (green), WARN (amber), ERROR (red)
  - Amber timestamps [HH:MM:SS]
  - Source keywords (FORK, SYSTEM, WORKER, PLC) in bold cyan/white
  - Line spacing ~1.6
  - "Clear" ghost button
  - Auto‑scroll and line trimming (max 200 lines)
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
)
from PySide6.QtCore import Qt
from .theme import (
    COLOR_BG_DEEP, COLOR_PANEL, COLOR_BORDER, COLOR_TERMINAL_BG,
    COLOR_ACCENT, COLOR_AMBER, COLOR_GREEN, COLOR_RED,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_FAINT,
    FONT_MONO, FONT_UI
)


class LogWidget(QFrame):
    """System logs terminal with color‑coded entries and auto‑scroll."""

    MAX_LINES = 200  # maximum number of lines kept in memory

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # Header row: title + "Clear" ghost button
        header = QHBoxLayout()
        title = QLabel("System Logs")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_UI};")
        header.addWidget(title)
        header.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("class", "ghost-btn")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        # Terminal body – read‑only QTextEdit with HTML rendering
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLOR_TERMINAL_BG};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 12px;
                font-family: {FONT_MONO};
                font-size: 13px;
                color: {COLOR_TEXT_PRIMARY};
                line-height: 1.6;
            }}
        """)
        layout.addWidget(self.terminal)

    def log(self, level: str, source: str, message: str) -> None:
        """
        Append a formatted log line.

        Args:
            level: 'INFO', 'WARN', or 'ERROR' (case‑insensitive)
            source: e.g., 'SYSTEM', 'PLC', 'WORKER', 'SIM', etc.
            message: the log text
        """
        ts = datetime.now().strftime("%H:%M:%S")
        level_upper = level.upper()

        # Map level to color
        level_colors = {
            "INFO": COLOR_GREEN,
            "WARN": COLOR_AMBER,
            "ERROR": COLOR_RED,
        }
        level_color = level_colors.get(level_upper, COLOR_TEXT_SECONDARY)

        # Source styling: bold cyan for PLC/WORKER/FORK, white otherwise
        if source.upper() in ("FORK", "PLC", "WORKER"):
            src_color = COLOR_ACCENT
        else:
            src_color = "#ffffff"  # white

        # Build HTML line
        html = (
            f'<span style="color:{COLOR_AMBER}">[{ts}]</span> '
            f'<span style="color:{level_color}">[{level_upper}]</span> '
            f'<span style="color:{src_color}; font-weight:bold">{source}</span>: '
            f'<span style="color:{COLOR_TEXT_PRIMARY}">{message}</span>'
        )
        self.terminal.append(html)

        # Trim old lines to avoid memory bloat
        doc = self.terminal.document()
        while doc.blockCount() > self.MAX_LINES:
            cursor = self.terminal.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

        # Auto‑scroll to bottom
        sb = self.terminal.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self) -> None:
        """Clear all log entries."""
        self.terminal.clear()