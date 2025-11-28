from __future__ import annotations
from pathlib import Path
from typing import Union
import graphviz

from .models import Project


def generate_diagram(project: Project, output_path: Union[str, Path]) -> str:
    """Generate a simple bus-level diagram using Graphviz and return PNG path."""
    output_path = Path(output_path)
    base = output_path.with_suffix("")

    dot_lines = [
        'digraph BusCraft {',
        '  rankdir=LR;',
        '  node [shape=box, style=filled, fillcolor="#222222", fontcolor="white"];',
        '  env [label="buscraft_env"];',
        '  dut [label="DUT", shape=box3d, fillcolor="#444444"];',
        '  scoreboard [label="scoreboard", fillcolor="#333333"];',
    ]

    for idx, agent in enumerate(project.agents):
        node_name = f"agent_{idx}"
        label = f"{agent.name}\\n({agent.protocol_id}, {agent.role})"
        dot_lines.append(f'  {node_name} [label="{label}"];')
        dot_lines.append(f"  {node_name} -> dut;")
        dot_lines.append(f"  {node_name} -> scoreboard;")

    dot_lines.append("  env -> dut;")
    dot_lines.append("  env -> scoreboard;")
    dot_lines.append("}")

    dot_src = "\n".join(dot_lines)
    src = graphviz.Source(dot_src)
    base.parent.mkdir(parents=True, exist_ok=True)
    out = src.render(filename=str(base), format="png", cleanup=True)
    return out
