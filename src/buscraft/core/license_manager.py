from __future__ import annotations
import json
import base64
import rsa
from pathlib import Path
from typing import Any, Dict, Union
from .models import LicenseInfo, Project

_PUB_KEY_DATA = b"""-----BEGIN RSA PUBLIC KEY-----
MIIBCgKCAQEAj518pPfAeWdt04ZLv6lL6pKWY7zHpHTSl/UYTwpNQDlGfpJaNwSa
jmZWKbaZ53pjfiH9XsTVx3+T1KO7JRvbuZ6L4cXFR6rnumg+mffe9a+vpRqRB7QR
qQMpEn9JR7Vgpx6fOCeKTJuJ/BKmn8T88eBj5zBQOoi8CGtpKAIcAao+sKXE2J+O
M0zUpY8UNF/Re4DOYlN0lJESqMNs0BXwVoQZeFEdV+pcW4vclY4s5xXzu/++kkZd
vprItTAID+daRzue2vQeFdvLcIydr/Ig7+ajRXyuO1kqUODQGZ4iFxW7yUFR+xSL
gYukHIrHleprmzY5I4l0FrRbNbf3X7MQ2wIDAQAB
-----END RSA PUBLIC KEY-----"""

_PUB_KEY = rsa.PublicKey.load_pkcs1(_PUB_KEY_DATA)

def _verify_signature(payload_dict: Dict[str, Any], signature_b64: str) -> bool:
    if not signature_b64:
        return False
    try:
        payload_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
        sig_bytes = base64.b64decode(signature_b64)
        rsa.verify(payload_bytes, sig_bytes, _PUB_KEY)
        return True
    except Exception:
        return False

def load_license(path: Union[str, Path]) -> LicenseInfo:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return load_license_from_dict(raw)

def load_license_from_dict(raw: Dict[str, Any]) -> LicenseInfo:
    payload = {k: v for k, v in raw.items() if k != "signature"}
    signature = raw.get("signature", "")
    valid = _verify_signature(payload, signature)

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
        "customer": "UNLICENSED_DEMO",
        "valid_till": "2099-12-31",
        "features": {
            "amba_axi": False,
            "amba_apb": True,
            "amba_ahb": False,
            "amba_chi": False,
            "serial_i2c": False,
            "generic_blank": True,
        },
        "limits": {"max_agents": 2, "max_protocols_per_project": 1},
        "hostid": None,
        "signature": ""
    }
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
