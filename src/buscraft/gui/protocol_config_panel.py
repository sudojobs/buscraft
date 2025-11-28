from __future__ import annotations
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QAbstractItemView
)
from PySide6.QtCore import Qt

from buscraft.core.models import Project, Agent
from buscraft.core.plugin_manager import get_all_protocols


class ProtocolConfigPanel(QWidget):
    """Simple table-based panel for configuring agents."""

    HEADERS = ["Name", "Protocol", "Role", "Data Width", "Addr Width", "VIP Mode"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Project | None = None
        self.protocols = get_all_protocols()

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, len(self.HEADERS), self)
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Agent")
        self.btn_remove = QPushButton("Remove Agent")
        self.btn_dup = QPushButton("Duplicate Agent")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_dup)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.btn_add.clicked.connect(self.add_agent_row)
        self.btn_remove.clicked.connect(self.remove_selected_row)
        self.btn_dup.clicked.connect(self.duplicate_selected_row)

    def set_project(self, project: Project) -> None:
        self.project = project
        self._refresh_from_project()

    # ---- internal helpers ----

    def _add_agent_to_table(self, agent: Agent) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(agent.name))

        # Protocol combo
        proto_combo = QComboBox()
        for pid, plugin in self.protocols.items():
            proto_combo.addItem(plugin.label, pid)
        idx = proto_combo.findData(agent.protocol_id)
        if idx >= 0:
            proto_combo.setCurrentIndex(idx)
        self.table.setCellWidget(row, 1, proto_combo)

        # Role
        role_combo = QComboBox()
        for role in ("master", "slave", "monitor_only"):
            role_combo.addItem(role)
        role_idx = role_combo.findText(agent.role)
        if role_idx >= 0:
            role_combo.setCurrentIndex(role_idx)
        self.table.setCellWidget(row, 2, role_combo)

        # Data width
        data_item = QTableWidgetItem(str(agent.parameters.get("data_width", 32)))
        self.table.setItem(row, 3, data_item)

        # Addr width
        addr_item = QTableWidgetItem(str(agent.parameters.get("addr_width", 32)))
        self.table.setItem(row, 4, addr_item)

        # VIP Mode
        vip_combo = QComboBox()
        for mode in ("full", "placeholder", "blank"):
            vip_combo.addItem(mode)
        vip_idx = vip_combo.findText(agent.vip_mode)
        if vip_idx >= 0:
            vip_combo.setCurrentIndex(vip_idx)
        self.table.setCellWidget(row, 5, vip_combo)

    def _refresh_from_project(self) -> None:
        self.table.setRowCount(0)
        if not self.project:
            return
        for agent in self.project.agents:
            self._add_agent_to_table(agent)

    # ---- slots ----

    def add_agent_row(self) -> None:
        default_protocol = "amba_axi" if "amba_axi" in self.protocols else next(iter(self.protocols.keys()))
        agent = Agent(
            name=f"agent_{self.table.rowCount()}",
            protocol_id=default_protocol,
            role="master",
            parameters={"data_width": 32, "addr_width": 32},
            vip_mode="full",
        )
        self._add_agent_to_table(agent)

    def remove_selected_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def duplicate_selected_row(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        agent = self._agent_from_row(row)
        agent.name = f"{agent.name}_copy"
        self._add_agent_to_table(agent)

    def _agent_from_row(self, row: int) -> Agent:
        name = self.table.item(row, 0).text() if self.table.item(row, 0) else f"agent_{row}"

        proto_combo: QComboBox = self.table.cellWidget(row, 1)  # type: ignore
        protocol_id = proto_combo.currentData()

        role_combo: QComboBox = self.table.cellWidget(row, 2)  # type: ignore
        role = role_combo.currentText()

        data_width = int(self.table.item(row, 3).text()) if self.table.item(row, 3) else 32
        addr_width = int(self.table.item(row, 4).text()) if self.table.item(row, 4) else 32

        vip_combo: QComboBox = self.table.cellWidget(row, 5)  # type: ignore
        vip_mode = vip_combo.currentText()

        return Agent(
            name=name,
            protocol_id=protocol_id,
            role=role,
            parameters={"data_width": data_width, "addr_width": addr_width},
            vip_mode=vip_mode,
        )

    def sync_to_project(self) -> None:
        if not self.project:
            return
        agents: List[Agent] = []
        for row in range(self.table.rowCount()):
            agents.append(self._agent_from_row(row))
        self.project.agents = agents
        self.project.protocols_used = sorted({a.protocol_id for a in agents})
