# demo/ui/theme.py
"""
Design Tokens & QSS Stylesheets – Immutable Visual Specification.
Provides all colors, fonts, and global styles for the PySide6 desktop dashboard.

Version: 2.4.1
Compliant with the visual specification (dark industrial theme).
"""

# ======================== COLOR TOKENS ========================
COLOR_BG_DEEP = "#0a0e14"          # deepest background (header, sidebar, footer)
COLOR_PANEL = "#121a28"            # card/panel background
COLOR_BORDER = "#1d2836"           # hairline borders
COLOR_ACCENT = "#00c2ff"           # primary cyan accent
COLOR_ACCENT_SOFT = "#7dd3fc"      # lighter cyan (slider thumb, etc.)
COLOR_AMBER = "#eab308"            # warning/setpoint color
COLOR_GREEN = "#22c55e"            # healthy status
COLOR_RED = "#ef4444"              # error/disconnected
COLOR_TEXT_PRIMARY = "#f1f5f9"     # near-white text
COLOR_TEXT_SECONDARY = "#94a3b8"   # grey labels
COLOR_TEXT_FAINT = "#64748b"       # dim metadata
COLOR_TERMINAL_BG = "#080b10"      # log panel background
COLOR_CHART_GRID = "#1c2634"       # faint grid lines
COLOR_ACTIVE_NAV = "#1a2433"       # active sidebar item background

# ======================== TYPOGRAPHY ========================
FONT_UI = "'Inter', 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace"

# ======================== GLOBAL QSS ========================
GLOBAL_QSS = f"""
/* Reset */
QWidget {{
    background-color: {COLOR_BG_DEEP};
    color: {COLOR_TEXT_PRIMARY};
    font-family: {FONT_UI};
    border: none;
    outline: none;
}}

/* Panels (cards) */
QFrame.panel {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 20px;
}}

/* Labels */
QLabel {{
    background: transparent;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.title {{
    font-size: 16px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.kpi-value {{
    font-size: 46px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
    line-height: 1;
    padding: 0;
    margin: 0;
}}

QLabel.kpi-unit {{
    font-size: 20px;
    font-weight: 400;
    color: {COLOR_TEXT_SECONDARY};
    padding-top: 12px;  /* baseline alignment */
}}

QLabel.meta {{
    font-size: 12px;
    color: #8b98a9;
    font-family: {FONT_MONO};
}}

/* Input field for sensor setpoint */
QLineEdit.sim-input {{
    background-color: #0d1420;
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    font-family: {FONT_MONO};
    font-size: 14px;
    color: {COLOR_TEXT_PRIMARY};
}}

QLineEdit.sim-input:focus {{
    border: 1px solid {COLOR_ACCENT};
}}

/* Primary CTA button (Apply Changes) – only saturated element */
QPushButton.apply-btn {{
    background-color: {COLOR_ACCENT};
    color: #000000;
    font-size: 14px;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 12px;
    min-height: 44px;
}}

QPushButton.apply-btn:hover {{
    background-color: {COLOR_ACCENT_SOFT};
}}

QPushButton.apply-btn:pressed {{
    background-color: #0099cc;
}}

/* Ghost button (Clear logs, etc.) */
QPushButton.ghost-btn {{
    background: transparent;
    border: 1px solid {COLOR_BORDER};
    color: {COLOR_TEXT_SECONDARY};
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 13px;
}}

QPushButton.ghost-btn:hover {{
    border-color: {COLOR_TEXT_SECONDARY};
    color: {COLOR_TEXT_PRIMARY};
}}

/* Slider (Sensor Simulator) */
QSlider::groove:horizontal {{
    height: 4px;
    background: #2a3646;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: {COLOR_ACCENT};
}}

QSlider::sub-page:horizontal {{
    background: {COLOR_ACCENT};
    border-radius: 2px;
}}

/* Toast notification */
QFrame.toast {{
    background-color: #1a2433;
    border: 1px solid {COLOR_AMBER};
    border-radius: 8px;
    padding: 12px 20px;
}}

/* Status pill (header) */
QFrame.status-pill {{
    border: 1px solid {COLOR_GREEN};
    border-radius: 12px;
    padding: 4px 12px;
    background: transparent;
}}

QLabel.status-pill-text {{
    font-size: 13px;
    font-family: {FONT_MONO};
    color: {COLOR_GREEN};
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: {COLOR_TERMINAL_BG};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: #2a3646;
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}
"""

# Optional: explicitly export the most important symbols
__all__ = [
    "GLOBAL_QSS",
    "COLOR_BG_DEEP",
    "COLOR_PANEL",
    "COLOR_BORDER",
    "COLOR_ACCENT",
    "COLOR_ACCENT_SOFT",
    "COLOR_AMBER",
    "COLOR_GREEN",
    "COLOR_RED",
    "COLOR_TEXT_PRIMARY",
    "COLOR_TEXT_SECONDARY",
    "COLOR_TEXT_FAINT",
    "COLOR_TERMINAL_BG",
    "COLOR_CHART_GRID",
    "COLOR_ACTIVE_NAV",
    "FONT_UI",
    "FONT_MONO",
]