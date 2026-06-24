"""Selective file generation dialog — GUI equivalent of the CLI 'generate' command."""
from __future__ import annotations
from pathlib import Path
from typing import Set

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QGroupBox, QGridLayout, QTextEdit,
    QDialogButtonBox, QProgressBar, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal as QtSignal

from buscraft.core.models import Project
from buscraft.core.generator import FILE_CATEGORIES, MINIMAL_FILES, FULL_FILES
from buscraft.core.license_manager import LicenseInfo


class _GenerateWorker(QThread):
    """Runs code generation on a background thread."""
    finished = QtSignal(dict)  # output_files
    error = QtSignal(str)

    def __init__(self, project: Project, license_info: LicenseInfo | None,
                 selected_files: Set[str]):
        super().__init__()
        self.project = project
        self.license_info = license_info
        self.selected_files = selected_files

    def run(self):
        try:
            from buscraft.core.generator import Generator
            gen = Generator(self.project, self.license_info)
            result = gen.generate_all(selected_files=self.selected_files)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class GenerateDialog(QDialog):
    """Dialog for choosing which UVM file categories to generate."""

    def __init__(self, project: Project, license_info: LicenseInfo | None = None,
                 parent=None):
        super().__init__(parent)
        self.project = project
        self.license_info = license_info
        self._worker: _GenerateWorker | None = None
        self._checkboxes: dict[str, QCheckBox] = {}

        self.setWindowTitle("Generate UVM Code")
        self.setMinimumSize(560, 520)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # --- Category checkboxes ---
        cat_group = QGroupBox("Select file categories to generate")
        grid = QGridLayout(cat_group)

        row = 0
        for key, desc in FILE_CATEGORIES.items():
            cb = QCheckBox(f"{key}")
            cb.setToolTip(desc)
            cb.setChecked(key in FULL_FILES)
            lbl = QLabel(f"  <small>{desc}</small>")
            lbl.setTextFormat(Qt.RichText)
            grid.addWidget(cb, row, 0)
            grid.addWidget(lbl, row, 1)
            self._checkboxes[key] = cb
            row += 1

        root.addWidget(cat_group)

        # --- Preset buttons ---
        preset_row = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_minimal = QPushButton("Minimal (agent + env + scripts)")
        btn_none = QPushButton("Deselect All")
        btn_all.clicked.connect(lambda: self._set_preset(FULL_FILES))
        btn_minimal.clicked.connect(lambda: self._set_preset(MINIMAL_FILES))
        btn_none.clicked.connect(lambda: self._set_preset(set()))
        preset_row.addWidget(btn_all)
        preset_row.addWidget(btn_minimal)
        preset_row.addWidget(btn_none)
        preset_row.addStretch()
        root.addLayout(preset_row)

        # --- Progress ---
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        # --- Results ---
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setVisible(False)
        self.txt_results.setMaximumHeight(180)
        root.addWidget(self.txt_results)

        # --- Buttons ---
        btn_box = QDialogButtonBox()
        self.btn_generate = btn_box.addButton("Generate", QDialogButtonBox.AcceptRole)
        self.btn_close = btn_box.addButton("Close", QDialogButtonBox.RejectRole)
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_close.clicked.connect(self.reject)
        root.addWidget(btn_box)

    # ---------------------------------------------------------------- Helpers

    def _set_preset(self, selected: Set[str]):
        for key, cb in self._checkboxes.items():
            cb.setChecked(key in selected)

    def _get_selected(self) -> Set[str]:
        return {key for key, cb in self._checkboxes.items() if cb.isChecked()}

    # ----------------------------------------------------------------- Slots

    def _on_generate(self):
        selected = self._get_selected()
        if not selected:
            QMessageBox.warning(self, "Nothing Selected",
                                "Please select at least one file category.")
            return

        self.btn_generate.setEnabled(False)
        self.progress.setVisible(True)
        self.txt_results.setVisible(False)
        self.txt_results.clear()

        self._worker = _GenerateWorker(
            self.project, self.license_info, selected
        )
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, output_files: dict):
        self.progress.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.txt_results.setVisible(True)

        lines = [f"Generated {len(output_files)} file(s):\n"]
        for file_type, file_path in output_files.items():
            lines.append(f"  • {file_type}: {file_path}")
        lines.append(f"\nOutput directory: {self.project.output_dir}")
        self.txt_results.setPlainText("\n".join(lines))

    def _on_error(self, msg: str):
        self.progress.setVisible(False)
        self.btn_generate.setEnabled(True)
        QMessageBox.critical(self, "Generation Error", msg)
