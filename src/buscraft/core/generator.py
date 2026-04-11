from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional, Set

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import Project
from .license_manager import LicenseInfo, check_feature, check_limits, create_demo_license
from .plugin_manager import protocols_for_project


class GenerationError(Exception):
    pass


# All available file categories for selective generation
FILE_CATEGORIES = {
    "interface":  "Signal-level interface (modports for master/slave/monitor)",
    "seq_item":   "Sequence item (transaction fields + constraints)",
    "agent":      "UVM agent (driver + monitor + sequencer shell)",
    "sequences":  "Test sequences (write, read, mixed traffic)",
    "env":        "Top-level UVM environment",
    "scoreboard": "Scoreboard (expected vs actual checker)",
    "coverage":   "Functional coverage collectors",
    "assertions": "SVA protocol assertions",
    "tb_top":     "Testbench top (clock, reset, DUT placeholder, config_db)",
    "test":       "Base test + smoke test",
    "sim_scripts":"Simulator Makefile and run scripts",
}

# Minimal set for basic structure
MINIMAL_FILES = {"agent", "env", "sim_scripts"}

# Full set for simulation-ready testbench
FULL_FILES = set(FILE_CATEGORIES.keys())


def _get_templates_root() -> Path:
    import sys
    from pathlib import Path

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return base / "buscraft" / "templates"
    else:
        return Path(__file__).resolve().parents[1] / "templates"


def _create_env() -> Environment:
    root = _get_templates_root()
    loader = FileSystemLoader(str(root))
    env = Environment(
        loader=loader,
        autoescape=select_autoescape([]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


class Generator:
    def __init__(self, project: Project, license_info: Optional[LicenseInfo] = None):
        self.project = project
        self.license = license_info or create_demo_license()
        self.env = _create_env()

    def validate(self) -> None:
        if not check_limits(self.license, self.project):
            raise GenerationError("License limits exceeded (agents/protocols).")

        for agent in self.project.agents:
            feat = check_feature(self.license, agent.protocol_id)
            if not feat:
                raise GenerationError(f"Protocol {agent.protocol_id} is not enabled in the license.")

    def generate_all(self, selected_files: Optional[Set[str]] = None) -> Dict[str, str]:
        """
        Generate verification files based on selected categories.
        
        Args:
            selected_files: Set of file category names to generate.
                          If None, generates the legacy default set (agent + env + sim).
        
        Returns:
            Mapping: logical name -> output file path.
        """
        self.validate()

        # Default to legacy behavior if no selection given
        if selected_files is None:
            selected_files = MINIMAL_FILES

        out_paths: Dict[str, str] = {}
        out_root = Path(self.project.output_dir)
        out_root.mkdir(parents=True, exist_ok=True)

        context: Dict[str, Any] = {
            "project": self.project,
            "agents": self.project.agents,
            "features": self.project.features,
            "license": self.license,
        }

        # --- Protocol-specific files (agent, pkg) ---
        if "agent" in selected_files:
            for plugin in protocols_for_project(self.project):
                templates = plugin.get_templates()
                for key, tpath in templates.items():
                    tmpl = self.env.get_template(tpath)
                    rendered = tmpl.render(context=context, plugin=plugin)
                    dest_name = Path(tpath).name.replace(".j2", "")
                    dest_path = out_root / dest_name
                    dest_path.write_text(rendered, encoding="utf-8")
                    out_paths[f"{plugin.id}_{key}"] = str(dest_path)

        # --- Common template files ---
        common_templates = {
            "interface":  ("common/base_interface.sv.j2",  "{plugin_id}_interface.sv"),
            "seq_item":   ("common/base_seq_item.sv.j2",   "{plugin_id}_seq_item.sv"),
            "sequences":  ("common/base_sequence.sv.j2",   "{plugin_id}_sequences.sv"),
            "env":        ("common/base_env.sv.j2",        "buscraft_env.sv"),
            "scoreboard": ("common/base_scoreboard.sv.j2", "buscraft_scoreboard.sv"),
            "coverage":   ("common/base_cov.sv.j2",        "buscraft_coverage.sv"),
            "assertions": ("common/base_assert.sv.j2",     "buscraft_assertions.sv"),
            "tb_top":     ("common/base_tb_top.sv.j2",     "tb_top.sv"),
            "test":       ("common/base_test.sv.j2",       "{project_name}_test.sv"),
        }

        for category, (tpath, dest_pattern) in common_templates.items():
            if category not in selected_files:
                continue
            if category in ("agent",):  # Already handled above
                continue
                
            try:
                tmpl = self.env.get_template(tpath)
            except Exception:
                continue  # Skip if template doesn't exist yet
            
            # For per-protocol templates, generate one file per protocol
            if "{plugin_id}" in dest_pattern:
                for plugin in protocols_for_project(self.project):
                    rendered = tmpl.render(context=context, plugin=plugin)
                    dest_name = dest_pattern.replace("{plugin_id}", plugin.id)
                    dest_path = out_root / dest_name
                    dest_path.write_text(rendered, encoding="utf-8")
                    out_paths[f"{plugin.id}_{category}"] = str(dest_path)
            else:
                rendered = tmpl.render(context=context)
                dest_name = dest_pattern.replace("{project_name}", self.project.name)
                dest_path = out_root / dest_name
                dest_path.write_text(rendered, encoding="utf-8")
                out_paths[category] = str(dest_path)

        # --- Simulator scripts ---
        if "sim_scripts" in selected_files and self.project.features.get("sim_scripts_enable", True):
            sim = self.project.simulator
            sim_dir = out_root / "sim" / sim
            sim_dir.mkdir(parents=True, exist_ok=True)
            
            sim_templates = {
                "Makefile": f"sim/{sim}/Makefile.j2",
                "run.sh": f"sim/{sim}/run.sh.j2",
            }
            
            # Also try coverage config
            cov_template = f"sim/{sim}/coverage_cff.j2"
            sim_templates["coverage_cff"] = cov_template
            
            for dest_name, tpath in sim_templates.items():
                try:
                    tmpl = self.env.get_template(tpath)
                    rendered = tmpl.render(context=context)
                    dest_path = sim_dir / dest_name
                    dest_path.write_text(rendered, encoding="utf-8")
                    out_paths[f"sim_{sim}_{dest_name}"] = str(dest_path)
                except Exception:
                    continue  # Skip if template doesn't exist for this simulator

        return out_paths
