"""BusCraft CLI - Command-line interface for BusCraft UVM VIP generator."""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from pyfiglet import figlet_format

from buscraft.core.models import Project, Agent
from buscraft.core.project_io import load_project, save_project
from buscraft.core.generator import Generator, GenerationError
from buscraft.core.plugin_manager import get_all_protocols, get_protocol
from buscraft.core.visualizer import generate_diagram

app = typer.Typer(
    name="buscraftcli",
    help="BusCraft - UVM VIP Generator CLI",
    add_completion=True,
)
console = Console()


def show_banner():
    """Display the BusCraft banner."""
    banner_text = figlet_format("BusCraft", font="slant")
    banner_panel = Panel(
        f"[bold cyan]{banner_text}[/bold cyan]\n"
        "[dim]Universal Verification Methodology (UVM) VIP Generator[/dim]\n"
        "[dim]Version 0.1.0[/dim]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(banner_panel)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
):
    """BusCraft CLI - UVM VIP Generator."""
    if version:
        console.print("[bold cyan]BusCraft[/bold cyan] version [bold]0.1.0[/bold]")
        raise typer.Exit()
    
    if ctx.invoked_subcommand is None:
        show_banner()
        console.print("\n[bold]Welcome to BusCraft![/bold]")
        console.print("Use [cyan]buscraftcli --help[/cyan] to see available commands.\n")


@app.command()
def gui():
    """Launch the BusCraft GUI application."""
    console.print("[bold cyan]Launching BusCraft GUI...[/bold cyan]")
    import subprocess
    try:
        # Launch the GUI using the existing buscraft module
        result = subprocess.run([sys.executable, "-m", "buscraft.main"], check=True)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error:[/bold red] Failed to launch GUI (exit code {e.returncode})")
        raise typer.Exit(e.returncode)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def new(
    name: str = typer.Option(..., "--name", "-n", help="Project name"),
    output_dir: str = typer.Option("./buscraft_out", "--output", "-o", help="Output directory"),
    simulator: str = typer.Option("vcs", "--simulator", "-s", help="Simulator (vcs, questa, etc.)"),
    save_to: Optional[str] = typer.Option(None, "--save", help="Save project to file"),
):
    """Create a new BusCraft project."""
    show_banner()
    
    project = Project(
        name=name,
        output_dir=output_dir,
        simulator=simulator,
    )
    
    console.print(f"\n[bold green]✓[/bold green] Created new project: [bold]{name}[/bold]")
    console.print(f"  Output directory: [cyan]{output_dir}[/cyan]")
    console.print(f"  Simulator: [cyan]{simulator}[/cyan]")
    
    if save_to:
        save_path = Path(save_to)
        save_project(project, save_path)
        console.print(f"\n[bold green]✓[/bold green] Saved project to: [cyan]{save_path}[/cyan]")
    else:
        console.print("\n[dim]Use --save to save the project configuration.[/dim]")


@app.command()
def add_agent(
    project_file: str = typer.Argument(..., help="Path to project JSON file"),
    name: str = typer.Option(..., "--name", "-n", help="Agent name"),
    protocol: str = typer.Option(..., "--protocol", "-p", help="Protocol ID (e.g., amba_axi)"),
    role: str = typer.Option("master", "--role", "-r", help="Agent role (master/slave/monitor_only)"),
    vip_mode: str = typer.Option("full", "--vip-mode", help="VIP mode (full/placeholder/blank)"),
):
    """Add an agent to an existing project."""
    try:
        project = load_project(project_file)
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] Project file not found: {project_file}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to load project: {e}")
        raise typer.Exit(1)
    
    # Validate protocol
    plugin = get_protocol(protocol)
    if not plugin:
        console.print(f"[bold red]Error:[/bold red] Unknown protocol: {protocol}")
        console.print("Use [cyan]buscraftcli list-protocols[/cyan] to see available protocols.")
        raise typer.Exit(1)
    
    # Create agent
    agent = Agent(
        name=name,
        protocol_id=protocol,
        role=role,
        vip_mode=vip_mode,
        parameters=plugin.get_default_parameters(),
    )
    
    project.agents.append(agent)
    if protocol not in project.protocols_used:
        project.protocols_used.append(protocol)
    
    save_project(project, project_file)
    
    console.print(f"\n[bold green]✓[/bold green] Added agent: [bold]{name}[/bold]")
    console.print(f"  Protocol: [cyan]{protocol}[/cyan] ({plugin.label})")
    console.print(f"  Role: [cyan]{role}[/cyan]")
    console.print(f"  VIP Mode: [cyan]{vip_mode}[/cyan]")
    console.print(f"\n[bold green]✓[/bold green] Updated project: [cyan]{project_file}[/cyan]")


@app.command()
def generate(
    project_file: str = typer.Argument(..., help="Path to project JSON file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """Generate UVM code from a project file."""
    show_banner()
    
    try:
        project = load_project(project_file)
    except FileNotFoundError:
        console.print(f"\n[bold red]Error:[/bold red] Project file not found: {project_file}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] Failed to load project: {e}")
        raise typer.Exit(1)
    
    console.print(f"\n[bold]Generating UVM code for project:[/bold] [cyan]{project.name}[/cyan]\n")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating files...", total=None)
            
            generator = Generator(project)
            output_files = generator.generate_all()
            
            progress.update(task, completed=True)
        
        console.print(f"\n[bold green]✓[/bold green] Generation complete!")
        console.print(f"  Output directory: [cyan]{project.output_dir}[/cyan]")
        console.print(f"  Files generated: [bold]{len(output_files)}[/bold]\n")
        
        if verbose:
            table = Table(title="Generated Files", show_header=True, header_style="bold cyan")
            table.add_column("Type", style="dim")
            table.add_column("Path", style="cyan")
            
            for file_type, file_path in output_files.items():
                table.add_row(file_type, file_path)
            
            console.print(table)
        else:
            console.print("[dim]Use --verbose to see all generated files.[/dim]")
            
    except GenerationError as e:
        console.print(f"\n[bold red]Generation Error:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected Error:[/bold red] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def info(
    project_file: str = typer.Argument(..., help="Path to project JSON file"),
):
    """Display project information."""
    try:
        project = load_project(project_file)
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] Project file not found: {project_file}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to load project: {e}")
        raise typer.Exit(1)
    
    show_banner()
    
    # Project info panel
    info_text = f"""[bold]Name:[/bold] {project.name}
[bold]Output Directory:[/bold] {project.output_dir}
[bold]Simulator:[/bold] {project.simulator}
[bold]Agents:[/bold] {len(project.agents)}
[bold]Protocols:[/bold] {len(project.protocols_used)}"""
    
    console.print(Panel(info_text, title="Project Information", border_style="cyan"))
    
    # Features table
    if project.features:
        console.print("\n[bold]Features:[/bold]")
        features_table = Table(show_header=False, box=None)
        features_table.add_column("Feature", style="cyan")
        features_table.add_column("Status")
        
        for feature, enabled in project.features.items():
            status = "[green]✓ Enabled[/green]" if enabled else "[dim]✗ Disabled[/dim]"
            features_table.add_row(feature, status)
        
        console.print(features_table)
    
    # Agents table
    if project.agents:
        console.print("\n[bold]Agents:[/bold]")
        agents_table = Table(show_header=True, header_style="bold cyan")
        agents_table.add_column("Name", style="bold")
        agents_table.add_column("Protocol")
        agents_table.add_column("Role")
        agents_table.add_column("VIP Mode")
        
        for agent in project.agents:
            plugin = get_protocol(agent.protocol_id)
            protocol_label = plugin.label if plugin else agent.protocol_id
            agents_table.add_row(
                agent.name,
                protocol_label,
                agent.role,
                agent.vip_mode,
            )
        
        console.print(agents_table)
    else:
        console.print("\n[dim]No agents defined yet.[/dim]")


@app.command(name="list-protocols")
def list_protocols():
    """List all available protocol plugins."""
    show_banner()
    
    protocols = get_all_protocols()
    
    if not protocols:
        console.print("\n[yellow]No protocols found.[/yellow]")
        return
    
    console.print(f"\n[bold]Available Protocols:[/bold] {len(protocols)}\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", style="bold")
    table.add_column("Family")
    table.add_column("Label", style="cyan")
    table.add_column("Maturity")
    
    for protocol_id, plugin in sorted(protocols.items()):
        maturity_style = "green" if plugin.maturity == "full" else "yellow"
        table.add_row(
            protocol_id,
            plugin.family,
            plugin.label,
            f"[{maturity_style}]{plugin.maturity}[/{maturity_style}]",
        )
    
    console.print(table)
    console.print("\n[dim]Use these protocol IDs with the add-agent command.[/dim]")


@app.command()
def visualize(
    project_file: str = typer.Argument(..., help="Path to project JSON file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (default: project_name_diagram.png)"),
):
    """Generate a block diagram visualization of the project."""
    try:
        project = load_project(project_file)
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] Project file not found: {project_file}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to load project: {e}")
        raise typer.Exit(1)
    
    if not project.agents:
        console.print("[yellow]Warning:[/yellow] No agents in project. Nothing to visualize.")
        raise typer.Exit(0)
    
    if output is None:
        output = f"{project.name}_diagram.png"
    
    console.print(f"\n[bold]Generating diagram for:[/bold] [cyan]{project.name}[/cyan]")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating visualization...", total=None)
            
            output_path = generate_diagram(project, output)
            
            progress.update(task, completed=True)
        
        console.print(f"\n[bold green]✓[/bold green] Diagram generated: [cyan]{output_path}[/cyan]")
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] Failed to generate diagram: {e}")
        console.print("[dim]Make sure Graphviz is installed on your system.[/dim]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
