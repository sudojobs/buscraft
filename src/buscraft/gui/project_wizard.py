from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox,
    QPushButton, QFileDialog, QComboBox, QWidget, QHBoxLayout
)

from buscraft.core.models import Project, Agent


class ProjectWizard(QDialog):
    """Minimal single-page wizard for creating a new project."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New BusCraft Project")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_name = QLineEdit("buscraft_demo")
        self.ed_out = QLineEdit(str(Path("./buscraft_out").resolve()))
        self.btn_browse = QPushButton("Browse...")
        self.cmb_sim = QComboBox()
        self.cmb_sim.addItems(["vcs", "questa", "xcelium", "verilator"])

        form.addRow("Project name:", self.ed_name)

        out_widget = QWidget()
        out_layout = QHBoxLayout(out_widget)
        out_layout.setContentsMargins(0, 0, 0, 0)
        out_layout.addWidget(self.ed_out)
        out_layout.addWidget(self.btn_browse)
        form.addRow("Output directory:", out_widget)

        form.addRow("Simulator:", self.cmb_sim)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        layout.addWidget(btns)

        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        self.btn_browse.clicked.connect(self._on_browse)

    def _on_browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.ed_out.setText(directory)

    def create_project(self) -> Project:
        proj = Project(
            name=self.ed_name.text().strip() or "buscraft_demo",
            output_dir=self.ed_out.text().strip() or "./buscraft_out",
            simulator=self.cmb_sim.currentText(),
        )
        # Default AXI agent
        agent = Agent(
            name="axi_agent_0",
            protocol_id="amba_axi",
            role="master",
            parameters={"data_width": 32, "addr_width": 32},
            vip_mode="full",
        )
        proj.agents.append(agent)
        proj.protocols_used = ["amba_axi"]
        return proj
