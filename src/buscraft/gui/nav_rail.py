"""Vertical navigation rail — sidebar with icon + label items.

Replaces QTabWidget for top-level navigation.
Emits ``page_changed(str)`` when a nav item is clicked.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSizePolicy,
)
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QFontMetrics
from PySide6.QtCore import Qt, Signal, QRect, QSize, QPropertyAnimation, Property

from buscraft.gui.theme import C, Fonts


# ── Nav Item Data ──────────────────────────────────────────────────────────

NAV_ITEMS = [
    ("dashboard",  "Dashboard"),
    ("agents",     "Agents"),
    ("features",   "Features"),
    ("spec",       "Spec Import"),
    ("visualize",  "Visualize"),
    ("ai",         "AI Assistant"),
]

NAV_BOTTOM_ITEMS = [
    ("settings",   "Settings"),
]


class _NavItem(QWidget):
    """A single navigation item: icon + label, with active/hover states."""

    clicked = Signal(str)  # emits the item key

    ITEM_HEIGHT = 64
    ITEM_WIDTH = 80
    INDICATOR_WIDTH = 3

    def __init__(self, key: str, label: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.label = label
        self._active = False
        self._hovered = False

        self.setFixedSize(self.ITEM_WIDTH, self.ITEM_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool):
        self._active = value
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.key)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        if self._active:
            p.fillRect(0, 0, w, h, QColor(C.NAV_ACTIVE))
        elif self._hovered:
            p.fillRect(0, 0, w, h, QColor(C.NAV_HOVER))

        # Active indicator (left bar)
        if self._active:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C.NAV_INDICATOR))
            p.drawRoundedRect(0, 8, self.INDICATOR_WIDTH, h - 16, 2, 2)

        # Label
        label_color = QColor(C.TEXT) if (self._active or self._hovered) else QColor(C.TEXT_DIM)
        p.setPen(label_color)
        label_font = QFont()
        label_font.setPixelSize(11)
        label_font.setWeight(QFont.DemiBold if self._active else QFont.Medium)
        p.setFont(label_font)
        
        # Center the label vertically and horizontally
        label_rect = QRect(0, 0, w, h)
        p.drawText(label_rect, Qt.AlignCenter, self.label)

        p.end()


class NavRail(QWidget):
    """Vertical navigation rail with icon + label items."""

    page_changed = Signal(str)  # emits the page key

    WIDTH = _NavItem.ITEM_WIDTH

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)
        self.setObjectName("navRail")
        self.setStyleSheet(f"""
            QWidget#navRail {{
                background: {C.NAV_BG};
                border-right: 1px solid {C.BORDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo = QLabel("BC")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedHeight(52)
        logo.setStyleSheet(f"""
            QLabel {{
                color: {C.PRIMARY};
                font-size: 22px;
                font-weight: 800;
                letter-spacing: 2px;
                background: transparent;
                padding-top: 8px;
            }}
        """)
        layout.addWidget(logo)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C.BORDER};")
        layout.addWidget(sep)

        layout.addSpacing(8)

        # Main nav items
        self._items: dict[str, _NavItem] = {}
        for key, label in NAV_ITEMS:
            item = _NavItem(key, label)
            item.clicked.connect(self._on_item_clicked)
            self._items[key] = item
            layout.addWidget(item)

        layout.addStretch()

        # Bottom items
        for key, label in NAV_BOTTOM_ITEMS:
            item = _NavItem(key, label)
            item.clicked.connect(self._on_item_clicked)
            self._items[key] = item
            layout.addWidget(item)

        layout.addSpacing(8)

        # Set first item active
        self._active_key: str = NAV_ITEMS[0][0]
        self._items[self._active_key].active = True

    def set_active(self, key: str):
        """Set the active nav item programmatically."""
        if key not in self._items:
            return
        if key == self._active_key:
            return
        self._items[self._active_key].active = False
        self._active_key = key
        self._items[key].active = True

    def _on_item_clicked(self, key: str):
        if key == self._active_key:
            return
        self._items[self._active_key].active = False
        self._active_key = key
        self._items[key].active = True
        self.page_changed.emit(key)
