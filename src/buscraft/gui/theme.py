"""BusCraft Design System — colours, typography, and QSS stylesheet.

Every widget in the application is styled through this module.
Call ``apply_theme(app)`` once at startup.
"""
from __future__ import annotations

from PySide6.QtGui import QPalette, QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


# ── Colour Palette ──────────────────────────────────────────────────────────

class C:
    """Colour constants used throughout the application."""

    # Backgrounds
    BG_DARKEST   = "#12131e"   # window / app background
    BG_DARK      = "#1a1b2e"   # main content area
    BG_SURFACE   = "#242640"   # cards, panels
    BG_ELEVATED  = "#2d2f4a"   # hover states, popups, tooltips
    BG_INPUT     = "#1e2035"   # text input fields

    # Borders
    BORDER       = "#363858"
    BORDER_LIGHT = "#434670"

    # Accents
    PRIMARY      = "#00bcd4"   # cyan — primary actions
    PRIMARY_DIM  = "#008c9e"   # darker cyan for borders/subtle use
    SECONDARY    = "#7c3aed"   # purple — secondary accent
    SECONDARY_DIM = "#5b21b6"

    # Semantic
    SUCCESS      = "#22c55e"
    WARNING      = "#f59e0b"
    ERROR        = "#ef4444"
    INFO         = "#3b82f6"

    # Text
    TEXT         = "#e2e8f0"   # primary text
    TEXT_MUTED   = "#94a3b8"   # secondary text
    TEXT_DIM     = "#64748b"   # tertiary / placeholder
    TEXT_ON_PRIMARY = "#0a0b14"  # dark text on cyan buttons

    # Navigation
    NAV_BG       = "#141524"
    NAV_ACTIVE   = "#1e2040"
    NAV_HOVER    = "#1a1c38"
    NAV_INDICATOR = PRIMARY

    # Misc
    SCROLLBAR    = "#3a3d5c"
    SCROLLBAR_HOVER = "#4a4d7c"


# ── Typography ──────────────────────────────────────────────────────────────

class Fonts:
    """Font families and sizes."""

    # Families (with fallbacks)
    FAMILY      = "SF Pro Text, Segoe UI, Helvetica Neue, Arial, sans-serif"
    MONO        = "SF Mono, Menlo, Consolas, monospace"

    # Sizes
    TITLE       = 20
    HEADING     = 16
    BODY        = 13
    SMALL       = 11
    TINY        = 10


# ── QSS Stylesheet ─────────────────────────────────────────────────────────

def _build_stylesheet() -> str:
    """Build the complete QSS stylesheet string."""
    return f"""
    /* ── Global ─────────────────────────────────────────── */

    * {{
        font-family: {Fonts.FAMILY};
        color: {C.TEXT};
        outline: none;
    }}

    QMainWindow {{
        background: {C.BG_DARKEST};
    }}

    QWidget {{
        background: transparent;
    }}

    QWidget#centralWidget {{
        background: {C.BG_DARKEST};
    }}

    /* ── Labels ─────────────────────────────────────────── */

    QLabel {{
        background: transparent;
        padding: 0;
    }}

    QLabel#sectionTitle {{
        font-size: {Fonts.HEADING}px;
        font-weight: 600;
        color: {C.TEXT};
    }}

    QLabel#pageTitle {{
        font-size: {Fonts.TITLE}px;
        font-weight: 700;
        color: {C.TEXT};
    }}

    QLabel#mutedLabel {{
        color: {C.TEXT_MUTED};
        font-size: {Fonts.SMALL}px;
    }}

    /* ── Buttons ────────────────────────────────────────── */

    QPushButton {{
        background: {C.BG_ELEVATED};
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
        padding: 8px 18px;
        font-size: {Fonts.BODY}px;
        font-weight: 500;
        min-height: 18px;
    }}

    QPushButton:hover {{
        background: {C.BORDER};
        border-color: {C.BORDER_LIGHT};
    }}

    QPushButton:pressed {{
        background: {C.BG_SURFACE};
    }}

    QPushButton:disabled {{
        background: {C.BG_DARK};
        color: {C.TEXT_DIM};
        border-color: {C.BG_SURFACE};
    }}

    QPushButton#primaryButton {{
        background: {C.PRIMARY};
        color: {C.TEXT_ON_PRIMARY};
        border: none;
        font-weight: 600;
    }}

    QPushButton#primaryButton:hover {{
        background: {C.PRIMARY_DIM};
        color: {C.TEXT};
    }}

    QPushButton#primaryButton:pressed {{
        background: #007a8a;
    }}

    QPushButton#dangerButton {{
        background: transparent;
        color: {C.ERROR};
        border: 1px solid {C.ERROR};
    }}

    QPushButton#dangerButton:hover {{
        background: {C.ERROR};
        color: white;
    }}

    QPushButton#generateCTA {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {C.PRIMARY}, stop:1 {C.SECONDARY});
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 28px;
        font-weight: 700;
        font-size: 13px;
    }}

    QPushButton#generateCTA:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {C.PRIMARY_DIM}, stop:1 {C.SECONDARY_DIM});
    }}

    QPushButton#iconButton {{
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 6px;
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
    }}

    QPushButton#iconButton:hover {{
        background: {C.BG_ELEVATED};
    }}

    /* ── Inputs ─────────────────────────────────────────── */

    QLineEdit {{
        background: {C.BG_INPUT};
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: {Fonts.BODY}px;
        selection-background-color: {C.PRIMARY_DIM};
    }}

    QLineEdit:focus {{
        border-color: {C.PRIMARY};
    }}

    QLineEdit:disabled {{
        background: {C.BG_DARK};
        color: {C.TEXT_DIM};
    }}

    QLineEdit#searchInput {{
        border-radius: 18px;
        padding-left: 16px;
    }}

    /* ── Text Edits ─────────────────────────────────────── */

    QTextEdit {{
        background: {C.BG_INPUT};
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
        padding: 8px;
        font-family: {Fonts.MONO};
        font-size: {Fonts.BODY}px;
        selection-background-color: {C.PRIMARY_DIM};
    }}

    QTextEdit:focus {{
        border-color: {C.PRIMARY};
    }}

    /* ── ComboBox ───────────────────────────────────────── */

    QComboBox {{
        background: {C.BG_INPUT};
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
        padding: 6px 12px;
        min-height: 20px;
    }}

    QComboBox:hover {{
        border-color: {C.BORDER_LIGHT};
    }}

    QComboBox:focus {{
        border-color: {C.PRIMARY};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}

    QComboBox::down-arrow {{
        image: none;
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {C.TEXT_MUTED};
    }}

    QComboBox QAbstractItemView {{
        background: {C.BG_ELEVATED};
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
        padding: 4px;
        selection-background-color: {C.PRIMARY_DIM};
        outline: none;
    }}

    /* ── CheckBox ───────────────────────────────────────── */

    QCheckBox {{
        spacing: 8px;
        color: {C.TEXT};
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {C.BORDER_LIGHT};
        border-radius: 4px;
        background: {C.BG_INPUT};
    }}

    QCheckBox::indicator:checked {{
        background: {C.PRIMARY};
        border-color: {C.PRIMARY};
    }}

    QCheckBox::indicator:hover {{
        border-color: {C.PRIMARY};
    }}

    /* ── Scroll Bars ────────────────────────────────────── */

    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: {C.SCROLLBAR};
        border-radius: 4px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {C.SCROLLBAR_HOVER};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background: {C.SCROLLBAR};
        border-radius: 4px;
        min-width: 30px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {C.SCROLLBAR_HOVER};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}

    /* ── Scroll Area ────────────────────────────────────── */

    QScrollArea {{
        border: none;
        background: transparent;
    }}

    /* ── Group Boxes ────────────────────────────────────── */

    QGroupBox {{
        background: {C.BG_SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 12px;
        margin-top: 16px;
        padding: 20px 16px 16px 16px;
        font-weight: 600;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        color: {C.TEXT};
        font-size: {Fonts.BODY}px;
    }}

    /* ── Tables ─────────────────────────────────────────── */

    QTableWidget {{
        background: {C.BG_SURFACE};
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
        gridline-color: {C.BORDER};
        selection-background-color: {C.PRIMARY_DIM};
    }}

    QTableWidget::item {{
        padding: 6px;
    }}

    QHeaderView::section {{
        background: {C.BG_ELEVATED};
        color: {C.TEXT_MUTED};
        border: none;
        border-bottom: 1px solid {C.BORDER};
        padding: 8px;
        font-weight: 600;
        font-size: {Fonts.SMALL}px;
        text-transform: uppercase;
    }}

    /* ── Progress Bar ──────────────────────────────────── */

    QProgressBar {{
        background: {C.BG_INPUT};
        border: none;
        border-radius: 4px;
        height: 6px;
        text-align: center;
        color: transparent;
    }}

    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {C.PRIMARY}, stop:1 {C.SECONDARY});
        border-radius: 4px;
    }}

    /* ── Tab Widget (fallback for any remaining tabs) ──── */

    QTabWidget::pane {{
        border: 1px solid {C.BORDER};
        border-radius: 8px;
        background: {C.BG_SURFACE};
    }}

    QTabBar::tab {{
        background: {C.BG_DARK};
        color: {C.TEXT_MUTED};
        border: none;
        padding: 10px 20px;
        margin-right: 2px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}

    QTabBar::tab:selected {{
        background: {C.BG_SURFACE};
        color: {C.TEXT};
    }}

    QTabBar::tab:hover:!selected {{
        background: {C.BG_ELEVATED};
        color: {C.TEXT};
    }}

    /* ── Tooltips ───────────────────────────────────────── */

    QToolTip {{
        background: {C.BG_ELEVATED};
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: {Fonts.SMALL}px;
    }}

    /* ── Menu Bar ───────────────────────────────────────── */

    QMenuBar {{
        background: {C.BG_DARKEST};
        color: {C.TEXT_MUTED};
        border: none;
        padding: 2px;
    }}

    QMenuBar::item {{
        background: transparent;
        padding: 6px 12px;
        border-radius: 4px;
    }}

    QMenuBar::item:selected {{
        background: {C.BG_ELEVATED};
        color: {C.TEXT};
    }}

    QMenu {{
        background: {C.BG_ELEVATED};
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 8px 32px 8px 16px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background: {C.PRIMARY_DIM};
    }}

    QMenu::separator {{
        height: 1px;
        background: {C.BORDER};
        margin: 4px 8px;
    }}

    /* ── Dialogs ────────────────────────────────────────── */

    QDialog {{
        background: {C.BG_DARK};
    }}

    QDialogButtonBox QPushButton {{
        min-width: 80px;
    }}

    /* ── Message Box ────────────────────────────────────── */

    QMessageBox {{
        background: {C.BG_DARK};
    }}

    QMessageBox QLabel {{
        color: {C.TEXT};
        font-size: {Fonts.BODY}px;
    }}

    /* ── Splitter ───────────────────────────────────────── */

    QSplitter::handle {{
        background: {C.BORDER};
    }}

    QSplitter::handle:horizontal {{
        width: 1px;
    }}

    QSplitter::handle:vertical {{
        height: 1px;
    }}

    /* ── Status Bar ─────────────────────────────────────── */

    QStatusBar {{
        background: {C.BG_DARKEST};
        color: {C.TEXT_MUTED};
        border-top: 1px solid {C.BORDER};
        font-size: {Fonts.SMALL}px;
    }}

    QStatusBar QLabel {{
        color: {C.TEXT_MUTED};
        font-size: {Fonts.SMALL}px;
    }}

    /* ── Form Layout ────────────────────────────────────── */

    QFormLayout {{
        spacing: 12px;
    }}

    /* ── File Dialog ────────────────────────────────────── */

    QFileDialog {{
        background: {C.BG_DARK};
    }}
    """


# ── Public API ──────────────────────────────────────────────────────────────

_STYLESHEET: str | None = None


def apply_theme(app: QApplication) -> None:
    """Apply the BusCraft dark theme to the entire application."""

    # Palette (for widgets that don't fully respect QSS)
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(C.BG_DARKEST))
    palette.setColor(QPalette.WindowText,      QColor(C.TEXT))
    palette.setColor(QPalette.Base,            QColor(C.BG_INPUT))
    palette.setColor(QPalette.AlternateBase,   QColor(C.BG_SURFACE))
    palette.setColor(QPalette.Text,            QColor(C.TEXT))
    palette.setColor(QPalette.Button,          QColor(C.BG_ELEVATED))
    palette.setColor(QPalette.ButtonText,      QColor(C.TEXT))
    palette.setColor(QPalette.Highlight,       QColor(C.PRIMARY))
    palette.setColor(QPalette.HighlightedText, QColor(C.TEXT_ON_PRIMARY))
    palette.setColor(QPalette.Link,            QColor(C.PRIMARY))
    palette.setColor(QPalette.BrightText,      QColor(C.WARNING))
    palette.setColor(QPalette.ToolTipBase,     QColor(C.BG_ELEVATED))
    palette.setColor(QPalette.ToolTipText,     QColor(C.TEXT))
    palette.setColor(QPalette.PlaceholderText, QColor(C.TEXT_DIM))

    app.setPalette(palette)
    app.setStyle("Fusion")

    global _STYLESHEET
    _STYLESHEET = _build_stylesheet()
    app.setStyleSheet(_STYLESHEET)


# Keep backward compat — old code calls apply_dark_theme(app)
apply_dark_theme = apply_theme
