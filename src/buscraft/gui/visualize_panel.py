"""Full visualization panel — GUI equivalent of the CLI 'visualize' command."""
from __future__ import annotations
from pathlib import Path
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFileDialog, QTextEdit, QGroupBox,
    QFormLayout, QMessageBox, QScrollArea, QSizePolicy,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from buscraft.core.models import Project


class VisualizePanel(QWidget):
    """Tab panel for generating UVM architecture diagrams."""

    DIAGRAM_TYPES = [
        ("Block Diagram (Graphviz)", "block"),
        ("Sequence Diagram (PlantUML)", "sequence"),
        ("State Machine (PlantUML)", "state"),
        ("GTKWave Signal Config", "gtkwave"),
        ("All Diagrams", "all"),
    ]

    FORMATS = ["png", "svg", "pdf"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Project | None = None
        self._build_ui()

    def set_project(self, project: Project):
        self.project = project
        # Default output dir based on project
        if project:
            self.ed_outdir.setText(f"{project.name}_diagrams")

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        root = QVBoxLayout(self)

        # --- Options ---
        opts_group = QGroupBox("Diagram Options")
        form = QFormLayout(opts_group)

        self.cmb_type = QComboBox()
        for label, _ in self.DIAGRAM_TYPES:
            self.cmb_type.addItem(label)
        form.addRow("Diagram type:", self.cmb_type)

        self.cmb_format = QComboBox()
        self.cmb_format.addItems(self.FORMATS)
        form.addRow("Output format:", self.cmb_format)

        outdir_row = QWidget()
        od_layout = QHBoxLayout(outdir_row)
        od_layout.setContentsMargins(0, 0, 0, 0)
        self.ed_outdir = QLineEdit("buscraft_diagrams")
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.clicked.connect(self._on_browse_dir)
        od_layout.addWidget(self.ed_outdir, stretch=1)
        od_layout.addWidget(self.btn_browse)
        form.addRow("Output directory:", outdir_row)

        root.addWidget(opts_group)

        # --- Generate button ---
        btn_row = QHBoxLayout()
        self.btn_generate = QPushButton("Generate Diagrams")
        self.btn_generate.setMinimumHeight(36)
        self.btn_generate.clicked.connect(self._on_generate)
        btn_row.addWidget(self.btn_generate)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # --- Image preview (scrollable) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.image_label = QLabel("Diagrams will appear here after generation.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll_area.setWidget(self.image_label)
        root.addWidget(self.scroll_area, stretch=3)

        # --- Generated files log ---
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(140)
        self.txt_log.setPlaceholderText("Generated file list…")
        root.addWidget(self.txt_log, stretch=1)

    # --------------------------------------------------------------- Slots --

    def _on_browse_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.ed_outdir.setText(directory)

    def _on_generate(self):
        if not self.project:
            QMessageBox.warning(self, "No Project",
                                "Create or open a project first.")
            return

        if not self.project.agents:
            QMessageBox.warning(self, "No Agents",
                                "Add at least one agent before generating diagrams.")
            return

        out_dir = self.ed_outdir.text().strip() or "buscraft_diagrams"
        os.makedirs(out_dir, exist_ok=True)
        fmt = self.cmb_format.currentText()
        _, diagram_key = self.DIAGRAM_TYPES[self.cmb_type.currentIndex()]

        generated: list[tuple[str, str]] = []
        errors: list[str] = []
        base_name = f"{out_dir}/{self.project.name}"

        # --- Block ---
        if diagram_key in ("block", "all"):
            try:
                from buscraft.core.visualizer import generate_diagram
                path = generate_diagram(self.project, f"{base_name}_architecture", fmt=fmt)
                generated.append(("Block diagram (Graphviz)", path))
            except Exception as exc:
                errors.append(f"Block diagram: {exc}")

        # --- Sequence ---
        if diagram_key in ("sequence", "all"):
            try:
                from buscraft.core.visualizer import generate_puml_sequence, render_puml
                puml_path = generate_puml_sequence(self.project, f"{base_name}_sequence")
                generated.append(("Sequence diagram (.puml)", puml_path))
                rendered = render_puml(puml_path, fmt=fmt)
                if rendered:
                    generated.append(("Sequence diagram (rendered)", rendered))
            except Exception as exc:
                errors.append(f"Sequence diagram: {exc}")

        # --- State ---
        if diagram_key in ("state", "all"):
            try:
                from buscraft.core.visualizer import generate_puml_state, render_puml
                puml_path = generate_puml_state(self.project, f"{base_name}_state")
                generated.append(("State diagram (.puml)", puml_path))
                rendered = render_puml(puml_path, fmt=fmt)
                if rendered:
                    generated.append(("State diagram (rendered)", rendered))
            except Exception as exc:
                errors.append(f"State diagram: {exc}")

        # --- GTKWave ---
        if diagram_key in ("gtkwave", "all"):
            try:
                from buscraft.core.visualizer import generate_gtkwave_savefile
                gtkw_path = generate_gtkwave_savefile(self.project, f"{base_name}_waves")
                generated.append(("GTKWave config (.gtkw)", gtkw_path))
            except Exception as exc:
                errors.append(f"GTKWave config: {exc}")

        # --- Update log ---
        lines = []
        if generated:
            lines.append(f"Generated {len(generated)} file(s):\n")
            for label, path in generated:
                lines.append(f"  - {label}: {path}")
        if errors:
            lines.append(f"\nErrors ({len(errors)}):")
            for err in errors:
                lines.append(f"  ✗ {err}")

        puml_files = [p for _, p in generated if p.endswith(".puml")]
        if puml_files:
            lines.append("\nTip: Render .puml files at https://www.plantuml.com/plantuml/uml/")
            lines.append("     Or install PlantUML: brew install plantuml")

        self.txt_log.setPlainText("\n".join(lines))

        # --- Show the first renderable image ---
        image_shown = False
        for _, path in generated:
            if path.endswith((".png", ".svg", ".pdf")):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self.scroll_area.size() * 0.95,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation,
                    )
                    self.image_label.setPixmap(scaled)
                    image_shown = True
                    break

        if not image_shown:
            self.image_label.setText(
                "No rendered image available.\n"
                "Generated .puml text files — install PlantUML to render them."
            )

        if errors and not generated:
            QMessageBox.critical(self, "Diagram Errors", "\n".join(errors))
