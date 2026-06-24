"""Spec-to-Project import panel — full GUI equivalent of the CLI 'spec' command.

Supports:
- File picker and drag-and-drop
- Fast/Deep analysis modes
- File category selection for code generation
- Combined analyze → import → generate flow
"""
from __future__ import annotations
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QTextEdit, QProgressBar,
    QMessageBox, QGroupBox, QFormLayout, QCheckBox, QGridLayout,
)
from PySide6.QtCore import Qt, QThread, Signal as QtSignal, QMimeData

from buscraft.core.generator import FILE_CATEGORIES, MINIMAL_FILES, FULL_FILES


class _AnalysisWorker(QThread):
    """Runs spec analysis on a background thread."""
    progress = QtSignal(str, int, int)   # stage, current, total
    finished = QtSignal(object)          # SpecModel
    error = QtSignal(str)

    def __init__(self, raw_text: str, deep: bool = False):
        super().__init__()
        self.raw_text = raw_text
        self.deep = deep

    def run(self):
        try:
            from buscraft.core.spec_analyzer import analyze_spec
            llm = None
            if self.deep:
                try:
                    from huggingface_hub import hf_hub_download
                    from llama_cpp import Llama
                    model_path = hf_hub_download(
                        repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
                        filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf",
                    )
                    llm = Llama(
                        model_path=model_path, verbose=False,
                        n_ctx=2048, n_gpu_layers=0, n_threads=4, seed=42,
                    )
                except Exception:
                    pass

            def on_progress(stage, current, total):
                self.progress.emit(stage, current, total)

            spec_model = analyze_spec(
                self.raw_text, llm=llm,
                on_progress=on_progress, deep=self.deep,
            )
            self.finished.emit(spec_model)
        except Exception as exc:
            self.error.emit(str(exc))


class _GenerateWorker(QThread):
    """Runs code generation on a background thread."""
    finished = QtSignal(dict)
    error = QtSignal(str)

    def __init__(self, project, selected_files, license_info=None):
        super().__init__()
        self.project = project
        self.selected_files = selected_files
        self.license_info = license_info

    def run(self):
        try:
            from buscraft.core.generator import Generator
            gen = Generator(self.project, self.license_info)
            result = gen.generate_all(selected_files=self.selected_files)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class SpecImportPanel(QWidget):
    """Tab panel for importing an IP spec file and converting it to a BusCraft project."""

    # Emitted when the user wants to import the result into the active project.
    project_ready = QtSignal(object)  # Project

    def __init__(self, parent=None):
        super().__init__(parent)
        self._spec_model = None
        self._project = None
        self._raw_text: str | None = None
        self._worker: _AnalysisWorker | None = None
        self._gen_worker: _GenerateWorker | None = None
        self.setAcceptDrops(True)
        self._build_ui()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        root = QVBoxLayout(self)

        # --- File selection ---
        file_group = QGroupBox("Specification File (or drag && drop a file here)")
        file_layout = QFormLayout(file_group)

        file_row = QWidget()
        fr_layout = QHBoxLayout(file_row)
        fr_layout.setContentsMargins(0, 0, 0, 0)
        self.ed_file = QLineEdit()
        self.ed_file.setPlaceholderText("Select a .pdf, .md, or .txt spec file…")
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.clicked.connect(self._on_browse)
        fr_layout.addWidget(self.ed_file, stretch=1)
        fr_layout.addWidget(self.btn_browse)
        file_layout.addRow("File:", file_row)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Leave blank to auto-detect from spec")
        file_layout.addRow("Project name:", self.ed_name)

        opts_row = QWidget()
        opts_layout = QHBoxLayout(opts_row)
        opts_layout.setContentsMargins(0, 0, 0, 0)
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["Fast (regex)", "Deep (AI-powered)"])
        self.cmb_sim = QComboBox()
        self.cmb_sim.addItems(["vcs", "questa", "xcelium", "verilator"])
        opts_layout.addWidget(QLabel("Mode:"))
        opts_layout.addWidget(self.cmb_mode)
        opts_layout.addWidget(QLabel("  Simulator:"))
        opts_layout.addWidget(self.cmb_sim)
        opts_layout.addStretch()
        file_layout.addRow(opts_row)

        root.addWidget(file_group)

        # --- File category selection ---
        cat_group = QGroupBox("Files to Generate")
        cat_layout = QVBoxLayout(cat_group)

        preset_row = QHBoxLayout()
        btn_all = QPushButton("All")
        btn_minimal = QPushButton("Minimal")
        btn_none = QPushButton("None")
        btn_all.clicked.connect(lambda: self._set_preset(FULL_FILES))
        btn_minimal.clicked.connect(lambda: self._set_preset(MINIMAL_FILES))
        btn_none.clicked.connect(lambda: self._set_preset(set()))
        preset_row.addWidget(btn_all)
        preset_row.addWidget(btn_minimal)
        preset_row.addWidget(btn_none)
        preset_row.addStretch()
        cat_layout.addLayout(preset_row)

        grid = QGridLayout()
        self._cat_checkboxes: dict[str, QCheckBox] = {}
        row = 0
        col = 0
        for key, desc in FILE_CATEGORIES.items():
            cb = QCheckBox(key)
            cb.setToolTip(desc)
            cb.setChecked(True)  # default: all selected
            self._cat_checkboxes[key] = cb
            grid.addWidget(cb, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1
        cat_layout.addLayout(grid)
        root.addWidget(cat_group)

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        self.btn_analyze = QPushButton("① Analyze Spec")
        self.btn_analyze.setMinimumHeight(36)
        self.btn_analyze.clicked.connect(self._on_analyze)

        self.btn_import = QPushButton("② Import to Project")
        self.btn_import.setMinimumHeight(36)
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self._on_import)

        self.btn_generate = QPushButton("③ Generate UVM Code")
        self.btn_generate.setMinimumHeight(36)
        self.btn_generate.setEnabled(False)
        self.btn_generate.clicked.connect(self._on_generate)

        self.btn_all_in_one = QPushButton("Analyze + Import + Generate")
        self.btn_all_in_one.setMinimumHeight(36)
        self.btn_all_in_one.clicked.connect(self._on_full_pipeline)

        btn_row.addWidget(self.btn_analyze)
        btn_row.addWidget(self.btn_import)
        btn_row.addWidget(self.btn_generate)
        btn_row.addWidget(self.btn_all_in_one)
        root.addLayout(btn_row)

        # --- Progress ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.lbl_status = QLabel("")
        root.addWidget(self.progress_bar)
        root.addWidget(self.lbl_status)

        # --- Results ---
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setPlaceholderText(
            "Analysis results will appear here.\n\n"
            "You can also drag and drop a .pdf, .md, or .txt file onto this panel."
        )
        root.addWidget(self.txt_results, stretch=1)

    # --------------------------------------------------------- Drag & Drop --

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(('.pdf', '.md', '.txt', '.rst')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and Path(path).exists():
                self.ed_file.setText(path)
                self.lbl_status.setText(f"Dropped: {Path(path).name}")
                event.acceptProposedAction()
                return
        event.ignore()

    # --------------------------------------------------------------- Helpers

    def _set_preset(self, selected: set):
        for key, cb in self._cat_checkboxes.items():
            cb.setChecked(key in selected)

    def _get_selected_files(self) -> set:
        return {key for key, cb in self._cat_checkboxes.items() if cb.isChecked()}

    # --------------------------------------------------------------- Slots --

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Specification File", "",
            "Spec Files (*.pdf *.md *.txt *.rst);;All Files (*.*)"
        )
        if path:
            self.ed_file.setText(path)

    def _on_analyze(self):
        filepath = self.ed_file.text().strip()
        if not filepath:
            QMessageBox.warning(self, "No File", "Select or drop a specification file first.")
            return
        if not Path(filepath).exists():
            QMessageBox.critical(self, "File Not Found", f"File does not exist:\n{filepath}")
            return

        self.lbl_status.setText("Reading specification file…")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.btn_analyze.setEnabled(False)
        self.btn_import.setEnabled(False)
        self.btn_generate.setEnabled(False)
        self.txt_results.clear()
        self._spec_model = None
        self._project = None

        try:
            from buscraft.core.spec_parser import parse_spec
            self._raw_text = parse_spec(filepath)
        except ImportError as exc:
            QMessageBox.critical(self, "Missing Dependency", str(exc))
            self._reset_progress()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Parse Error", f"Failed to read spec:\n{exc}")
            self._reset_progress()
            return

        self.lbl_status.setText(f"Extracted {len(self._raw_text):,} characters. Analyzing…")

        deep = self.cmb_mode.currentIndex() == 1
        self._worker = _AnalysisWorker(self._raw_text, deep=deep)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.start()

    def _on_progress(self, stage: str, current: int, total: int):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        self.lbl_status.setText(f"Analyzing: {stage}")

    def _on_analysis_done(self, spec_model):
        self._spec_model = spec_model
        self._reset_progress()

        from buscraft.core.spec_to_project import spec_summary
        summary = spec_summary(spec_model)
        self.txt_results.setPlainText(summary)
        self.btn_import.setEnabled(True)
        self.lbl_status.setText("Analysis complete — click 'Import to Project' or 'Generate UVM Code'.")

    def _on_analysis_error(self, msg: str):
        self._reset_progress()
        QMessageBox.critical(self, "Analysis Error", msg)
        self.lbl_status.setText("Analysis failed.")

    def _on_import(self):
        if not self._spec_model:
            return

        from buscraft.core.spec_to_project import spec_to_project

        name = self.ed_name.text().strip() or None
        simulator = self.cmb_sim.currentText()

        self._project = spec_to_project(
            self._spec_model,
            project_name=name,
            simulator=simulator,
        )

        self.project_ready.emit(self._project)
        self.btn_generate.setEnabled(True)
        self.lbl_status.setText(
            f"Project '{self._project.name}' imported. "
            f"Click 'Generate UVM Code' to produce files."
        )

    def _on_generate(self):
        if not self._project:
            QMessageBox.warning(self, "No Project", "Analyze and import a spec first.")
            return

        selected = self._get_selected_files()
        if not selected:
            QMessageBox.warning(self, "Nothing Selected", "Select at least one file category.")
            return

        self.lbl_status.setText("Generating UVM code…")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.btn_generate.setEnabled(False)

        self._gen_worker = _GenerateWorker(self._project, selected)
        self._gen_worker.finished.connect(self._on_gen_done)
        self._gen_worker.error.connect(self._on_gen_error)
        self._gen_worker.start()

    def _on_gen_done(self, output_files: dict):
        self._reset_progress()
        lines = [f"Generated {len(output_files)} file(s):\n"]
        for file_type, file_path in output_files.items():
            lines.append(f"  - {file_type}: {file_path}")
        lines.append(f"\nOutput directory: {self._project.output_dir}")

        self.txt_results.append("\n\n" + "=" * 50)
        self.txt_results.append("\n".join(lines))
        self.lbl_status.setText(f"Generated {len(output_files)} files successfully.")
        self.btn_generate.setEnabled(True)

    def _on_gen_error(self, msg: str):
        self._reset_progress()
        QMessageBox.critical(self, "Generation Error", msg)
        self.btn_generate.setEnabled(True)

    def _on_full_pipeline(self):
        """Run the full pipeline: analyze → import → generate."""
        filepath = self.ed_file.text().strip()
        if not filepath:
            QMessageBox.warning(self, "No File", "Select or drop a specification file first.")
            return
        if not Path(filepath).exists():
            QMessageBox.critical(self, "File Not Found", f"File does not exist:\n{filepath}")
            return

        # Override the analysis done callback to auto-continue
        self._full_pipeline_mode = True
        self._on_analyze()

    def _on_analysis_done_pipeline(self, spec_model):
        """Called after analysis when in full pipeline mode."""
        self._on_analysis_done(spec_model)
        self._on_import()
        self._on_generate()

    # Override to support pipeline mode
    def _on_analysis_done(self, spec_model):
        self._spec_model = spec_model
        self._reset_progress()

        from buscraft.core.spec_to_project import spec_summary
        summary = spec_summary(spec_model)
        self.txt_results.setPlainText(summary)
        self.btn_import.setEnabled(True)

        if getattr(self, '_full_pipeline_mode', False):
            self._full_pipeline_mode = False
            self.lbl_status.setText("Pipeline: analysis done, importing…")
            self._on_import()
            self._on_generate()
        else:
            self.lbl_status.setText("Analysis complete — click 'Import to Project' or 'Generate UVM Code'.")

    def _reset_progress(self):
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 1)
        self.btn_analyze.setEnabled(True)
