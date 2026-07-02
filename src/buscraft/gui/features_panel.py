"""Feature toggle cards panel — replaces bare checkboxes.

Each feature is displayed as a styled card with icon, description,
and a toggle switch.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy, QGridLayout,
)
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, Signal, QRect, QRectF

from buscraft.core.models import Project
from buscraft.gui.theme import C, Fonts


# ── Feature definitions ───────────────────────────────────────────────────

FEATURES = [
    {
        "key": "scoreboard_enable",
        "title": "Scoreboard",
        "desc": "Automatic data integrity checking between master and slave agents.",
        "category": "Verification",
        "accent": C.SUCCESS,
    },
    {
        "key": "coverage_enable",
        "title": "Functional Coverage",
        "desc": "Covergroups for bus states, transitions, and corner cases.",
        "category": "Verification",
        "accent": C.SECONDARY,
    },
    {
        "key": "assertions_enable",
        "title": "SVA Assertions",
        "desc": "Built-in SystemVerilog Assertions for protocol rule checks.",
        "category": "Verification",
        "accent": C.WARNING,
    },
    {
        "key": "sim_scripts_enable",
        "title": "Simulation Scripts",
        "desc": "Auto-generate Makefiles for VCS, Questa, Xcelium, Verilator.",
        "category": "Tooling",
        "accent": C.PRIMARY,
    },
    {
        "key": "ai_assist_enable",
        "title": "AI Assistance",
        "desc": "Enable AI-powered code suggestions and verification insights.",
        "category": "Advanced",
        "accent": "#e040fb",
    },
]


# ── Toggle Switch ──────────────────────────────────────────────────────────

class _ToggleSwitch(QWidget):
    """Custom-painted toggle switch."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, value: bool):
        self._checked = value
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Track
        track_color = QColor(C.PRIMARY) if self._checked else QColor(C.BORDER_LIGHT)
        p.setPen(Qt.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(0, 2, w, h - 4, (h - 4) // 2, (h - 4) // 2)

        # Thumb
        thumb_x = w - h + 4 if self._checked else 4
        p.setBrush(QColor("white") if self._checked else QColor(C.TEXT_MUTED))
        p.drawEllipse(QRectF(thumb_x, 5, h - 10, h - 10))

        p.end()


# ── Feature Card ───────────────────────────────────────────────────────────

class _FeatureCard(QWidget):
    """A feature card with title, description, and toggle."""

    toggled = Signal(str, bool)  # key, checked

    def __init__(self, key: str, title: str, desc: str,
                 accent: str, checked: bool = True, parent=None):
        super().__init__(parent)
        self.key = key
        self._title = title
        self._desc = desc
        self._accent = accent
        self._hovered = False

        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)

        # Build layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(14)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {C.TEXT};
            background: transparent;
        """)
        text_layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            font-size: 11px;
            color: {C.TEXT_MUTED};
            background: transparent;
        """)
        text_layout.addWidget(desc_label)
        layout.addLayout(text_layout, stretch=1)

        # Toggle
        self.toggle = _ToggleSwitch(checked)
        self.toggle.toggled.connect(lambda v: self.toggled.emit(self.key, v))
        layout.addWidget(self.toggle, alignment=Qt.AlignVCenter)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Card background
        bg = QColor(C.BG_ELEVATED) if self._hovered else QColor(C.BG_SURFACE)
        border = QColor(C.BORDER_LIGHT) if self._hovered else QColor(C.BORDER)
        p.setPen(QPen(border, 1))
        p.setBrush(bg)
        p.drawRoundedRect(1, 1, w - 2, h - 2, 12, 12)

        p.end()


# ── Features Panel ─────────────────────────────────────────────────────────

class FeaturesPanel(QWidget):
    """Feature toggles panel with category grouping."""

    features_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict[str, _FeatureCard] = {}
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        title = QLabel("Features & Coverage")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Configure verification features for code generation.")
        subtitle.setObjectName("mutedLabel")
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        # Group by category
        categories: dict[str, list] = {}
        for feat in FEATURES:
            cat = feat["category"]
            categories.setdefault(cat, []).append(feat)

        for cat_name, feats in categories.items():
            cat_label = QLabel(cat_name.upper())
            cat_label.setStyleSheet(f"""
                color: {C.TEXT_DIM};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding-left: 4px;
                background: transparent;
            """)
            layout.addWidget(cat_label)

            for feat in feats:
                card = _FeatureCard(
                    key=feat["key"],
                    title=feat["title"],
                    desc=feat["desc"],
                    accent=feat["accent"],
                    checked=True,
                )
                card.toggled.connect(self._on_toggle)
                self._cards[feat["key"]] = card
                layout.addWidget(card)

            layout.addSpacing(8)

        layout.addStretch()

        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def load_from_project(self, project: Project):
        """Load feature toggles from project."""
        for key, card in self._cards.items():
            checked = project.features.get(key, True)
            card.toggle.checked = checked

    def save_to_project(self, project: Project):
        """Save feature toggles to project."""
        for key, card in self._cards.items():
            project.features[key] = card.toggle.checked

    def _on_toggle(self, key: str, checked: bool):
        self.features_changed.emit()
