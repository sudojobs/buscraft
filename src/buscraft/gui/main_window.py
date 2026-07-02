"""BusCraft Main Window — sidebar + content + status bar layout.

Replaces the old QTabWidget design with a modern IDE-style layout:
  NavRail (left) | Content (center) | StatusBar (bottom)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFileDialog, QMessageBox, QApplication, QDialog,
    QStackedWidget, QSizePolicy,
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from buscraft.core.models import Project
from buscraft.core.project_io import load_project, save_project
from buscraft.core.generator import Generator, GenerationError
from buscraft.core.visualizer import generate_diagram
from buscraft.core.license_manager import (
    load_license, get_license_summary, LicenseInfo, create_demo_license,
)
from buscraft.gui.nav_rail import NavRail
from buscraft.gui.status_bar import StatusBar
from buscraft.gui.dashboard_panel import DashboardPanel
from buscraft.gui.agents_panel import AgentsPanel
from buscraft.gui.features_panel import FeaturesPanel
from buscraft.gui.settings_panel import SettingsPanel
from buscraft.gui.spec_import_panel import SpecImportPanel
from buscraft.gui.visualize_panel import VisualizePanel
from buscraft.gui.ai_panel import AIPanel
from buscraft.gui.generate_dialog import GenerateDialog
from buscraft.gui.project_wizard import ProjectWizard
from buscraft.gui.protocol_browser_dialog import ProtocolBrowserDialog
from buscraft.gui.theme import C


# Map nav keys to stack indices
PAGE_KEYS = ["dashboard", "agents", "features", "spec", "visualize", "ai", "settings"]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BusCraft")
        self.resize(1200, 760)
        self.setMinimumSize(900, 600)

        self.project: Project | None = None
        self.current_project_path: Path | None = None
        self.license_info: LicenseInfo | None = create_demo_license()

        self._create_actions()
        self._create_menu()
        self._create_central()

        self.statusBar().hide()  # Hide Qt's default status bar

    # ──────────────────────────────────────────────── UI Construction ──

    def _create_actions(self) -> None:
        self.act_new = QAction("&New", self)
        self.act_open = QAction("&Open...", self)
        self.act_save = QAction("&Save", self)
        self.act_save_as = QAction("Save &As...", self)
        self.act_exit = QAction("E&xit", self)

        self.act_gen_code = QAction("Generate &Code...", self)
        self.act_gen_diag = QAction("Generate &Diagram", self)
        self.act_load_license = QAction("&Load License...", self)
        self.act_launch_wave = QAction("Launch &Waveform Viewer", self)

        self.act_about = QAction("&About", self)
        self.act_protocols = QAction("&Protocol Browser...", self)

        self.act_new.triggered.connect(self.on_new_project)
        self.act_open.triggered.connect(self.on_open_project)
        self.act_save.triggered.connect(self.on_save_project)
        self.act_save_as.triggered.connect(self.on_save_as_project)
        self.act_exit.triggered.connect(self.close)

        self.act_gen_code.triggered.connect(self.on_generate_code)
        self.act_gen_diag.triggered.connect(self.on_generate_diagram)
        self.act_load_license.triggered.connect(self.on_load_license)
        self.act_launch_wave.triggered.connect(self.on_launch_waveform)

        self.act_about.triggered.connect(self.on_about)
        self.act_protocols.triggered.connect(self.on_protocol_browser)

        # Shortcuts
        self.act_new.setShortcut("Ctrl+N")
        self.act_open.setShortcut("Ctrl+O")
        self.act_save.setShortcut("Ctrl+S")
        self.act_save_as.setShortcut("Ctrl+Shift+S")
        self.act_gen_code.setShortcut("Ctrl+G")

    def _create_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_open)
        file_menu.addSeparator()
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)

        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction(self.act_gen_code)
        tools_menu.addAction(self.act_gen_diag)
        tools_menu.addSeparator()
        tools_menu.addAction(self.act_launch_wave)
        tools_menu.addAction(self.act_load_license)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self.act_protocols)
        help_menu.addSeparator()
        help_menu.addAction(self.act_about)

    def _create_central(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Main area: NavRail + Content ──
        main_area = QHBoxLayout()
        main_area.setContentsMargins(0, 0, 0, 0)
        main_area.setSpacing(0)

        # Nav rail
        self.nav_rail = NavRail()
        self.nav_rail.page_changed.connect(self._on_page_changed)
        main_area.addWidget(self.nav_rail)

        # Content stack
        self.stack = QStackedWidget()
        self.stack.setObjectName("contentStack")
        self.stack.setStyleSheet(f"""
            QStackedWidget#contentStack {{
                background: {C.BG_DARK};
            }}
        """)

        # Create pages in order matching PAGE_KEYS
        self.dashboard = DashboardPanel()
        self.dashboard.action_new_project.connect(self.on_new_project)
        self.dashboard.action_import_spec.connect(lambda: self._navigate_to("spec"))
        self.dashboard.action_generate.connect(self.on_generate_code)
        self.dashboard.action_visualize.connect(lambda: self._navigate_to("visualize"))
        self.dashboard.open_recent.connect(self._on_open_recent)

        self.agents_panel = AgentsPanel()
        self.agents_panel.agents_changed.connect(self._on_agents_changed)

        self.features_panel = FeaturesPanel()

        self.spec_panel = SpecImportPanel()
        self.spec_panel.project_ready.connect(self._on_spec_project_imported)

        self.visualize_panel = VisualizePanel()

        self.ai_panel = AIPanel()

        self.settings_panel = SettingsPanel()
        self.settings_panel.license_changed.connect(self._on_license_changed)

        # Add in PAGE_KEYS order
        self.stack.addWidget(self.dashboard)     # 0: dashboard
        self.stack.addWidget(self.agents_panel)   # 1: agents
        self.stack.addWidget(self.features_panel) # 2: features
        self.stack.addWidget(self.spec_panel)     # 3: spec
        self.stack.addWidget(self.visualize_panel)# 4: visualize
        self.stack.addWidget(self.ai_panel)       # 5: ai
        self.stack.addWidget(self.settings_panel) # 6: settings

        main_area.addWidget(self.stack, stretch=1)

        root_layout.addLayout(main_area, stretch=1)

        # ── Status bar ──
        self.app_status_bar = StatusBar()
        self.app_status_bar.generate_clicked.connect(self.on_generate_code)
        root_layout.addWidget(self.app_status_bar)

        # Set initial license display
        self._update_status_bar()

    # ──────────────────────────────────────────── Navigation ──

    def _on_page_changed(self, key: str):
        """Handle nav rail page change."""
        if key in PAGE_KEYS:
            self.stack.setCurrentIndex(PAGE_KEYS.index(key))

    def _navigate_to(self, key: str):
        """Programmatically navigate to a page."""
        if key in PAGE_KEYS:
            self.nav_rail.set_active(key)
            self.stack.setCurrentIndex(PAGE_KEYS.index(key))

    # ──────────────────────────────────────────── Project ↔ UI sync ──

    def _project_from_ui(self) -> None:
        """Sync all UI panels back to the project object."""
        if not self.project:
            self.project = Project()
        self.settings_panel.save_to_project(self.project)
        self.agents_panel.sync_to_project()
        self.features_panel.save_to_project(self.project)

    def _ui_from_project(self) -> None:
        """Load project data into all UI panels."""
        if not self.project:
            return
        self.settings_panel.load_from_project(self.project)
        self.agents_panel.set_project(self.project)
        self.features_panel.load_from_project(self.project)
        self.visualize_panel.set_project(self.project)
        self._update_dashboard()
        self._update_status_bar()

    def _update_dashboard(self):
        """Refresh dashboard stats."""
        if self.project:
            self.dashboard.update_stats(
                agent_count=len(self.project.agents),
                protocol_count=len(set(a.protocol_id for a in self.project.agents)),
            )

    def _update_status_bar(self):
        """Refresh the bottom status bar."""
        if self.project:
            self.app_status_bar.set_project_info(
                self.project.name,
                len(self.project.agents),
            )
        else:
            self.app_status_bar.clear()

        if self.license_info:
            self.app_status_bar.set_license_info(
                self.license_info.customer,
                self.license_info.signature_valid,
            )

    def _on_agents_changed(self):
        """Agents were added/removed/modified."""
        self._update_dashboard()
        self._update_status_bar()

    # ──────────────────────────────────────────── Slots ──

    def on_new_project(self) -> None:
        dlg = ProjectWizard(self)
        if dlg.exec() == QDialog.Accepted:
            self.project = dlg.create_project()
            self.current_project_path = None
            self._ui_from_project()
            self._navigate_to("agents")

    def on_open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open BusCraft Project", "",
            "BusCraft Project (*.uvmproj.json);;All Files (*.*)"
        )
        if not path:
            return
        self._open_project_file(path)

    def _open_project_file(self, path: str) -> None:
        try:
            self.project = load_project(path)
            self.current_project_path = Path(path)
            self._ui_from_project()
            self._navigate_to("agents")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to open project:\n{exc}")

    def _on_open_recent(self, path: str):
        if Path(path).exists():
            self._open_project_file(path)
        else:
            QMessageBox.warning(self, "Not Found", f"File not found:\n{path}")

    def on_save_project(self) -> None:
        if not self.project:
            QMessageBox.warning(self, "No Project", "Create a project first.")
            return
        if not self.current_project_path:
            self.on_save_as_project()
            return
        self._project_from_ui()
        try:
            save_project(self.project, self.current_project_path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to save project:\n{exc}")

    def on_save_as_project(self) -> None:
        if not self.project:
            QMessageBox.warning(self, "No Project", "Create a project first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save BusCraft Project As", "",
            "BusCraft Project (*.uvmproj.json);;All Files (*.*)"
        )
        if not path:
            return
        self.current_project_path = Path(path)
        self.on_save_project()

    def on_generate_code(self) -> None:
        if not self.project:
            QMessageBox.warning(self, "No Project", "Create a project first.")
            return
        self._project_from_ui()
        dlg = GenerateDialog(self.project, self.license_info, parent=self)
        dlg.exec()

    def on_generate_diagram(self) -> None:
        if not self.project:
            QMessageBox.warning(self, "No Project", "Create a project first.")
            return
        self._project_from_ui()
        self.visualize_panel.set_project(self.project)
        self._navigate_to("visualize")

    def on_load_license(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load BusCraft License", "",
            "License (*.json);;All Files (*.*)"
        )
        if not path:
            return
        try:
            self.license_info = load_license(path)
            self.settings_panel.set_license_info(self.license_info)
            self._update_status_bar()
            QMessageBox.information(self, "License Loaded", "License loaded successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load license:\n{exc}")

    def _on_license_changed(self, lic):
        self.license_info = lic
        self._update_status_bar()

    def on_about(self) -> None:
        QMessageBox.information(
            self, "About BusCraft",
            "BusCraft v0.1.0\n\n"
            "UVM Verification Environment Generator\n\n"
            "© 2024-2026 BusCraft",
        )

    def on_protocol_browser(self) -> None:
        dlg = ProtocolBrowserDialog(self)
        dlg.exec()

    def _on_spec_project_imported(self, project: Project) -> None:
        self.project = project
        self.current_project_path = None
        self._ui_from_project()
        self._navigate_to("agents")

    def on_launch_waveform(self) -> None:
        if not shutil.which("gtkwave"):
            msg = "GTKWave is not installed or not in PATH."
            if sys.platform == "darwin":
                msg += "\n\nInstall with: brew install --cask gtkwave"
            elif sys.platform == "linux":
                msg += "\n\nInstall with: sudo apt install gtkwave"
            QMessageBox.warning(self, "GTKWave Not Found", msg)
            return

        if not self.project:
            QMessageBox.warning(self, "No Project", "Create a project first.")
            return

        self._project_from_ui()
        search_dir = Path(self.project.output_dir)

        if not search_dir.exists():
            QMessageBox.warning(
                self, "No Output",
                f"Output directory does not exist yet:\n{search_dir}"
            )
            return

        import os
        vcd_files = list(search_dir.rglob("*.vcd"))
        fst_files = list(search_dir.rglob("*.fst"))
        all_waves = vcd_files + fst_files

        if not all_waves:
            QMessageBox.information(
                self, "No Waveforms",
                f"No .vcd or .fst files found in:\n{search_dir}\n\n"
                "Run a simulation that dumps waveforms first."
            )
            return

        target = str(max(all_waves, key=os.path.getmtime))

        try:
            subprocess.Popen(
                ["gtkwave", target],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "GTKWave Error",
                f"Failed to launch GTKWave:\n{exc}"
            )
