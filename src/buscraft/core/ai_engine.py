from __future__ import annotations
from typing import Dict, Any


class AIEngine:
    def generate_project_config(self, natural_language_desc: str, current_config: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def suggest_coverage(self, protocol_id: str, agent_config: Dict[str, Any]) -> str:
        raise NotImplementedError

    def suggest_assertions(self, protocol_id: str, agent_config: Dict[str, Any]) -> str:
        raise NotImplementedError


class DummyAIEngine(AIEngine):
    """Offline, no-network AI stub."""

    def generate_project_config(self, natural_language_desc: str, current_config: Dict[str, Any]) -> Dict[str, Any]:
        cfg = dict(current_config)
        notes = list(cfg.get("notes", []))
        notes.append(f"AI stub: interpreted description: {natural_language_desc[:80]}")
        cfg["notes"] = notes
        return cfg

    def suggest_coverage(self, protocol_id: str, agent_config: Dict[str, Any]) -> str:
        return f"// TODO: coverage suggestions for protocol {protocol_id}\n"

    def suggest_assertions(self, protocol_id: str, agent_config: Dict[str, Any]) -> str:
        return f"// TODO: assertion suggestions for protocol {protocol_id}\n"


class LocalLLMAIEngine(DummyAIEngine):
    """Stub for future integration with a local LLM server (e.g. llama.cpp + GGUF).

    Intended usage:
      - Configure base URL and model via config file or UI.
      - Send HTTP requests to local server with prompt / context.
      - Stay fully offline (no external network).

    For now, this class behaves like DummyAIEngine.
    """
    # Override methods here when integrating with your local LLM server.
    pass
