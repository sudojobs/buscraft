from __future__ import annotations
from typing import Dict, Any
from buscraft.core.plugin_manager import ProtocolPlugin


class GenericBlankPlugin(ProtocolPlugin):
    def __init__(self):
        super().__init__(
            id="generic_blank",
            family="generic",
            label="Generic Blank Env",
            maturity="placeholder",
            supports={
                "vip": False,
                "bfm": False,
                "coverage": False,
                "assertions": False,
                "blank_env": True,
            },
        )

    def get_templates(self) -> Dict[str, str]:
        return {
            "env": "protocols/generic/blank_env.sv.j2",
        }

    def get_default_parameters(self) -> Dict[str, Any]:
        return {}

    def ai_prompt_context(self) -> Dict[str, Any]:
        return {"protocol": "GENERIC"}


def get_plugin() -> ProtocolPlugin:
    return GenericBlankPlugin()
