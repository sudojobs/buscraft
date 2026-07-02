"""Protocol browser dialog — GUI equivalent of the CLI 'list-protocols' command."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialogButtonBox, QLabel,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from buscraft.core.plugin_manager import get_all_protocols


class ProtocolBrowserDialog(QDialog):
    """Read-only dialog listing all available protocol plugins."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Available Protocols")
        self.setMinimumSize(520, 340)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.lbl_count = QLabel()
        layout.addWidget(self.lbl_count)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Family", "Label", "Maturity"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        hint = QLabel(
            "<small>Use these protocol IDs when adding agents in the "
            "Protocols &amp; Agents tab.</small>"
        )
        hint.setTextFormat(Qt.RichText)
        layout.addWidget(hint)

        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _populate(self):
        protocols = get_all_protocols()
        self.lbl_count.setText(f"Available Protocols: {len(protocols)}")
        self.table.setRowCount(len(protocols))

        for row, (pid, plugin) in enumerate(sorted(protocols.items())):
            self.table.setItem(row, 0, QTableWidgetItem(pid))
            self.table.setItem(row, 1, QTableWidgetItem(plugin.family))
            self.table.setItem(row, 2, QTableWidgetItem(plugin.label))

            maturity_item = QTableWidgetItem(plugin.maturity)
            if plugin.maturity == "full":
                maturity_item.setForeground(QColor(100, 220, 100))
            else:
                maturity_item.setForeground(QColor(255, 200, 80))
            self.table.setItem(row, 3, maturity_item)
