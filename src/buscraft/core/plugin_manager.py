from __future__ import annotations
import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Dict, Any, List

from buscraft.core.models import Project, Agent


@dataclass
class ProtocolPlugin:
    id: str
    family: str
    label: str
    maturity: str  # "full" or "placeholder"
    supports: Dict[str, bool] = field(default_factory=dict)

    def get_templates(self) -> Dict[str, str]:
        """Return logical name -> Jinja2 template path"""
        raise NotImplementedError

    def get_default_parameters(self) -> Dict[str, Any]:
        return {}

    def ai_prompt_context(self) -> Dict[str, Any]:
        return {}


_PROTOCOL_REGISTRY: Dict[str, ProtocolPlugin] = {}
_LOADED = False


def _discover_plugins() -> None:
    global _LOADED
    if _LOADED:
        return

    package_name = "buscraft.plugins"
    package = importlib.import_module(package_name)

    for finder, name, ispkg in pkgutil.iter_modules(package.__path__):
        if ispkg:
            continue
        module_name = f"{package_name}.{name}"
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            print(f"[BusCraft] Failed to import plugin {module_name}: {exc}")
            continue

        plugin_obj = None
        if hasattr(module, "get_plugin"):
            try:
                plugin_obj = module.get_plugin()
            except Exception as exc:
                print(f"[BusCraft] get_plugin() failed in {module_name}: {exc}")
                continue

        if isinstance(plugin_obj, ProtocolPlugin):
            if plugin_obj.id in _PROTOCOL_REGISTRY:
                print(f"[BusCraft] Duplicate protocol id {plugin_obj.id}, ignoring.")
            else:
                _PROTOCOL_REGISTRY[plugin_obj.id] = plugin_obj

    _LOADED = True


def get_all_protocols() -> Dict[str, ProtocolPlugin]:
    _discover_plugins()
    return dict(_PROTOCOL_REGISTRY)


def get_protocol(protocol_id: str) -> ProtocolPlugin | None:
    _discover_plugins()
    return _PROTOCOL_REGISTRY.get(protocol_id)


def protocols_for_project(project: Project) -> List[ProtocolPlugin]:
    _discover_plugins()
    result: List[ProtocolPlugin] = []
    for agent in project.agents:
        plugin = _PROTOCOL_REGISTRY.get(agent.protocol_id)
        if plugin and plugin not in result:
            result.append(plugin)
    return result
