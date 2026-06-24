"""Consolidated settings panel — project, license, dependencies, about.

Replaces the old "Project Settings" tab and "License Info" tab,
and absorbs the install dialog contents.
"""
from __future__ import annotations

import shutil
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFormLayout, QScrollArea, QFrame,
    QTextEdit, QFileDialog, QSizePolicy, QGroupBox,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal

from buscraft.core.models import Project
from buscraft.core.license_manager import (
    load_license, get_license_summary, LicenseInfo, create_demo_license,
)
from buscraft.gui.theme import C, Fonts


class _SettingsSection(QWidget):
    """A collapsible settings section with title and content."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsSection")
        self.setStyleSheet(f"""
            QWidget#settingsSection {{
                background: {C.BG_SURFACE};
                border: 1px solid {C.BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {C.TEXT};
            background: transparent;
        """)
        layout.addWidget(lbl)

        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(8)
        layout.addLayout(self._content_layout)

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout


class SettingsPanel(QWidget):
    """Consolidated settings page."""

    license_changed = Signal(object)  # LicenseInfo

    def __init__(self, parent=None):
        super().__init__(parent)
        self._license_info: LicenseInfo | None = create_demo_license()
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # ── Project Settings ──
        proj_section = _SettingsSection("Project")
        proj_form = QFormLayout()
        proj_form.setSpacing(10)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Project name")
        proj_form.addRow("Name", self.ed_name)

        out_row = QHBoxLayout()
        self.ed_output = QLineEdit()
        self.ed_output.setPlaceholderText("Output directory")
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._on_browse_output)
        out_row.addWidget(self.ed_output, stretch=1)
        out_row.addWidget(self.btn_browse)
        proj_form.addRow("Output Dir", out_row)

        self.cmb_sim = QComboBox()
        self.cmb_sim.addItems(["vcs", "questa", "xcelium", "verilator"])
        proj_form.addRow("Simulator", self.cmb_sim)

        proj_section.content_layout().addLayout(proj_form)
        layout.addWidget(proj_section)

        # ── License ──
        lic_section = _SettingsSection("License")

        self.lic_text = QTextEdit()
        self.lic_text.setReadOnly(True)
        self.lic_text.setMaximumHeight(140)
        self.lic_text.setStyleSheet(f"""
            QTextEdit {{
                background: {C.BG_INPUT};
                border-radius: 8px;
                font-family: {Fonts.MONO};
                font-size: {Fonts.SMALL}px;
            }}
        """)
        lic_section.content_layout().addWidget(self.lic_text)

        btn_row = QHBoxLayout()
        self.btn_load_lic = QPushButton("Load License File…")
        self.btn_load_lic.setCursor(Qt.PointingHandCursor)
        self.btn_load_lic.clicked.connect(self._on_load_license)
        btn_row.addWidget(self.btn_load_lic)
        btn_row.addStretch()
        lic_section.content_layout().addLayout(btn_row)

        layout.addWidget(lic_section)

        # ── Dependencies ──
        deps_section = _SettingsSection("Dependencies")

        self.deps_container = QVBoxLayout()
        self.deps_container.setSpacing(8)
        deps_section.content_layout().addLayout(self.deps_container)

        btn_check = QPushButton("Check Dependencies")
        btn_check.setCursor(Qt.PointingHandCursor)
        btn_check.clicked.connect(self._check_deps)
        deps_section.content_layout().addWidget(btn_check)

        layout.addWidget(deps_section)

        # ── About ──
        about_section = _SettingsSection("About")
        about_text = QLabel(
            "BusCraft v0.1.0\n"
            "UVM Verification Environment Generator\n\n"
            "© 2024-2026 BusCraft. All rights reserved."
        )
        about_text.setStyleSheet(f"""
            color: {C.TEXT_MUTED};
            font-size: {Fonts.BODY}px;
            background: transparent;
        """)
        about_section.content_layout().addWidget(about_text)
        layout.addWidget(about_section)

        layout.addStretch()
        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        # Initial state
        self._update_license_view()
        self._check_deps()

    # ── Project sync ──

    def load_from_project(self, project: Project):
        self.ed_name.setText(project.name)
        self.ed_output.setText(project.output_dir)
        idx = self.cmb_sim.findText(project.simulator)
        if idx >= 0:
            self.cmb_sim.setCurrentIndex(idx)

    def save_to_project(self, project: Project):
        project.name = self.ed_name.text().strip() or "untitled"
        project.output_dir = self.ed_output.text().strip() or "./buscraft_out"
        project.simulator = self.cmb_sim.currentText()

    # ── License ──

    def get_license_info(self) -> LicenseInfo | None:
        return self._license_info

    def set_license_info(self, lic: LicenseInfo | None):
        self._license_info = lic
        self._update_license_view()
        self.license_changed.emit(lic)

    def _update_license_view(self):
        self.lic_text.setPlainText(get_license_summary(self._license_info))

    def _on_load_license(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load BusCraft License", "",
            "License (*.json);;All Files (*.*)"
        )
        if not path:
            return
        try:
            lic = load_license(path)
            self.set_license_info(lic)
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to load license:\n{exc}")

    def _on_browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.ed_output.setText(directory)

    # ── Dependencies ──

    def _check_deps(self):
        # Clear existing
        while self.deps_container.count():
            child = self.deps_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        deps = [
            self._check_dep("Graphviz", "dot", "Block diagram generation"),
            self._check_dep("GTKWave", "gtkwave", "Waveform viewing"),
        ]

        # AI model check
        ai_installed = False
        try:
            from huggingface_hub import try_to_load_from_cache
            cached = try_to_load_from_cache(
                repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
                filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf",
            )
            if cached and cached is not None:
                ai_installed = True
        except Exception:
            pass
        deps.append(("AI Model (Qwen 7B)", ai_installed, "~4 GB, for AI assistant"))

        for name, installed, desc in deps:
            row = QHBoxLayout()

            color = C.SUCCESS if installed else C.ERROR
            status = QLabel(f'<span style="color: {color}">{name}</span>')
            status.setStyleSheet(f"background: transparent; font-size: {Fonts.BODY}px;")
            row.addWidget(status)

            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: {Fonts.SMALL}px; background: transparent;")
            row.addWidget(desc_lbl)
            row.addStretch()

            status_text = "Installed" if installed else "Not found"
            st_lbl = QLabel(status_text)
            st_lbl.setStyleSheet(f"""
                color: {C.SUCCESS if installed else C.WARNING};
                font-size: {Fonts.SMALL}px;
                background: transparent;
            """)
            row.addWidget(st_lbl)

            container = QWidget()
            container.setLayout(row)
            self.deps_container.addWidget(container)

    @staticmethod
    def _check_dep(name: str, cmd: str, desc: str) -> tuple:
        return (name, shutil.which(cmd) is not None, desc)
