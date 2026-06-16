"""SLS brand stylesheet and colour constants for the SynthPop Desktop app."""

# ── Palette ───────────────────────────────────────────────────────────────────
PURPLE       = "#9063CD"   # SLS brand accent (Twitter link colour on sls.lscs.ac.uk)
PURPLE_DARK  = "#5a3a8e"   # Header, group-box titles
PURPLE_HOVER = "#7a4fb5"
PURPLE_LIGHT = "#ede8f8"   # Alternating rows, hover tints
GREEN        = "#61a229"   # Confirm / generate (from site's accept-button colour)
GREEN_HOVER  = "#4e8221"
GREEN_DARK   = "#3d6519"
RED          = "#c0392b"
BG           = "#f4f1fa"   # Window / pane background
TEXT         = "#333333"
MUTED        = "#777777"
BORDER       = "#d0c5e8"

APP_QSS = f"""

/* ── Base ────────────────────────────────────────────── */
QWidget {{
    font-family: Arial, sans-serif;
    font-size: 12px;
    color: {TEXT};
}}
QMainWindow {{
    background: {BG};
}}

/* ── Tab widget ──────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-top: none;
    background: {BG};
}}
QTabBar::tab {{
    background: #e0d8f0;
    color: #555555;
    padding: 7px 20px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
    font-size: 12px;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    background: {PURPLE};
    color: white;
    font-weight: bold;
    border-color: {PURPLE};
}}
QTabBar::tab:hover:!selected {{
    background: #c9b8e8;
    color: #222222;
}}
QTabBar::tab:disabled {{
    color: #aaaaaa;
    background: #ece8f5;
}}

/* ── Buttons — default (outline purple) ──────────────── */
QPushButton {{
    border: 1px solid {PURPLE};
    border-radius: 4px;
    padding: 5px 14px;
    background: white;
    color: {PURPLE};
    min-height: 24px;
}}
QPushButton:hover {{
    background: {PURPLE_LIGHT};
}}
QPushButton:pressed {{
    background: #c9b8e8;
}}
QPushButton:disabled {{
    color: #aaaaaa;
    border-color: #cccccc;
    background: #f5f5f5;
}}

/* Primary action — green filled */
QPushButton[role="primary"] {{
    background: {GREEN};
    color: white;
    border: 1px solid {GREEN_HOVER};
    font-weight: bold;
}}
QPushButton[role="primary"]:hover {{
    background: {GREEN_HOVER};
}}
QPushButton[role="primary"]:pressed {{
    background: {GREEN_DARK};
}}
QPushButton[role="primary"]:disabled {{
    background: #b5d68a;
    border-color: #b5d68a;
    color: white;
}}

/* Export action — purple filled */
QPushButton[role="export"] {{
    background: {PURPLE};
    color: white;
    border: 1px solid {PURPLE_HOVER};
    font-weight: bold;
}}
QPushButton[role="export"]:hover {{
    background: {PURPLE_HOVER};
}}
QPushButton[role="export"]:pressed {{
    background: {PURPLE_DARK};
}}
QPushButton[role="export"]:disabled {{
    background: #c9b8e8;
    border-color: #c9b8e8;
    color: white;
}}

/* Cancel — outline red */
QPushButton[role="cancel"] {{
    background: white;
    color: {RED};
    border: 1px solid {RED};
    font-weight: normal;
}}
QPushButton[role="cancel"]:hover {{
    background: #fdf0ee;
}}
QPushButton[role="cancel"]:disabled {{
    color: #ccaaaa;
    border-color: #ccaaaa;
}}

/* ── Progress bars ───────────────────────────────────── */
QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {PURPLE_LIGHT};
    text-align: center;
    color: {PURPLE_DARK};
    min-height: 16px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PURPLE_DARK}, stop:1 {PURPLE});
    border-radius: 3px;
}}

/* ── Group boxes ─────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 5px;
    margin-top: 10px;
    padding: 10px 8px 8px 8px;
    background: white;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    top: -1px;
    color: {PURPLE_DARK};
    font-weight: bold;
    padding: 0 4px;
    background: white;
}}

/* ── Tables ──────────────────────────────────────────── */
QTableWidget {{
    background: white;
    border: 1px solid {BORDER};
    gridline-color: #ece8f5;
    border-radius: 4px;
    alternate-background-color: {PURPLE_LIGHT};
}}
QTableWidget::item {{
    padding: 3px 6px;
}}
QTableWidget::item:selected {{
    background: {PURPLE};
    color: white;
}}
QHeaderView::section {{
    background: {PURPLE_DARK};
    color: white;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #7a52a8;
    font-weight: bold;
    font-size: 11px;
}}
QHeaderView::section:last-child {{
    border-right: none;
}}
QHeaderView::section:horizontal {{
    border-bottom: 1px solid {PURPLE_DARK};
}}
QCornerButton::section {{
    background: {PURPLE_DARK};
    border: none;
}}

/* ── List widgets ────────────────────────────────────── */
QListWidget {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 3px 6px;
}}
QListWidget::item:selected {{
    background: {PURPLE};
    color: white;
}}
QListWidget::item:hover:!selected {{
    background: {PURPLE_LIGHT};
}}

/* ── Text browser ────────────────────────────────────── */
QTextBrowser {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 4px;
}}

/* ── Scroll areas ────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}

/* ── Splitter ────────────────────────────────────────── */
QSplitter::handle:horizontal {{
    background: {BORDER};
    width: 2px;
}}

/* ── Status bar ──────────────────────────────────────── */
QStatusBar {{
    background: {PURPLE_DARK};
    color: white;
    font-size: 11px;
    padding: 2px 8px;
}}
QStatusBar::item {{
    border: none;
}}

/* ── Inputs ──────────────────────────────────────────── */
QSpinBox, QComboBox, QLineEdit {{
    background: white;
    border: 1px solid #c8bde0;
    border-radius: 3px;
    padding: 2px 5px;
    min-height: 22px;
}}
QSpinBox:focus, QComboBox:focus, QLineEdit:focus {{
    border-color: {PURPLE};
}}
QComboBox QAbstractItemView {{
    background: white;
    border: 1px solid {BORDER};
    selection-background-color: {PURPLE};
    selection-color: white;
}}

/* ── Checkboxes ──────────────────────────────────────── */
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 2px;
    border: 1px solid #c8bde0;
    background: white;
}}
QCheckBox::indicator:checked {{
    background: {PURPLE};
    border-color: {PURPLE_DARK};
}}
QCheckBox::indicator:hover {{
    border-color: {PURPLE};
}}

/* ── Radio buttons ───────────────────────────────────── */
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 1px solid #c8bde0;
    background: white;
}}
QRadioButton::indicator:checked {{
    background: {PURPLE};
    border-color: {PURPLE_DARK};
}}
QRadioButton::indicator:hover {{
    border-color: {PURPLE};
}}

/* ── Menu bar ────────────────────────────────────────── */
QMenuBar {{
    background: {PURPLE_DARK};
    color: white;
    padding: 2px 4px;
    font-size: 12px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    background: transparent;
    border-radius: 3px;
}}
QMenuBar::item:selected {{
    background: {PURPLE};
}}
QMenu {{
    background: white;
    border: 1px solid {BORDER};
    padding: 4px 0;
}}
QMenu::item {{
    padding: 5px 24px 5px 16px;
    color: {TEXT};
}}
QMenu::item:selected {{
    background: {PURPLE};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}

/* ── Tooltips ────────────────────────────────────────── */
QToolTip {{
    background: {PURPLE_DARK};
    color: white;
    border: none;
    padding: 6px 10px;
    border-radius: 3px;
    font-size: 11px;
}}
"""
