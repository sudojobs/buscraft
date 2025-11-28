from __future__ import annotations
from typing import Dict, Any
from buscraft.core.plugin_manager import ProtocolPlugin


class I2cProtocolPlugin(ProtocolPlugin):
    def __init__(self):
        super().__init__(
            id="serial_i2c",
            family="serial",
            label="I2C",
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
            "pkg": "protocols/serial/i2c/i2c_pkg.sv.j2",
            "agent": "protocols/serial/i2c/i2c_agent.sv.j2",
        }

    def get_default_parameters(self) -> Dict[str, Any]:
        return {"addr_width": 7, "data_width": 8}

    def ai_prompt_context(self) -> Dict[str, Any]:
        return {"protocol": "I2C"}


def get_plugin() -> ProtocolPlugin:
    return I2cProtocolPlugin()
