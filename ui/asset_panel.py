# demo/ui/asset_panel.py
"""
Sidebar Navigation Container.

Visual Spec:
  - Fixed width: 190px.
  - Dark background matching header.
  - Vertical list of nav items (icon + label).
  - Active item: lighter panel, 4px cyan left border, white text.
  - Bottom‑pinned status: green dot + "System Healthy".
  - Micro‑interactions: hover effects with smooth (simulated) 200ms transition.

The hover effect is achieved via QSS `:hover` pseudo‑state; the active state
is controlled by a dynamic property `active` that triggers attribute‑based
styling. This allows both hover and active states to work simultaneously.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QTimer
from .theme import COLOR_BG_DEEP, COLOR_GREEN, COLOR_ACCENT, COLOR_TEXT_PRIMARY, FONT_UI


# Navigation items: (icon, label)
NAV_ITEMS = [
    ("🏠", "Dashboard"),
    ("🗄️", "PLC Data"),
    ("🌡️", "Sensors"),
    ("💻", "System Metrics"),
    ("📋", "Logs"),
    ("⚙️", "Settings"),
]


class NavItem(QLabel):
    """A single navigation row with hover and active states."""

    clicked = Signal(str)   # emits the item's internal name

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(f"  {icon}   {label}", parent)
        self.name = label.lower().replace(" ", "_")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)

        # Set up stylesheet with dynamic property for active state
        # and :hover for both active/inactive
        self.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #8b98a9;
                border-left: 4px solid transparent;
                border-radius: 6px;
                padding-left: 16px;
                font-size: 14px;
                font-weight: 500;
                font-family: """ + FONT_UI + """;
            }
            QLabel:hover {
                background: #1a2433;
                color: """ + COLOR_TEXT_PRIMARY + """;
                border-left-color: """ + COLOR_ACCENT + """;
            }
            QLabel[active="true"] {
                background: #1a2433;
                color: """ + COLOR_TEXT_PRIMARY + """;
                border-left: 4px solid """ + COLOR_ACCENT + """;
                padding-left: 12px;
            }
            QLabel[active="true"]:hover {
                background: #1a2433;
                color: """ + COLOR_TEXT_PRIMARY + """;
            }
        """)
        self.setProperty("active", False)
        self._active = False

    def mousePressEvent(self, event):
        self.clicked.emit(self.name)
        super().mousePressEvent(event)

    def set_active(self, active: bool) -> None:
        """Activate or deactivate the item, updating the property and styles."""
        self._active = active
        self.setProperty("active", active)
        # Force a style refresh
        self.style().unpolish(self)
        self.style().polish(self)


class AssetPanel(QFrame):
    """Left sidebar with navigation and system status."""

    nav_selected = Signal(str)  # emits the selected item's name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(190)
        self.setStyleSheet(f"""
            background-color: {COLOR_BG_DEEP};
            border-right: 1px solid #1a2332;
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(2)

        # Logo
        logo = QLabel("⬡ S7 SCADA")
        logo.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: white;
            padding: 0 16px 24px 16px;
            letter-spacing: 1px;
            font-family: {FONT_UI};
        """)
        layout.addWidget(logo)

        # Navigation items
        self.nav_items = {}
        for icon, label in NAV_ITEMS:
            item = NavItem(icon, label)
            item.clicked.connect(self._on_nav_click)
            layout.addWidget(item)
            self.nav_items[item.name] = item

        # Activate Dashboard by default
        self.nav_items["dashboard"].set_active(True)

        layout.addStretch()

        # Bottom‑pinned System Healthy status
        status_row = QVBoxLayout()
        status_row.setContentsMargins(16, 0, 16, 0)

        health_container = QHBoxLayout()
        self.health_dot = QLabel("●")
        self.health_dot.setStyleSheet(f"color:{COLOR_GREEN}; font-size:10px;")
        self.health_text = QLabel("System Healthy")
        self.health_text.setStyleSheet(f"color:{COLOR_GREEN}; font-size:13px; font-family: {FONT_UI};")

        health_container.addWidget(self.health_dot)
        health_container.addWidget(self.health_text)
        health_container.addStretch()
        status_row.addLayout(health_container)
        layout.addLayout(status_row)

    def _on_nav_click(self, name: str) -> None:
        """Update active states and emit signal."""
        for item in self.nav_items.values():
            item.set_active(item.name == name)
        self.nav_selected.emit(name)