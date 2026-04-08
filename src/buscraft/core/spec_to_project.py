"""
BusCraft Spec-to-Project Converter — Transforms an analyzed SpecModel
into a fully configured BusCraft Project ready for code generation.
"""
from __future__ import annotations
from typing import Optional, Dict, Any

from .models import Project, Agent
from .spec_analyzer import SpecModel
from .plugin_manager import get_protocol, get_all_protocols


# Mapping from detected protocol names to BusCraft plugin IDs
PROTOCOL_MAP = {
    "axi": "amba_axi",
    "axi4": "amba_axi",
    "axi4-lite": "amba_axi",
    "apb": "amba_apb",
    "ahb": "amba_ahb",
    "ahb-lite": "amba_ahb",
    "chi": "amba_chi",
    "i2c": "serial_i2c",
    "spi": "generic_blank",
    "uart": "generic_blank",
    "pcie": "generic_blank",
    "usb": "generic_blank",
    "ethernet": "generic_blank",
    "custom": "generic_blank",
    "unknown": "generic_blank",
}

# Signal name patterns that hint at specific protocols
SIGNAL_PROTOCOL_HINTS = {
    "amba_axi": ["AWADDR", "WDATA", "BRESP", "ARADDR", "RDATA", "AWVALID", "WVALID", "BREADY", "ARVALID", "RREADY"],
    "amba_apb": ["PSEL", "PENABLE", "PWRITE", "PADDR", "PWDATA", "PRDATA", "PREADY"],
    "amba_ahb": ["HADDR", "HWDATA", "HRDATA", "HTRANS", "HBURST", "HSIZE", "HREADY"],
    "amba_chi": ["TXREQ", "TXRSP", "TXDAT", "RXREQ", "RXRSP", "RXDAT"],
    "serial_i2c": ["SDA", "SCL"],
}


def _detect_protocol_from_signals(spec: SpecModel) -> str:
    """Use signal names to confirm or override protocol detection."""
    signal_names = {s.name.upper() for s in spec.signals}
    
    best_match = ""
    best_score = 0
    
    for plugin_id, hint_signals in SIGNAL_PROTOCOL_HINTS.items():
        matches = sum(1 for hs in hint_signals if any(hs in sn for sn in signal_names))
        if matches > best_score:
            best_score = matches
            best_match = plugin_id
    
    # Only override if we have a strong signal match (3+ signals)
    if best_score >= 3:
        return best_match
    
    return ""


def _infer_agent_parameters(spec: SpecModel, plugin_id: str) -> Dict[str, Any]:
    """Infer agent parameters (signal widths, etc.) from extracted spec data."""
    params: Dict[str, Any] = {}
    
    # Get default parameters from the plugin
    plugin = get_protocol(plugin_id)
    if plugin:
        params = plugin.get_default_parameters().copy()
    
    # Override with actual widths from spec signals
    signal_map = {s.name.upper(): s for s in spec.signals}
    
    # Common AXI signal width mappings
    width_mappings = {
        "addr_width": ["AWADDR", "ARADDR", "HADDR", "PADDR"],
        "data_width": ["WDATA", "RDATA", "HWDATA", "HRDATA", "PWDATA", "PRDATA"],
        "id_width": ["AWID", "ARID", "BID", "RID"],
    }
    
    for param_name, signal_names in width_mappings.items():
        for sn in signal_names:
            if sn in signal_map and signal_map[sn].width > 1:
                params[param_name] = signal_map[sn].width
                break  # Use the first match
    
    return params


def _determine_agent_role(spec: SpecModel) -> str:
    """Determine if the spec describes a master, slave, or monitor."""
    text_lower = spec.description.lower()
    
    # Check signal directions for clues
    output_signals = [s for s in spec.signals if s.direction == "output"]
    input_signals = [s for s in spec.signals if s.direction == "input"]
    
    # Heuristic: If the IP drives address/write channels, it's likely a master
    master_signals = {"AWADDR", "ARADDR", "WDATA", "AWVALID", "ARVALID"}
    drives_master = any(
        s.name.upper() in master_signals
        for s in output_signals
    )
    
    if drives_master or "master" in text_lower:
        return "master"
    elif "slave" in text_lower or "peripheral" in text_lower:
        return "slave"
    else:
        return "master"  # Default


def spec_to_project(
    spec: SpecModel,
    project_name: Optional[str] = None,
    output_dir: str = "./buscraft_out",
    simulator: str = "vcs",
) -> Project:
    """Convert an analyzed SpecModel into a BusCraft Project.
    
    Args:
        spec: The analyzed specification model.
        project_name: Override for the project name (defaults to spec IP name).
        output_dir: Output directory for generated code.
        simulator: Target simulator.
    
    Returns:
        A fully configured Project ready for code generation.
    """
    name = project_name or spec.ip_name or "spec_project"
    
    # --- Resolve protocol ---
    # First try the AI-detected protocol
    protocol_key = spec.protocol_type.lower().replace(" ", "").replace("-", "")
    plugin_id = PROTOCOL_MAP.get(protocol_key, "generic_blank")
    
    # Then try signal-based detection to confirm or override
    signal_detected = _detect_protocol_from_signals(spec)
    if signal_detected:
        plugin_id = signal_detected
    
    # Verify the plugin actually exists
    if not get_protocol(plugin_id):
        plugin_id = "generic_blank"
    
    # --- Build agent parameters ---
    agent_params = _infer_agent_parameters(spec, plugin_id)
    
    # --- Determine agent role ---
    agent_role = _determine_agent_role(spec)
    
    # --- Infer global params ---
    clock_name = spec.clock_signals[0] if spec.clock_signals else "clk"
    reset_name = spec.reset_signals[0] if spec.reset_signals else "rst_n"
    reset_active_low = "n" in reset_name.lower() or "neg" in reset_name.lower()
    
    # --- Create the project ---
    project = Project(
        name=name,
        output_dir=output_dir,
        simulator=simulator,
        global_params={
            "timescale": "1ns/1ps",
            "reset_active_low": reset_active_low,
            "clock_name": clock_name,
            "reset_name": reset_name,
        },
        agents=[
            Agent(
                name=f"{name}_agent",
                protocol_id=plugin_id,
                role=agent_role,
                parameters=agent_params,
                vip_mode="full",
            )
        ],
        protocols_used=[plugin_id],
        features={
            "scoreboard_enable": True,
            "coverage_enable": True,
            "assertions_enable": len(spec.timing_constraints) > 0,
            "ai_assist_enable": False,
            "sim_scripts_enable": True,
        },
    )
    
    return project


def spec_summary(spec: SpecModel) -> str:
    """Generate a human-readable summary of extracted spec data."""
    lines = [
        f"IP Name:      {spec.ip_name}",
        f"Protocol:     {spec.protocol_type} (confidence: {spec.protocol_confidence:.0%})",
        f"Signals:      {len(spec.signals)} found",
        f"Registers:    {len(spec.registers)} found",
        f"Timing Rules: {len(spec.timing_constraints)} found",
        f"Clock(s):     {', '.join(spec.clock_signals) if spec.clock_signals else 'auto-detect'}",
        f"Reset(s):     {', '.join(spec.reset_signals) if spec.reset_signals else 'auto-detect'}",
        f"Transfers:    {', '.join(spec.transfer_modes) if spec.transfer_modes else 'not specified'}",
        f"Errors:       {', '.join(spec.error_conditions) if spec.error_conditions else 'none detected'}",
    ]
    
    if spec.signals:
        lines.append("\nKey Signals:")
        for sig in spec.signals[:10]:  # Show first 10
            width_str = f"[{sig.width-1}:0]" if sig.width > 1 else ""
            lines.append(f"  {sig.direction:6s}  {sig.name}{width_str}  — {sig.description}")
        if len(spec.signals) > 10:
            lines.append(f"  ... and {len(spec.signals) - 10} more")
    
    if spec.registers:
        lines.append("\nRegister Map:")
        for reg in spec.registers[:8]:
            lines.append(f"  {reg.offset}  {reg.name} ({reg.access}, {reg.width}-bit)  — {reg.description}")
        if len(spec.registers) > 8:
            lines.append(f"  ... and {len(spec.registers) - 8} more")
    
    return "\n".join(lines)
