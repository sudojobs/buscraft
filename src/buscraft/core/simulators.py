from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass
class SimulatorConfigDef:
    id: str
    label: str
    template_paths: Dict[str, str]  # compile, run, coverage

# Placeholder for future simulator plugin system.
