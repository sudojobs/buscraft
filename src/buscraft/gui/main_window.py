from __future__ import annotations
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel,
    QFileDialog, QMessageBox, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QPushButton, QTextEdit, QHBoxLayout, QApplication,
    QDialog
)
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtCore import Qt

from buscraft.core.models import Project
from buscraft.core.project_io import load_project, save_project
from buscraft.core.generator import Generator, GenerationError
from buscraft.core.visualizer import generate_diagram
from buscraft.core.license_manager import load_license, get_license_summary, LicenseInfo, create_demo_license
from buscraft.gui.project_wizard import ProjectWizard
from buscraft.gui.protocol_config_panel import ProtocolConfigPanel
from buscraft.core.ai_engine import DummyAIEngine


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BusCraft")
        self.resize(1100, 700)

        self.project: Project | None = None
        self.current_project_path: Path | None = None
        self.license_info: LicenseInfo | None = create_demo_license()
        self.ai_engine = DummyAIEngine()

        self._create_actions()
        self._create_menu()
        self._create_central()

        self.statusBar().showMessage("Ready. Use File → New to create a project.")

    # -------- UI construction --------

    def _create_actions(self) -> None:
        self.act_new = QAction("&New", self)
        self.act_open = QAction("&Open...", self)
        self.act_save = QAction("&Save", self)
        self.act_save_as = QAction("Save &As...", self)
        self.act_exit = QAction("E&xit", self)

        self.act_gen_code = QAction("Generate &Code", self)
        self.act_gen_diag = QAction("Generate &Diagram", self)
        self.act_load_license = QAction("&Load License...", self)

        self.act_about = QAction("&About", self)

        self.act_new.triggered.connect(self.on_new_project)
        self.act_open.triggered.connect(self.on_open_project)
        self.act_save.triggered.connect(self.on_save_project)
        self.act_save_as.triggered.connect(self.on_save_as_project)
        self.act_exit.triggered.connect(self.close)

        self.act_gen_code.triggered.connect(self.on_generate_code)
        self.act_gen_diag.triggered.connect(self.on_generate_diagram)
        self.act_load_license.triggered.connect(self.on_load_license)

        self.act_about.triggered.connect(self.on_about)

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
        tools_menu.addAction(self.act_load_license)
        tools_menu.addAction(self.act_gen_code)
        tools_menu.addAction(self.act_gen_diag)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self.act_about)

    def _create_central(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs, stretch=3)

        # --- Project Settings tab ---
        self.tab_settings = QWidget()
        form = QFormLayout(self.tab_settings)
        self.ed_name = QLineEdit()
        self.ed_output = QLineEdit()
        self.btn_out_browse = QPushButton("Browse...")
        self.cmb_sim = QComboBox()
        self.cmb_sim.addItems(["vcs", "questa", "xcelium", "verilator"])

        out_widget = QWidget()
        out_layout = QHBoxLayout(out_widget)
        out_layout.setContentsMargins(0, 0, 0, 0)
        out_layout.addWidget(self.ed_output)
        out_layout.addWidget(self.btn_out_browse)

        form.addRow("Project name:", self.ed_name)
        form.addRow("Output directory:", out_widget)
        form.addRow("Simulator:", self.cmb_sim)

        self.btn_out_browse.clicked.connect(self._on_browse_output)
        self.tabs.addTab(self.tab_settings, "Project Settings")

        # --- Protocols & Agents tab ---
        self.protocol_panel = ProtocolConfigPanel(self)
        self.tabs.addTab(self.protocol_panel, "Protocols & Agents")

        # --- Features tab ---
        self.tab_features = QWidget()
        f_layout = QVBoxLayout(self.tab_features)
        self.chk_scoreboard = QCheckBox("Generate Scoreboard")
        self.chk_coverage = QCheckBox("Generate Coverage")
        self.chk_assertions = QCheckBox("Generate Assertions")
        self.chk_ai_assist = QCheckBox("Enable AI Assistance (stub)")
        self.chk_sim_scripts = QCheckBox("Generate Simulator Scripts")
        for c in (
            self.chk_scoreboard,
            self.chk_coverage,
            self.chk_assertions,
            self.chk_ai_assist,
            self.chk_sim_scripts,
        ):
            f_layout.addWidget(c)
        f_layout.addStretch()
        self.tabs.addTab(self.tab_features, "Features & Coverage")

        # --- AI Assistant tab ---
        self.tab_ai = QWidget()
        ai_layout = QVBoxLayout(self.tab_ai)
        self.ai_desc = QTextEdit()
        self.ai_desc.setPlaceholderText("Describe the desired environment here...")
        self.ai_log = QTextEdit()
        self.ai_log.setReadOnly(True)
        self.btn_ai_generate = QPushButton("Generate config from description (Dummy)")
        ai_layout.addWidget(self.ai_desc)
        ai_layout.addWidget(self.btn_ai_generate)
        ai_layout.addWidget(QLabel("AI log:"))
        ai_layout.addWidget(self.ai_log)
        self.btn_ai_generate.clicked.connect(self.on_ai_generate)
        self.tabs.addTab(self.tab_ai, "AI Assistant")

        # --- License Info tab ---
        self.tab_license = QWidget()
        lic_layout = QVBoxLayout(self.tab_license)
        self.lic_text = QTextEdit()
        self.lic_text.setReadOnly(True)
        lic_layout.addWidget(self.lic_text)
        self.tabs.addTab(self.tab_license, "License Info")

        # --- Diagram view ---
        self.diagram_label = QLabel("Diagram will appear here after generation.")
        self.diagram_label.setAlignment(Qt.AlignCenter)
        self.diagram_label.setMinimumHeight(200)
        layout.addWidget(self.diagram_label, stretch=2)

        self._update_license_view()

    # -------- project <-> UI sync --------

    def _project_from_ui(self) -> None:
        if not self.project:
            self.project = Project()
        self.project.name = self.ed_name.text().strip() or "untitled"
        self.project.output_dir = self.ed_output.text().strip() or "./buscraft_out"
        self.project.simulator = self.cmb_sim.currentText()
        self.project.features["scoreboard_enable"] = self.chk_scoreboard.isChecked()
        self.project.features["coverage_enable"] = self.chk_coverage.isChecked()
        self.project.features["assertions_enable"] = self.chk_assertions.isChecked()
        self.project.features["ai_assist_enable"] = self.chk_ai_assist.isChecked()
        self.project.features["sim_scripts_enable"] = self.chk_sim_scripts.isChecked()
        self.protocol_panel.sync_to_project()

    def _ui_from_project(self) -> None:
        if not self.project:
            return
        self.ed_name.setText(self.project.name)
        self.ed_output.setText(self.project.output_dir)
        idx = self.cmb_sim.findText(self.project.simulator)
        if idx >= 0:
            self.cmb_sim.setCurrentIndex(idx)
        self.chk_scoreboard.setChecked(self.project.features.get("scoreboard_enable", True))
        self.chk_coverage.setChecked(self.project.features.get("coverage_enable", True))
        self.chk_assertions.setChecked(self.project.features.get("assertions_enable", True))
        self.chk_ai_assist.setChecked(self.project.features.get("ai_assist_enable", False))
        self.chk_sim_scripts.setChecked(self.project.features.get("sim_scripts_enable", True))
        self.protocol_panel.set_project(self.project)

    # -------- slots --------

    def on_new_project(self) -> None:
        dlg = ProjectWizard(self)
        if dlg.exec() == QDialog.Accepted:
            self.project = dlg.create_project()
            self.current_project_path = None
            self._ui_from_project()
            self.statusBar().showMessage("New project created.", 3000)

    def on_open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open BusCraft Project", "", "BusCraft Project (*.uvmproj.json);;All Files (*.*)"
        )
        if not path:
            return
        try:
            self.project = load_project(path)
            self.current_project_path = Path(path)
            self._ui_from_project()
            self.statusBar().showMessage(f"Opened project: {path}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to open project:\n{exc}")

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
            self.statusBar().showMessage(f"Project saved to {self.current_project_path}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to save project:\n{exc}")

    def on_save_as_project(self) -> None:
        if not self.project:
            QMessageBox.warning(self, "No Project", "Create a project first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save BusCraft Project As", "", "BusCraft Project (*.uvmproj.json);;All Files (*.*)"
        )
        if not path:
            return
        self.current_project_path = Path(path)
        self.on_save_project()

    def _on_browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.ed_output.setText(directory)

    def on_generate_code(self) -> None:
        if not self.project:
            QMessageBox.warning(self, "No Project", "Create a project first.")
            return
        self._project_from_ui()
        try:
            gen = Generator(self.project, self.license_info)
            paths = gen.generate_all()
        except GenerationError as exc:
            QMessageBox.critical(self, "Generation Error", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Unexpected error: {exc}")
            return

        msg = "Generated files:\n" + "\n".join(f"- {k}: {v}" for k, v in paths.items())
        QMessageBox.information(self, "Generation Complete", msg)
        self.statusBar().showMessage("Generation complete.", 3000)

    def on_generate_diagram(self) -> None:
        if not self.project:
            QMessageBox.warning(self, "No Project", "Create a project first.")
            return
        self._project_from_ui()
        out_dir = Path(self.project.output_dir)
        img_path = out_dir / "buscraft_diagram.png"
        try:
            result = generate_diagram(self.project, img_path)
        except Exception as exc:
            QMessageBox.critical(self, "Diagram Error", f"Failed to generate diagram:\n{exc}")
            return

        pixmap = QPixmap(result)
        if pixmap.isNull():
            self.diagram_label.setText(f"Diagram generated at:\n{result}")
        else:
            self.diagram_label.setPixmap(pixmap.scaled(
                self.diagram_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        self.statusBar().showMessage("Diagram generated.", 3000)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        pixmap = self.diagram_label.pixmap()
        if pixmap:
            self.diagram_label.setPixmap(
                pixmap.scaled(
                    self.diagram_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )

    def on_load_license(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load BusCraft License", "", "License (*.json);;All Files (*.*)"
        )
        if not path:
            return
        try:
            self.license_info = load_license(path)
            self._update_license_view()
            QMessageBox.information(self, "License Loaded", "License loaded successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load license:\n{exc}")

    def _update_license_view(self) -> None:
        self.lic_text.setPlainText(get_license_summary(self.license_info))

    def on_ai_generate(self) -> None:
        if not self.project:
            QMessageBox.warning(self, "No Project", "Create a project first.")
            return
        desc = self.ai_desc.toPlainText().strip()
        if not desc:
            return
        current_cfg = self.project.to_dict()
        new_cfg = self.ai_engine.generate_project_config(desc, current_cfg)
        self.ai_log.append("AI stub processed description. Notes:")
        for n in new_cfg.get("notes", []):
            self.ai_log.append(f"- {n}")

    def on_about(self) -> None:
        QMessageBox.information(
            self,
            "About BusCraft",
            "BusCraft\n\nUVM VIP/ BFMs generator prototype.",
        )
