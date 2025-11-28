from __future__ import annotations
from typing import Dict, Any
from buscraft.core.plugin_manager import ProtocolPlugin


class ChiProtocolPlugin(ProtocolPlugin):
    def __init__(self):
        super().__init__(
            id="amba_chi",
            family="amba",
            label="AMBA CHI",
            maturity="placeholder",
            supports={
                "vip": True,
                "bfm": True,
                "coverage": True,
                "assertions": True,
                "blank_env": False,
            },
        )

    def get_templates(self) -> Dict[str, str]:
        return {
            "pkg": "protocols/amba/chi/chi_pkg.sv.j2",
            "agent": "protocols/amba/chi/chi_agent.sv.j2",
        }

    def get_default_parameters(self) -> Dict[str, Any]:
        return {"addr_width": 48, "data_width": 64}

    def ai_prompt_context(self) -> Dict[str, Any]:
        return {"protocol": "AMBA CHI"}


def get_plugin() -> ProtocolPlugin:
    return ChiProtocolPlugin()
