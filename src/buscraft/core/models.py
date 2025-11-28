from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


@dataclass
class Agent:
    name: str
    protocol_id: str  # e.g. "amba_axi"
    role: str = "master"  # "master", "slave", "monitor_only"
    parameters: Dict[str, Any] = field(default_factory=dict)
    vip_mode: str = "full"  # "full", "placeholder", "blank"


@dataclass
class SimulatorConfig:
    id: str
    label: str
    template_paths: Dict[str, str]  # compile, run, coverage_cff


@dataclass
class LicenseInfo:
    customer: str = "UNLICENSED"
    valid_till: str = "2099-12-31"
    features: Dict[str, Any] = field(default_factory=dict)
    limits: Dict[str, Any] = field(default_factory=dict)
    hostid: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    signature_valid: bool = False


@dataclass
class Project:
    name: str = "untitled"
    output_dir: str = "./buscraft_out"
    simulator: str = "vcs"
    global_params: Dict[str, Any] = field(
        default_factory=lambda: {
            "timescale": "1ns/1ps",
            "reset_active_low": True,
            "clock_name": "clk",
            "reset_name": "rst_n",
        }
    )
    agents: List[Agent] = field(default_factory=list)
    protocols_used: List[str] = field(default_factory=list)
    features: Dict[str, Any] = field(
        default_factory=lambda: {
            "scoreboard_enable": True,
            "coverage_enable": True,
            "assertions_enable": True,
            "ai_assist_enable": False,
            "sim_scripts_enable": True,
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Project":
        agents = [Agent(**a) for a in data.get("agents", [])]
        return Project(
            name=data.get("name", "untitled"),
            output_dir=data.get("output_dir", "./buscraft_out"),
            simulator=data.get("simulator", "vcs"),
            global_params=data.get("global_params", {}),
            agents=agents,
            protocols_used=data.get("protocols_used", []),
            features=data.get("features", {}),
        )
