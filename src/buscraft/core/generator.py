from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import Project
from .license_manager import LicenseInfo, check_feature, check_limits, create_demo_license
from .plugin_manager import protocols_for_project


class GenerationError(Exception):
    pass


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

    def generate_all(self) -> Dict[str, str]:
        """
        Generate a set of files:
          - per-protocol pkg/agent files
          - multi-protocol buscraft_env.sv
          - basic VCS Makefile (if simulator is vcs)
        Returns mapping: logical name -> path.
        """
        self.validate()

        out_paths: Dict[str, str] = {}
        out_root = Path(self.project.output_dir)
        out_root.mkdir(parents=True, exist_ok=True)

        context: Dict[str, Any] = {
            "project": self.project,
            "agents": self.project.agents,
            "features": self.project.features,
            "license": self.license,
        }

        # Protocol files
        for plugin in protocols_for_project(self.project):
            templates = plugin.get_templates()
            for key, tpath in templates.items():
                tmpl = self.env.get_template(tpath)
                rendered = tmpl.render(context=context, plugin=plugin)
                dest_name = Path(tpath).name.replace(".j2", "")
                dest_path = out_root / dest_name
                dest_path.write_text(rendered, encoding="utf-8")
                out_paths[f"{plugin.id}_{key}"] = str(dest_path)

        # Top-level env
        try:
            tmpl = self.env.get_template("common/base_env.sv.j2")
            rendered = tmpl.render(context=context)
            dest_path = out_root / "buscraft_env.sv"
            dest_path.write_text(rendered, encoding="utf-8")
            out_paths["buscraft_env"] = str(dest_path)
        except Exception as exc:
            raise GenerationError(f"Failed to generate base_env.sv: {exc}") from exc

        # Simple simulator script (VCS)
        if self.project.features.get("sim_scripts_enable", True) and self.project.simulator == "vcs":
            sim_dir = out_root / "sim" / "vcs"
            sim_dir.mkdir(parents=True, exist_ok=True)
            try:
                tmpl = self.env.get_template("sim/vcs/Makefile.j2")
                rendered = tmpl.render(context=context)
                dest_path = sim_dir / "Makefile"
                dest_path.write_text(rendered, encoding="utf-8")
                out_paths["sim_vcs_makefile"] = str(dest_path)
            except Exception as exc:
                raise GenerationError(f"Failed to generate VCS Makefile: {exc}") from exc

        return out_paths
