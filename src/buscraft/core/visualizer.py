"""
BusCraft Visualizer — Generates rich verification architecture diagrams.

Supports:
  - Graphviz (structural block diagrams) — default
  - PlantUML (behavioral sequence/state diagrams) — optional
"""
from __future__ import annotations
from pathlib import Path
from typing import Union, Optional
import graphviz

from .models import Project


# ═══════════════════════════════════════════════════════════════════════════════
# Graphviz — Structural Block Diagrams
# ═══════════════════════════════════════════════════════════════════════════════

# Color palette
COLORS = {
    "bg":         "#1a1a2e",
    "env":        "#16213e",
    "agent":      "#0f3460",
    "dut":        "#e94560",
    "scoreboard": "#533483",
    "coverage":   "#2b9348",
    "sequencer":  "#1b4965",
    "monitor":    "#5a189a",
    "driver":     "#48639C",
    "font":       "#ffffff",
    "edge":       "#aaaaaa",
    "edge_data":  "#00b4d8",
    "edge_ctrl":  "#e63946",
}


def generate_diagram(project: Project, output_path: Union[str, Path], fmt: str = "png") -> str:
    """Generate a detailed UVM architecture diagram using Graphviz.
    
    Args:
        project: BusCraft project to visualize.
        output_path: Output file path.
        fmt: Output format (png, svg, pdf).
    
    Returns:
        Generated file path.
    """
    output_path = Path(output_path)
    base = output_path.with_suffix("")

    dot = graphviz.Digraph(
        "BusCraft",
        format=fmt,
        engine="dot",
    )
    
    # Global graph attributes
    dot.attr(
        rankdir="TB",
        bgcolor=COLORS["bg"],
        fontcolor=COLORS["font"],
        fontname="Helvetica",
        fontsize="14",
        label=f"<<B>{project.name}</B> — UVM Testbench Architecture>",
        labelloc="t",
        pad="0.5",
        nodesep="0.8",
        ranksep="1.0",
    )
    
    # Default node style
    dot.attr("node",
        shape="record",
        style="filled,rounded",
        fontname="Helvetica",
        fontsize="11",
        fontcolor=COLORS["font"],
        penwidth="0",
        margin="0.2,0.15",
    )
    
    dot.attr("edge",
        fontname="Helvetica",
        fontsize="9",
        fontcolor=COLORS["edge"],
        color=COLORS["edge"],
        arrowsize="0.8",
    )
    
    # --- Top-level test ---
    dot.node("test", label="{test_base|{run_phase|raise_objection}}",
             fillcolor="#1d3557", shape="record")
    
    # --- Environment (subgraph for grouping) ---
    with dot.subgraph(name="cluster_env") as env:
        env.attr(
            label="buscraft_env",
            style="filled,rounded",
            color="#333355",
            fillcolor=COLORS["env"],
            fontcolor=COLORS["font"],
            fontname="Helvetica Bold",
            fontsize="13",
        )
        
        # Agents
        for idx, agent in enumerate(project.agents):
            agent_id = f"agent_{idx}"
            protocol_label = agent.protocol_id.replace("amba_", "").upper()
            
            with env.subgraph(name=f"cluster_{agent_id}") as ag:
                ag.attr(
                    label=f"{agent.name} ({protocol_label})",
                    style="filled,rounded",
                    color="#1a1a2e",
                    fillcolor=COLORS["agent"],
                    fontcolor=COLORS["font"],
                    fontsize="11",
                )
                
                ag.node(f"{agent_id}_sqr", label="sequencer",
                       fillcolor=COLORS["sequencer"])
                ag.node(f"{agent_id}_drv", label="driver",
                       fillcolor=COLORS["driver"])
                ag.node(f"{agent_id}_mon", label="monitor",
                       fillcolor=COLORS["monitor"])
                
                # Internal agent connections
                ag.edge(f"{agent_id}_sqr", f"{agent_id}_drv",
                       label="seq_item", color=COLORS["edge_data"])
        
        # Scoreboard
        if project.features.get("scoreboard_enable", True):
            env.node("scoreboard",
                    label="{scoreboard|{expected|actual|compare}}",
                    fillcolor=COLORS["scoreboard"])
        
        # Coverage
        if project.features.get("coverage_enable", True):
            env.node("coverage",
                    label="{coverage|{functional|protocol}}",
                    fillcolor=COLORS["coverage"])
    
    # --- DUT ---
    port_labels = []
    for idx, agent in enumerate(project.agents):
        protocol = agent.protocol_id.replace("amba_", "").upper()
        port_labels.append(f"<p{idx}> {protocol}")
    
    ports_str = "|".join(port_labels) if port_labels else "ports"
    dot.node("dut",
            label=f"{{DUT ({project.name})|{{{ports_str}}}}}",
            fillcolor=COLORS["dut"],
            shape="record",
            style="filled,bold",
            penwidth="2",
            color="#ff6b6b")
    
    # --- Connections ---
    dot.edge("test", "cluster_env", style="dashed", label="create")
    
    for idx, agent in enumerate(project.agents):
        agent_id = f"agent_{idx}"
        
        # Driver → DUT
        dot.edge(f"{agent_id}_drv", f"dut:p{idx}",
                label="drive", color=COLORS["edge_data"], penwidth="1.5")
        
        # DUT → Monitor
        dot.edge(f"dut:p{idx}", f"{agent_id}_mon",
                label="sample", color=COLORS["edge_ctrl"], style="dashed")
        
        # Monitor → Scoreboard
        if project.features.get("scoreboard_enable", True):
            dot.edge(f"{agent_id}_mon", "scoreboard",
                    label="analysis", color=COLORS["edge"], style="dotted")
        
        # Monitor → Coverage
        if project.features.get("coverage_enable", True):
            dot.edge(f"{agent_id}_mon", "coverage",
                    label="sample", color=COLORS["edge"], style="dotted")
    
    # Render
    base.parent.mkdir(parents=True, exist_ok=True)
    out = dot.render(filename=str(base), cleanup=True)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# PlantUML — Behavioral Diagrams (sequence, state)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_puml_sequence(project: Project, output_path: Union[str, Path]) -> str:
    """Generate a PlantUML sequence diagram showing a typical UVM transaction flow.
    
    Returns the .puml file path (user renders with plantuml.jar or a web service).
    """
    output_path = Path(output_path).with_suffix(".puml")
    
    agents = project.agents
    if not agents:
        agents_dummy = [type("A", (), {"name": "agent", "protocol_id": "generic"})()]
    
    lines = [
        "@startuml",
        f"title {project.name} — UVM Transaction Flow",
        "skinparam backgroundColor #1a1a2e",
        "skinparam defaultFontColor #ffffff",
        "skinparam sequenceArrowColor #00b4d8",
        "skinparam sequenceLifeLineBorderColor #aaaaaa",
        "skinparam participantBackgroundColor #16213e",
        "skinparam participantBorderColor #0f3460",
        "skinparam noteBorderColor #533483",
        "skinparam noteBackgroundColor #2b2b4e",
        "",
        'participant "Test" as test',
        'participant "Environment" as env',
    ]
    
    for idx, agent in enumerate(agents):
        proto = agent.protocol_id.replace("amba_", "").upper()
        lines.append(f'participant "{agent.name}\\n({proto})" as agent_{idx}')
        lines.append(f'participant "Sequencer" as sqr_{idx}')
        lines.append(f'participant "Driver" as drv_{idx}')
        lines.append(f'participant "Monitor" as mon_{idx}')
    
    lines.append('participant "DUT" as dut')
    
    if project.features.get("scoreboard_enable", True):
        lines.append('participant "Scoreboard" as scb')
    
    lines.append("")
    lines.append("== Initialization ==")
    lines.append("test -> env : create()")
    
    for idx, agent in enumerate(agents):
        lines.append(f"env -> agent_{idx} : build_phase()")
        lines.append(f"agent_{idx} -> sqr_{idx} : create()")
        lines.append(f"agent_{idx} -> drv_{idx} : create()")
        lines.append(f"agent_{idx} -> mon_{idx} : create()")
    
    lines.append("")
    lines.append("== Run Phase ==")
    
    for idx, agent in enumerate(agents):
        proto = agent.protocol_id.replace("amba_", "").upper()
        lines.append(f"test -> sqr_{idx} : start_sequence()")
        lines.append(f"sqr_{idx} -> drv_{idx} : {proto}_seq_item")
        lines.append(f"drv_{idx} -> dut : drive signals")
        lines.append(f"dut --> mon_{idx} : sample signals")
        
        if project.features.get("scoreboard_enable", True):
            lines.append(f"mon_{idx} -> scb : analysis_port.write()")
            lines.append(f"note right of scb : compare\\nexpected vs actual")
    
    lines.append("")
    lines.append("== Cleanup ==")
    lines.append("test -> env : drop_objection()")
    
    lines.append("@enduml")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return str(output_path)


def generate_puml_state(project: Project, output_path: Union[str, Path]) -> str:
    """Generate a PlantUML state diagram for the protocol FSM."""
    output_path = Path(output_path).with_suffix(".puml")
    
    agent = project.agents[0] if project.agents else None
    proto_id = agent.protocol_id if agent else "generic"
    
    lines = [
        "@startuml",
        f"title {project.name} — Protocol State Machine",
        "skinparam backgroundColor #1a1a2e",
        "skinparam defaultFontColor #ffffff",
        "skinparam stateBorderColor #0f3460",
        "skinparam stateBackgroundColor #16213e",
        "skinparam stateArrowColor #00b4d8",
        "",
    ]
    
    if "apb" in proto_id:
        lines.extend([
            "state IDLE",
            "state SETUP",
            "state ACCESS",
            "",
            "[*] --> IDLE",
            "IDLE --> SETUP : PSEL=1",
            "SETUP --> ACCESS : PENABLE=1",
            "ACCESS --> IDLE : PREADY=1\\n(transfer done)",
            "ACCESS --> ACCESS : PREADY=0\\n(wait state)",
            "",
            "note right of SETUP",
            "  Address & control",
            "  signals valid",
            "end note",
            "",
            "note right of ACCESS",
            "  Data transfer",
            "  Wait for PREADY",
            "end note",
        ])
    elif "axi" in proto_id:
        lines.extend([
            "state IDLE",
            "state AW_VALID : Write Address",
            "state W_VALID : Write Data",
            "state B_RESP : Write Response",
            "state AR_VALID : Read Address",
            "state R_DATA : Read Data",
            "",
            "[*] --> IDLE",
            "IDLE --> AW_VALID : write request",
            "AW_VALID --> W_VALID : AWREADY",
            "W_VALID --> B_RESP : WLAST & WREADY",
            "B_RESP --> IDLE : BVALID & BREADY",
            "",
            "IDLE --> AR_VALID : read request",
            "AR_VALID --> R_DATA : ARREADY",
            "R_DATA --> IDLE : RLAST & RVALID & RREADY",
        ])
    elif "ahb" in proto_id:
        lines.extend([
            "state IDLE : HTRANS=00",
            "state BUSY : HTRANS=01",
            "state NONSEQ : HTRANS=10",
            "state SEQ : HTRANS=11",
            "",
            "[*] --> IDLE",
            "IDLE --> NONSEQ : transfer start",
            "NONSEQ --> SEQ : HREADY=1\\n(burst continues)",
            "SEQ --> SEQ : HREADY=1\\n(burst continues)",
            "SEQ --> IDLE : last beat",
            "NONSEQ --> IDLE : single transfer\\nHREADY=1",
            "NONSEQ --> BUSY : master wait",
            "BUSY --> NONSEQ : continue",
        ])
    else:
        lines.extend([
            "state IDLE",
            "state TRANSFER",
            "state COMPLETE",
            "",
            "[*] --> IDLE",
            "IDLE --> TRANSFER : request",
            "TRANSFER --> COMPLETE : done",
            "COMPLETE --> IDLE : reset",
        ])
    
    lines.append("")
    lines.append("@enduml")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return str(output_path)


def render_puml(puml_path: str, fmt: str = "png") -> Optional[str]:
    """Try to render a .puml file using plantuml.jar or the plantuml CLI.
    
    Returns the output image path, or None if PlantUML is not available.
    """
    import shutil
    import subprocess
    
    puml_path = Path(puml_path)
    
    # Try plantuml CLI first
    if shutil.which("plantuml"):
        try:
            subprocess.run(
                ["plantuml", f"-t{fmt}", str(puml_path)],
                capture_output=True, timeout=30,
            )
            output = puml_path.with_suffix(f".{fmt}")
            if output.exists():
                return str(output)
        except Exception:
            pass
    
    # Try java -jar plantuml.jar
    jar_locations = [
        Path.home() / ".local" / "share" / "plantuml" / "plantuml.jar",
        Path("/usr/local/lib/plantuml.jar"),
        Path("/opt/plantuml/plantuml.jar"),
    ]
    
    if shutil.which("java"):
        for jar in jar_locations:
            if jar.exists():
                try:
                    subprocess.run(
                        ["java", "-jar", str(jar), f"-t{fmt}", str(puml_path)],
                        capture_output=True, timeout=60,
                    )
                    output = puml_path.with_suffix(f".{fmt}")
                    if output.exists():
                        return str(output)
                except Exception:
                    pass
    
    return None  # PlantUML not available — user has the .puml file to render elsewhere


# ═══════════════════════════════════════════════════════════════════════════════
# GTKWave — Waveform Config Generator
# ═══════════════════════════════════════════════════════════════════════════════

def generate_gtkwave_savefile(project: Project, output_path: Union[str, Path]) -> str:
    """Generate a GTKWave save file (.gtkw) with pre-configured signal groups.
    
    This auto-organizes signals by agent/protocol when the user opens
    a VCD file in GTKWave, instead of them having to manually find signals.
    """
    output_path = Path(output_path).with_suffix(".gtkw")
    
    lines = [
        "[*]",
        f"[dumpfile] \"{project.name}_waves.vcd\"",
        "[dumpfile_mtime] \"0\"",
        "[savefile] \"{output_path.name}\"",
        "[timestart] 0",
        "[size] 1400 800",
        "[pos] -1 -1",
        "",
        "# ═══════════════════════════════",
        "# Auto-generated by BusCraft",
        "# ═══════════════════════════════",
        "",
        "# Clock & Reset",
        f"@28",
        f"tb_top.{project.global_params.get('clock_name', 'clk')}",
        f"tb_top.{project.global_params.get('reset_name', 'rst_n')}",
        "@200",
        "-",
    ]
    
    from .plugin_manager import get_protocol
    
    for idx, agent in enumerate(project.agents):
        proto = agent.protocol_id.replace("amba_", "").upper()
        lines.append(f"# {agent.name} ({proto})")
        lines.append(f"@200")
        lines.append(f"-{agent.name}")
        
        plugin = get_protocol(agent.protocol_id)
        if plugin:
            params = plugin.get_default_parameters()
            
            # Add key protocol signals to the waveform view
            if "apb" in agent.protocol_id:
                for sig in ["PSEL", "PENABLE", "PWRITE", "PREADY", "PSLVERR"]:
                    lines.append(f"@28")
                    lines.append(f"tb_top.{agent.name}_vif.{sig}")
                for sig in ["PADDR", "PWDATA", "PRDATA"]:
                    lines.append(f"@22")
                    lines.append(f"tb_top.{agent.name}_vif.{sig}[{params.get('data_width', 32) - 1}:0]")
            
            elif "axi" in agent.protocol_id:
                for sig in ["AWVALID", "AWREADY", "WVALID", "WREADY", "BVALID", "BREADY",
                            "ARVALID", "ARREADY", "RVALID", "RREADY"]:
                    lines.append(f"@28")
                    lines.append(f"tb_top.{agent.name}_vif.{sig}")
                for sig in ["AWADDR", "ARADDR", "WDATA", "RDATA"]:
                    lines.append(f"@22")
                    lines.append(f"tb_top.{agent.name}_vif.{sig}[{params.get('data_width', 32) - 1}:0]")
            
            elif "ahb" in agent.protocol_id:
                for sig in ["HWRITE", "HREADY", "HSEL"]:
                    lines.append(f"@28")
                    lines.append(f"tb_top.{agent.name}_vif.{sig}")
                for sig in ["HADDR", "HWDATA", "HRDATA", "HTRANS", "HBURST"]:
                    lines.append(f"@22")
                    lines.append(f"tb_top.{agent.name}_vif.{sig}[{params.get('data_width', 32) - 1}:0]")
        
        lines.append(f"@200")
        lines.append("-")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return str(output_path)
