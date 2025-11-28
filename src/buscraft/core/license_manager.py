from __future__ import annotations
import json
import hmac
import hashlib
from pathlib import Path
from typing import Any, Dict, Union
from .models import LicenseInfo, Project

_SECRET = b"BUSCRAFT_DEMO_SECRET"


def _calc_signature(payload: Dict[str, Any]) -> str:
    """Dummy HMAC-based signature over all fields except 'signature'."""
    data = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hmac.new(_SECRET, data, hashlib.sha256).hexdigest()


def load_license(path: Union[str, Path]) -> LicenseInfo:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    payload = {k: v for k, v in raw.items() if k != "signature"}
    signature = raw.get("signature", "")
    calc = _calc_signature(payload)
    valid = signature == calc or signature == "DEMO"  # allow simple DEMO

    lic = LicenseInfo(
        customer=raw.get("customer", "UNKNOWN"),
        valid_till=raw.get("valid_till", "2099-12-31"),
        features=raw.get("features", {}),
        limits=raw.get("limits", {}),
        hostid=raw.get("hostid"),
        raw_data=raw,
        signature_valid=valid,
    )
    return lic


def load_license_from_dict(raw: Dict[str, Any]) -> LicenseInfo:
    payload = {k: v for k, v in raw.items() if k != "signature"}
    signature = raw.get("signature", "")
    calc = _calc_signature(payload)
    valid = signature == calc or signature == "DEMO"

    return LicenseInfo(
        customer=raw.get("customer", "UNKNOWN"),
        valid_till=raw.get("valid_till", "2099-12-31"),
        features=raw.get("features", {}),
        limits=raw.get("limits", {}),
        hostid=raw.get("hostid"),
        raw_data=raw,
        signature_valid=valid,
    )


def create_demo_license() -> LicenseInfo:
    raw = {
        "customer": "DEMO_USER",
        "valid_till": "2099-12-31",
        "features": {
            "amba_axi": True,
            "amba_apb": True,
            "amba_ahb": True,
            "amba_chi": True,
            "serial_i2c": True,
            "generic_blank": True,
        },
        "limits": {"max_agents": 128, "max_protocols_per_project": 32},
        "hostid": None,
    }
    raw["signature"] = _calc_signature(raw)
    return load_license_from_dict(raw)


def check_feature(lic: LicenseInfo | None, protocol_id: str) -> Any:
    if lic is None:
        return True
    return lic.features.get(protocol_id, False)


def check_limits(lic: LicenseInfo | None, project: Project) -> bool:
    if lic is None:
        return True
    limits = lic.limits or {}
    max_agents = limits.get("max_agents")
    max_protos = limits.get("max_protocols_per_project")
    if max_agents is not None and len(project.agents) > max_agents:
        return False
    if max_protos is not None and len(set(a.protocol_id for a in project.agents)) > max_protos:
        return False
    return True


def get_license_summary(lic: LicenseInfo | None) -> str:
    if lic is None:
        return "No license loaded. Using built-in demo mode."
    lines = [
        f"Customer: {lic.customer}",
        f"Valid till: {lic.valid_till}",
        f"Signature valid: {lic.signature_valid}",
        "",
        "Features:",
    ]
    for k, v in (lic.features or {}).items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("Limits:")
    for k, v in (lic.limits or {}).items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)
