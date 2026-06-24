"""Dependency checker / installer dialog — GUI equivalent of the CLI 'install' command."""
from __future__ import annotations
import shutil
import sys

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialogButtonBox, QLabel,
    QPushButton, QMessageBox,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, QProcess


class InstallDialog(QDialog):
    """Dialog for checking and installing BusCraft dependencies."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Check Dependencies")
        self.setMinimumSize(580, 340)
        self._processes: list[QProcess] = []
        self._build_ui()
        self._check_all()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "BusCraft requires some external tools. "
            "Check their status and install if needed."
        ))

        self.table = QTableWidget(3, 4)
        self.table.setHorizontalHeaderLabels(["Dependency", "Status", "Details", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)

        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _check_all(self):
        deps = [
            self._check_graphviz(),
            self._check_gtkwave(),
            self._check_ai_model(),
        ]

        for row, (name, installed, details, install_cmd) in enumerate(deps):
            self.table.setItem(row, 0, QTableWidgetItem(name))

            status_item = QTableWidgetItem("✓ Installed" if installed else "✗ Not Found")
            status_item.setForeground(
                QColor(100, 220, 100) if installed else QColor(255, 100, 100)
            )
            self.table.setItem(row, 1, status_item)
            self.table.setItem(row, 2, QTableWidgetItem(details))

            if not installed and install_cmd:
                btn = QPushButton("Install")
                btn.clicked.connect(lambda checked, cmd=install_cmd, r=row: self._on_install(cmd, r))
                self.table.setCellWidget(row, 3, btn)
            else:
                self.table.setItem(row, 3, QTableWidgetItem("—"))

    @staticmethod
    def _check_graphviz() -> tuple:
        dot_path = shutil.which("dot")
        if dot_path:
            return ("Graphviz", True, f"Found: {dot_path}", None)
        if sys.platform == "darwin" and shutil.which("brew"):
            return ("Graphviz", False, "For block diagram generation", ["brew", "install", "graphviz"])
        elif sys.platform == "linux":
            return ("Graphviz", False, "Run: sudo apt install graphviz", None)
        return ("Graphviz", False, "Please install manually", None)

    @staticmethod
    def _check_gtkwave() -> tuple:
        gtkw_path = shutil.which("gtkwave")
        if gtkw_path:
            return ("GTKWave", True, f"Found: {gtkw_path}", None)
        if sys.platform == "darwin" and shutil.which("brew"):
            return ("GTKWave", False, "For waveform viewing", ["brew", "install", "--cask", "gtkwave"])
        elif sys.platform == "linux":
            return ("GTKWave", False, "Run: sudo apt install gtkwave", None)
        return ("GTKWave", False, "Please install manually", None)

    @staticmethod
    def _check_ai_model() -> tuple:
        try:
            from huggingface_hub import try_to_load_from_cache
            cached = try_to_load_from_cache(
                repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
                filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf",
            )
            if cached and cached is not None:
                return ("AI Model (Qwen 7B)", True, f"Cached", None)
        except Exception:
            pass
        return ("AI Model (Qwen 7B)", False, "~4 GB download from HuggingFace", None)

    def _on_install(self, cmd: list[str], row: int):
        self.lbl_status.setText(f"Installing {self.table.item(row, 0).text()}…")

        # Disable the button
        widget = self.table.cellWidget(row, 3)
        if widget:
            widget.setEnabled(False)

        proc = QProcess(self)
        self._processes.append(proc)

        def on_finished(exit_code, exit_status):
            if exit_code == 0:
                self.table.item(row, 1).setText("✓ Installed")
                self.table.item(row, 1).setForeground(QColor(100, 220, 100))
                self.lbl_status.setText(f"{self.table.item(row, 0).text()} installed successfully.")
            else:
                stderr = proc.readAllStandardError().data().decode(errors="replace")
                self.lbl_status.setText(f"Installation failed (exit {exit_code}).")
                QMessageBox.warning(self, "Install Failed", stderr or "Unknown error")
                if widget:
                    widget.setEnabled(True)

        proc.finished.connect(on_finished)
        proc.start(cmd[0], cmd[1:])
