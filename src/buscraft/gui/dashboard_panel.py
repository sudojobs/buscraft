"""Dashboard panel — the home/landing page users see first.

Shows project stats, quick actions, and recent projects.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QScrollArea, QSizePolicy, QFrame,
)
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from PySide6.QtCore import Qt, Signal, QRect

from buscraft.gui.theme import C, Fonts


# ── Stat Card ──────────────────────────────────────────────────────────────

class _StatCard(QWidget):
    """A stat card showing a metric value and label."""

    def __init__(self, label: str, value: str = "—", accent: str = C.PRIMARY, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._accent = accent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(2)

        # Value
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"color: {C.TEXT}; font-size: 28px; font-weight: bold; background: transparent;")
        layout.addWidget(self.lbl_value)

        # Label
        self.lbl_label = QLabel(label)
        self.lbl_label.setStyleSheet(f"color: {C.TEXT_MUTED}; font-size: 11px; background: transparent;")
        layout.addWidget(self.lbl_label)

    def set_value(self, value: str):
        self.lbl_value.setText(value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Card background
        p.setPen(QPen(QColor(C.BORDER), 1))
        p.setBrush(QColor(C.BG_SURFACE))
        p.drawRoundedRect(1, 1, w - 2, h - 2, 12, 12)

        # Top accent line
        p.setPen(Qt.NoPen)
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0, QColor(self._accent))
        grad.setColorAt(1, QColor(C.BG_SURFACE))
        p.setBrush(grad)
        p.drawRoundedRect(1, 1, w - 2, 3, 2, 2)
        p.end()


# ── Action Card ────────────────────────────────────────────────────────────

class _ActionCard(QWidget):
    """A quick action card with icon and label."""

    clicked = Signal()

    def __init__(self, label: str, description: str = "",
                 primary: bool = False, parent=None):
        super().__init__(parent)
        self._primary = primary
        self._hovered = False

        self.setMinimumSize(150, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(6)

        self.lbl_label = QLabel(label)
        self.lbl_label.setAlignment(Qt.AlignCenter)
        self.lbl_label.setStyleSheet(f"color: {C.TEXT}; font-size: 13px; font-weight: 600; background: transparent;")
        layout.addWidget(self.lbl_label)

        if description:
            self.lbl_desc = QLabel(description)
            self.lbl_desc.setAlignment(Qt.AlignCenter)
            self.lbl_desc.setWordWrap(True)
            self.lbl_desc.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px; background: transparent;")
            layout.addWidget(self.lbl_desc)
        else:
            layout.addStretch()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Card background
        bg = QColor(C.BG_ELEVATED) if self._hovered else QColor(C.BG_SURFACE)
        border_color = QColor(C.PRIMARY if self._primary else C.BORDER)
        if self._hovered:
            border_color = QColor(C.PRIMARY)

        p.setPen(QPen(border_color, 1.5 if (self._primary or self._hovered) else 1))
        p.setBrush(bg)
        p.drawRoundedRect(1, 1, w - 2, h - 2, 12, 12)

        # Glow for primary
        if self._primary and self._hovered:
            glow = QColor(C.PRIMARY)
            glow.setAlpha(20)
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawRoundedRect(-2, -2, w + 4, h + 4, 14, 14)
            # Redraw card on top
            p.setPen(QPen(QColor(C.PRIMARY), 1.5))
            p.setBrush(QColor(C.BG_ELEVATED))
            p.drawRoundedRect(1, 1, w - 2, h - 2, 12, 12)
        p.end()


# ── Recent Project Item ────────────────────────────────────────────────────

class _RecentItem(QWidget):
    """A single recent project list item."""

    clicked = Signal(str)  # emits the file path

    def __init__(self, name: str, path: str, protocols: list[str], timestamp: str, parent=None):
        super().__init__(parent)
        self._name = name
        self._path = path
        self._protocols = protocols[:3]  # max 3 badges
        self._timestamp = timestamp
        self._hovered = False

        self.setFixedHeight(52)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._path)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        if self._hovered:
            p.fillRect(0, 0, w, h, QColor(C.BG_ELEVATED))

        # Name
        p.setPen(QColor(C.TEXT))
        name_font = QFont()
        name_font.setPixelSize(13)
        name_font.setWeight(QFont.DemiBold)
        p.setFont(name_font)
        p.drawText(QRect(12, 8, w - 120, 20), Qt.AlignLeft | Qt.AlignVCenter, self._name)

        # Protocol badges
        badge_x = 12
        badge_font = QFont()
        badge_font.setPixelSize(9)
        badge_font.setWeight(QFont.Medium)
        p.setFont(badge_font)
        for proto in self._protocols:
            label = proto.upper().replace("AMBA_", "")
            fm = p.fontMetrics()
            text_w = fm.horizontalAdvance(label) + 12
            p.setPen(Qt.NoPen)
            badge_bg = QColor(C.PRIMARY_DIM)
            badge_bg.setAlpha(80)
            p.setBrush(badge_bg)
            p.drawRoundedRect(badge_x, 30, text_w, 16, 4, 4)
            p.setPen(QColor(C.PRIMARY))
            p.drawText(QRect(badge_x, 30, text_w, 16), Qt.AlignCenter, label)
            badge_x += text_w + 4

        # Timestamp
        p.setPen(QColor(C.TEXT_DIM))
        ts_font = QFont()
        ts_font.setPixelSize(10)
        p.setFont(ts_font)
        p.drawText(QRect(w - 110, 8, 100, 20), Qt.AlignRight | Qt.AlignVCenter, self._timestamp)

        # Bottom border
        p.setPen(QPen(QColor(C.BORDER), 0.5))
        p.drawLine(12, h - 1, w - 12, h - 1)

        p.end()


# ── Dashboard Panel ────────────────────────────────────────────────────────

class DashboardPanel(QWidget):
    """Home / dashboard page with project overview and quick actions."""

    # Signals for quick action clicks
    action_new_project = Signal()
    action_import_spec = Signal()
    action_generate = Signal()
    action_visualize = Signal()
    open_recent = Signal(str)  # file path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)

        # ── Welcome header ──
        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # ── Stat cards row ──
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        self.stat_agents = _StatCard("Active Agents", "0", C.PRIMARY)
        self.stat_protocols = _StatCard("Protocols Used", "0", C.SECONDARY)
        self.stat_generated = _StatCard("Last Generated", "Never", C.SUCCESS)

        stats_layout.addWidget(self.stat_agents)
        stats_layout.addWidget(self.stat_protocols)
        stats_layout.addWidget(self.stat_generated)
        layout.addLayout(stats_layout)

        # ── Quick actions ──
        actions_title = QLabel("Quick Actions")
        actions_title.setObjectName("sectionTitle")
        layout.addWidget(actions_title)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(16)

        btn_new = _ActionCard("New Project", "Start from scratch")
        btn_spec = _ActionCard("Import Spec", "From PDF or text")
        btn_gen = _ActionCard("Generate Code", "Run UVM generator", primary=True)
        btn_viz = _ActionCard("View Diagrams", "Architecture view")

        btn_new.clicked.connect(self.action_new_project.emit)
        btn_spec.clicked.connect(self.action_import_spec.emit)
        btn_gen.clicked.connect(self.action_generate.emit)
        btn_viz.clicked.connect(self.action_visualize.emit)

        actions_layout.addWidget(btn_new)
        actions_layout.addWidget(btn_spec)
        actions_layout.addWidget(btn_gen)
        actions_layout.addWidget(btn_viz)
        layout.addLayout(actions_layout)

        # ── Recent projects ──
        recent_title = QLabel("Recent Projects")
        recent_title.setObjectName("sectionTitle")
        layout.addWidget(recent_title)

        self.recent_container = QVBoxLayout()
        self.recent_container.setSpacing(0)

        self._no_recent_label = QLabel("No recent projects. Use 'New Project' or 'Import Spec' to get started.")
        self._no_recent_label.setObjectName("mutedLabel")
        self._no_recent_label.setStyleSheet(f"""
            color: {C.TEXT_DIM};
            font-size: {Fonts.BODY}px;
            padding: 20px;
        """)
        self.recent_container.addWidget(self._no_recent_label)

        # Wrap in a card
        recent_card = QWidget()
        recent_card.setObjectName("recentCard")
        recent_card.setStyleSheet(f"""
            QWidget#recentCard {{
                background: {C.BG_SURFACE};
                border: 1px solid {C.BORDER};
                border-radius: 12px;
            }}
        """)
        recent_card.setLayout(self.recent_container)
        layout.addWidget(recent_card)

        layout.addStretch()

        scroll.setWidget(content)

        # Root layout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def update_stats(self, agent_count: int = 0, protocol_count: int = 0,
                     last_generated: str = "Never"):
        """Update the stat cards."""
        self.stat_agents.set_value(str(agent_count))
        self.stat_protocols.set_value(str(protocol_count))
        self.stat_generated.set_value(last_generated)

    def set_recent_projects(self, projects: list[dict]):
        """Set the recent projects list.

        Each dict should have: name, path, protocols (list), timestamp (str).
        """
        # Clear existing items
        while self.recent_container.count():
            child = self.recent_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not projects:
            self._no_recent_label = QLabel(
                "No recent projects. Use 'New Project' or 'Import Spec' to get started."
            )
            self._no_recent_label.setStyleSheet(f"""
                color: {C.TEXT_DIM};
                font-size: {Fonts.BODY}px;
                padding: 20px;
            """)
            self.recent_container.addWidget(self._no_recent_label)
            return

        for proj in projects[:8]:  # max 8
            item = _RecentItem(
                name=proj.get("name", "Untitled"),
                path=proj.get("path", ""),
                protocols=proj.get("protocols", []),
                timestamp=proj.get("timestamp", ""),
            )
            item.clicked.connect(self.open_recent.emit)
            self.recent_container.addWidget(item)
