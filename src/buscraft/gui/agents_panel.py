"""Card-based agents panel — replaces the old QTableWidget approach.

Agents are shown as visual cards with protocol badges, role chips,
and parameter displays.  A detail/properties panel appears on the right
when an agent is selected.
"""
from __future__ import annotations

from typing import List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QComboBox, QSizePolicy,
    QGridLayout, QSpinBox, QFormLayout, QMessageBox,
)
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from PySide6.QtCore import Qt, Signal, QRect

from buscraft.core.models import Project, Agent
from buscraft.core.plugin_manager import get_all_protocols
from buscraft.gui.theme import C, Fonts


# ── Protocol colour mapping ───────────────────────────────────────────────

PROTOCOL_COLORS = {
    "amba_axi": "#7c3aed",   # purple
    "amba_apb": "#3b82f6",   # blue
    "amba_ahb": "#06b6d4",   # cyan
    "amba_chi": "#f43f5e",   # pink
    "serial_i2c": "#f59e0b", # amber
    "generic_blank": "#6b7280", # gray
}


def _proto_color(protocol_id: str) -> str:
    return PROTOCOL_COLORS.get(protocol_id, C.TEXT_MUTED)


def _proto_short(protocol_id: str) -> str:
    """Short display name for a protocol."""
    mapping = {
        "amba_axi": "AXI",
        "amba_apb": "APB",
        "amba_ahb": "AHB",
        "amba_chi": "CHI",
        "serial_i2c": "I2C",
        "generic_blank": "GEN",
    }
    return mapping.get(protocol_id, protocol_id.upper()[:3])


# ── Agent Card ─────────────────────────────────────────────────────────────

class _AgentCard(QWidget):
    """A single agent displayed as a styled card."""

    selected = Signal(int)  # emits the agent index

    CARD_WIDTH = 260
    CARD_HEIGHT = 140

    def __init__(self, index: int, agent: Agent, parent=None):
        super().__init__(parent)
        self.index = index
        self.agent = agent
        self._is_selected = False
        self._hovered = False

        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.index)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        proto_color = QColor(_proto_color(self.agent.protocol_id))

        # Card background
        bg = QColor(C.BG_ELEVATED) if self._hovered else QColor(C.BG_SURFACE)
        border_c = proto_color if self._is_selected else (
            QColor(C.BORDER_LIGHT) if self._hovered else QColor(C.BORDER)
        )
        border_w = 1.5 if self._is_selected else 1.0

        p.setPen(QPen(border_c, border_w))
        p.setBrush(bg)
        p.drawRoundedRect(1, 1, w - 2, h - 2, 12, 12)

        # Top accent strip
        p.setPen(Qt.NoPen)
        p.setBrush(proto_color)
        # Clip to top rounded corners
        p.save()
        p.setClipRect(0, 0, w, 5)
        p.drawRoundedRect(1, 1, w - 2, 14, 12, 12)
        p.restore()

        # Protocol badge
        badge_text = _proto_short(self.agent.protocol_id)
        badge_font = QFont()
        badge_font.setPixelSize(10)
        badge_font.setWeight(QFont.Bold)
        p.setFont(badge_font)
        fm = p.fontMetrics()
        badge_w = fm.horizontalAdvance(badge_text) + 16
        badge_x = 14
        badge_y = 16

        badge_bg = QColor(proto_color)
        badge_bg.setAlpha(40)
        p.setPen(Qt.NoPen)
        p.setBrush(badge_bg)
        p.drawRoundedRect(badge_x, badge_y, badge_w, 22, 6, 6)
        p.setPen(proto_color)
        p.drawText(QRect(badge_x, badge_y, badge_w, 22), Qt.AlignCenter, badge_text)

        # Role badge
        role_text = self.agent.role.capitalize()
        role_x = badge_x + badge_w + 8
        role_w = fm.horizontalAdvance(role_text) + 16
        role_color = QColor(C.SUCCESS) if self.agent.role == "master" else (
            QColor(C.WARNING) if self.agent.role == "slave" else QColor(C.TEXT_DIM)
        )
        role_bg = QColor(role_color)
        role_bg.setAlpha(30)
        p.setPen(Qt.NoPen)
        p.setBrush(role_bg)
        p.drawRoundedRect(role_x, badge_y, role_w, 22, 6, 6)
        p.setPen(role_color)
        p.drawText(QRect(role_x, badge_y, role_w, 22), Qt.AlignCenter, role_text)

        # Agent name
        p.setPen(QColor(C.TEXT))
        name_font = QFont()
        name_font.setPixelSize(15)
        name_font.setWeight(QFont.DemiBold)
        p.setFont(name_font)
        p.drawText(QRect(14, 46, w - 28, 24), Qt.AlignLeft | Qt.AlignVCenter,
                   self.agent.name)

        # Parameter chips
        chip_y = 78
        chip_x = 14
        chip_font = QFont()
        chip_font.setPixelSize(10)
        p.setFont(chip_font)
        fm = p.fontMetrics()

        data_w = self.agent.parameters.get("data_width", 32)
        addr_w = self.agent.parameters.get("addr_width", 32)
        chips = [f"Data: {data_w}b", f"Addr: {addr_w}b", self.agent.vip_mode.upper()]

        for chip_text in chips:
            text_w = fm.horizontalAdvance(chip_text) + 12
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C.BG_DARK))
            p.drawRoundedRect(chip_x, chip_y, text_w, 18, 4, 4)
            p.setPen(QColor(C.TEXT_MUTED))
            p.drawText(QRect(chip_x, chip_y, text_w, 18), Qt.AlignCenter, chip_text)
            chip_x += text_w + 6

        # Selection glow
        if self._is_selected:
            glow = QColor(proto_color)
            glow.setAlpha(15)
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawRoundedRect(-2, -2, w + 4, h + 4, 14, 14)

        p.end()


# ── Agent Detail Panel ─────────────────────────────────────────────────────

class _AgentDetailPanel(QWidget):
    """Right-side properties panel for the selected agent."""

    agent_updated = Signal()

    WIDTH = 280

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)
        self.setObjectName("agentDetail")
        self.setStyleSheet(f"""
            QWidget#agentDetail {{
                background: {C.BG_SURFACE};
                border-left: 1px solid {C.BORDER};
            }}
        """)

        self._agent: Agent | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(16)

        title = QLabel("Agent Properties")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Form
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft)

        # Name
        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Agent name")
        self.ed_name.textChanged.connect(self._on_changed)
        form.addRow("Name", self.ed_name)

        # Protocol
        self.cmb_protocol = QComboBox()
        protocols = get_all_protocols()
        for pid, plugin in protocols.items():
            self.cmb_protocol.addItem(plugin.label, pid)
        self.cmb_protocol.currentIndexChanged.connect(self._on_changed)
        form.addRow("Protocol", self.cmb_protocol)

        # Role
        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["master", "slave", "monitor_only"])
        self.cmb_role.currentIndexChanged.connect(self._on_changed)
        form.addRow("Role", self.cmb_role)

        # Data width
        self.spin_data = QSpinBox()
        self.spin_data.setRange(8, 1024)
        self.spin_data.setSingleStep(8)
        self.spin_data.setValue(32)
        self.spin_data.setSuffix(" bits")
        self.spin_data.valueChanged.connect(self._on_changed)
        form.addRow("Data Width", self.spin_data)

        # Address width
        self.spin_addr = QSpinBox()
        self.spin_addr.setRange(8, 64)
        self.spin_addr.setSingleStep(8)
        self.spin_addr.setValue(32)
        self.spin_addr.setSuffix(" bits")
        self.spin_addr.valueChanged.connect(self._on_changed)
        form.addRow("Addr Width", self.spin_addr)

        # VIP mode
        self.cmb_vip = QComboBox()
        self.cmb_vip.addItems(["full", "placeholder", "blank"])
        self.cmb_vip.currentIndexChanged.connect(self._on_changed)
        form.addRow("VIP Mode", self.cmb_vip)

        layout.addLayout(form)
        layout.addStretch()

        # Delete button
        self.btn_delete = QPushButton("Delete Agent")
        self.btn_delete.setObjectName("dangerButton")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_delete)

        # Initially hidden
        self.setVisible(False)

    def set_agent(self, agent: Agent | None):
        """Load an agent's properties into the form."""
        self._agent = agent
        if agent is None:
            self.setVisible(False)
            return

        self.setVisible(True)
        # Block signals during population
        for w in (self.ed_name, self.cmb_protocol, self.cmb_role,
                  self.spin_data, self.spin_addr, self.cmb_vip):
            w.blockSignals(True)

        self.ed_name.setText(agent.name)

        idx = self.cmb_protocol.findData(agent.protocol_id)
        if idx >= 0:
            self.cmb_protocol.setCurrentIndex(idx)

        role_idx = self.cmb_role.findText(agent.role)
        if role_idx >= 0:
            self.cmb_role.setCurrentIndex(role_idx)

        self.spin_data.setValue(agent.parameters.get("data_width", 32))
        self.spin_addr.setValue(agent.parameters.get("addr_width", 32))

        vip_idx = self.cmb_vip.findText(agent.vip_mode)
        if vip_idx >= 0:
            self.cmb_vip.setCurrentIndex(vip_idx)

        for w in (self.ed_name, self.cmb_protocol, self.cmb_role,
                  self.spin_data, self.spin_addr, self.cmb_vip):
            w.blockSignals(False)

    def _on_changed(self):
        """Sync form values back to the agent object."""
        if self._agent is None:
            return
        self._agent.name = self.ed_name.text().strip() or "unnamed"
        self._agent.protocol_id = self.cmb_protocol.currentData() or "amba_axi"
        self._agent.role = self.cmb_role.currentText()
        self._agent.parameters["data_width"] = self.spin_data.value()
        self._agent.parameters["addr_width"] = self.spin_addr.value()
        self._agent.vip_mode = self.cmb_vip.currentText()
        self.agent_updated.emit()


# ── Agents Panel (main panel) ──────────────────────────────────────────────

class AgentsPanel(QWidget):
    """Card-based agent configuration panel with detail sidebar."""

    agents_changed = Signal()  # emitted when agents list is modified

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Project | None = None
        self._cards: list[_AgentCard] = []
        self._selected_index: int = -1
        self._protocols = get_all_protocols()
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left: Agent cards ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(24, 20, 24, 20)
        left_layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Agents")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        self.btn_add = QPushButton("+ Add Agent")
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self._on_add_agent)
        header.addWidget(self.btn_add)

        self.btn_dup = QPushButton("Duplicate")
        self.btn_dup.setCursor(Qt.PointingHandCursor)
        self.btn_dup.clicked.connect(self._on_duplicate_agent)
        header.addWidget(self.btn_dup)

        left_layout.addLayout(header)

        # Cards scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.cards_widget = QWidget()
        self.cards_layout = QGridLayout(self.cards_widget)
        self.cards_layout.setSpacing(16)
        self.cards_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll.setWidget(self.cards_widget)

        left_layout.addWidget(self.scroll)

        # Empty state
        self._empty_label = QLabel("No agents configured.\nClick '+ Add Agent' to get started.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {C.TEXT_DIM};
            font-size: {Fonts.HEADING}px;
            padding: 60px;
        """)

        root.addWidget(left, stretch=1)

        # ── Right: Detail panel ──
        self.detail = _AgentDetailPanel()
        self.detail.agent_updated.connect(self._on_agent_updated)
        self.detail.btn_delete.clicked.connect(self._on_delete_agent)
        root.addWidget(self.detail)

    def set_project(self, project: Project):
        """Load agents from a project."""
        self.project = project
        self._refresh_cards()

    def sync_to_project(self):
        """Write current agent list back to the project."""
        if self.project is None:
            return
        # Agents are modified in-place via the detail panel, so just
        # ensure protocols_used is current
        self.project.protocols_used = sorted({a.protocol_id for a in self.project.agents})

    # ── Card management ──

    def _refresh_cards(self):
        """Rebuild all cards from the project's agent list."""
        # Clear existing
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()
        self._selected_index = -1
        self.detail.set_agent(None)

        if not self.project or not self.project.agents:
            self._show_empty(True)
            return

        self._show_empty(False)

        for i, agent in enumerate(self.project.agents):
            card = _AgentCard(i, agent)
            card.selected.connect(self._on_card_selected)
            self._cards.append(card)

        self._layout_cards()

        # Select first
        if self._cards:
            self._on_card_selected(0)

    def _layout_cards(self):
        """Arrange cards in a grid."""
        # Clear layout
        while self.cards_layout.count():
            self.cards_layout.takeAt(0)

        cols = max(1, (self.scroll.width() - 48) // (_AgentCard.CARD_WIDTH + 16))
        if cols < 1:
            cols = 2

        for i, card in enumerate(self._cards):
            row = i // cols
            col = i % cols
            self.cards_layout.addWidget(card, row, col)

    def _show_empty(self, show: bool):
        if show:
            if self._empty_label.parent() is None:
                self.cards_layout.addWidget(self._empty_label, 0, 0)
            self._empty_label.setVisible(True)
        else:
            self._empty_label.setVisible(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._cards:
            self._layout_cards()

    # ── Slots ──

    def _on_card_selected(self, index: int):
        if self._selected_index >= 0 and self._selected_index < len(self._cards):
            self._cards[self._selected_index].set_selected(False)
        self._selected_index = index
        if 0 <= index < len(self._cards):
            self._cards[index].set_selected(True)
            self.detail.set_agent(self._cards[index].agent)

    def _on_agent_updated(self):
        """Detail panel changed agent properties — refresh the card."""
        if 0 <= self._selected_index < len(self._cards):
            self._cards[self._selected_index].update()
        self.agents_changed.emit()

    def _on_add_agent(self):
        if self.project is None:
            return
        default_proto = "amba_axi" if "amba_axi" in self._protocols else next(iter(self._protocols.keys()))
        agent = Agent(
            name=f"agent_{len(self.project.agents)}",
            protocol_id=default_proto,
            role="master",
            parameters={"data_width": 32, "addr_width": 32},
            vip_mode="full",
        )
        self.project.agents.append(agent)
        self._refresh_cards()
        # Select the new one
        self._on_card_selected(len(self._cards) - 1)
        self.agents_changed.emit()

    def _on_duplicate_agent(self):
        if self.project is None or self._selected_index < 0:
            return
        src = self.project.agents[self._selected_index]
        dup = Agent(
            name=f"{src.name}_copy",
            protocol_id=src.protocol_id,
            role=src.role,
            parameters=dict(src.parameters),
            vip_mode=src.vip_mode,
        )
        self.project.agents.append(dup)
        self._refresh_cards()
        self._on_card_selected(len(self._cards) - 1)
        self.agents_changed.emit()

    def _on_delete_agent(self):
        if self.project is None or self._selected_index < 0:
            return
        name = self.project.agents[self._selected_index].name
        reply = QMessageBox.question(
            self, "Delete Agent",
            f"Delete agent '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            del self.project.agents[self._selected_index]
            self._refresh_cards()
            self.agents_changed.emit()
