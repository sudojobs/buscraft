from __future__ import annotations
from typing import Dict, Any
from buscraft.core.plugin_manager import ProtocolPlugin


class ApbProtocolPlugin(ProtocolPlugin):
    def __init__(self):
        super().__init__(
            id="amba_apb",
            family="amba",
            label="AMBA APB",
            maturity="full",
            supports={
                "vip": True,
                "bfm": True,
                "coverage": False,
                "assertions": False,
                "blank_env": False,
            },
        )

    def get_templates(self) -> Dict[str, str]:
        return {
            "pkg": "protocols/amba/apb/apb_pkg.sv.j2",
            "agent": "protocols/amba/apb/apb_agent.sv.j2",
        }

    def get_default_parameters(self) -> Dict[str, Any]:
        return {"addr_width": 16, "data_width": 32}

    def ai_prompt_context(self) -> Dict[str, Any]:
        return {"protocol": "AMBA APB"}


def get_plugin() -> ProtocolPlugin:
    return ApbProtocolPlugin()
