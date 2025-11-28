from __future__ import annotations
from typing import Dict, Any
from buscraft.core.plugin_manager import ProtocolPlugin


class AxiProtocolPlugin(ProtocolPlugin):
    def __init__(self):
        super().__init__(
            id="amba_axi",
            family="amba",
            label="AMBA AXI4",
            maturity="full",
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
            "pkg": "protocols/amba/axi/axi_pkg.sv.j2",
            "agent": "protocols/amba/axi/axi_agent.sv.j2",
        }

    def get_default_parameters(self) -> Dict[str, Any]:
        return {"addr_width": 32, "data_width": 32, "id_width": 4}

    def ai_prompt_context(self) -> Dict[str, Any]:
        return {
            "protocol": "AMBA AXI4",
            "layers": ["AW", "W", "B", "AR", "R"],
        }


def get_plugin() -> ProtocolPlugin:
    return AxiProtocolPlugin()
