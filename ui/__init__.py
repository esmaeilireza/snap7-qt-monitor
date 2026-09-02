# demo/ui/__init__.py
"""
UI Package for S7 SCADA Dashboard.

Exposes the main window class and the global stylesheet for convenience.
"""

from .theme import GLOBAL_QSS
from .dashboard_ui import MainWindow

__all__ = [
    "GLOBAL_QSS",
    "MainWindow",
]