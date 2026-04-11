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


from rich.prompt import Prompt
from huggingface_hub import hf_hub_download
import shlex
import os

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

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

def get_llm():
    if not Llama:
        return None
    try:
        model_path = hf_hub_download(
            repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
            filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf"
        )
        # FORCE strict CPU settings to avoid macOS Rosetta metal deadlocks
        return Llama(
            model_path=model_path, 
            verbose=False, 
            n_ctx=2048,
            n_gpu_layers=0,  # Zero GPU layers
            n_threads=4,     # Limit threads
            seed=42          # Deterministic
        )
    except Exception as e:
        console.print(f"[yellow]Failed to load AI model: {e}[/yellow]")
        return None

def interactive_mode():
    """Run BusCraft CLI in interactive mode with AI support."""
    show_banner()
    console.print("\n[bold]Welcome to BusCraft AI Terminal![/bold]")
    
    llm = None
    with console.status("[dim]Initializing AI backend (CPU fallback logic)...[/dim]"):
        llm = get_llm()
        if llm:
            console.print("[green]✓ AI Backend ready. Try asking a question![/green]")
        else:
            console.print("[yellow]⚠ AI Backend not available. Operating as standard CLI.[/yellow]")

    console.print("Type a CLI command (e.g., 'new', 'info') or ask the AI. Type 'exit' to leave.\n")
    
    messages = [
        {
            "role": "system", 
            "content": (
                "You are BusCraft AI, an autonomous UVM verification expert agent. "
                "You can control the terminal and read/write files to accomplish complex tasks.\\n"
                "CRITICAL INSTRUCTIONS:\\n"
                "1. Specialize in UVM environments and IEEE 1800.2 guidelines.\\n"
                "2. NO conversational filler. Output only technical explanations and tool calls.\\n"
                "3. AUTONOMOUS TOOLS: You have access to the following XML tools. To use one, output the exact tag. You will receive the tool output in the next message.\\n"
                "   - Run terminal command: <bash> command here </bash>\\n"
                "   - Read a file's content: <read> filepath here </read>\\n"
                "   - Auto-write a file: Output a code block starting with // File: <filename.sv>\\n"
                "4. You must ONLY use ONE <bash> or <read> tool per message. You will automatically receive the execution result in the next message to continue your thought process.\\n"
            )
        }
    ]
    
    # Extract CLI commands correctly by checking the function name if explicitly registered name is missing
    cli_commands = []
    for cmd in app.registered_commands:
        if cmd.name:
            cli_commands.append(cmd.name)
        elif cmd.callback:
            # Typer defaults to using the function name with underscores replaced by hyphens
            cli_commands.append(cmd.callback.__name__.replace("_", "-"))
            
    cli_commands += ["help", "--help"]
    while True:
        try:
            command_str = Prompt.ask("[bold cyan]buscraft[/bold cyan] ")
            command_str = command_str.strip()
            
            if not command_str:
                continue
                
            if command_str.lower() in ("exit", "quit"):
                console.print("[dim]Exiting interactive mode...[/dim]")
                break
                
            args = shlex.split(command_str)
            if not args:
                continue
                
            cmd_name = args[0].lower()
            if cmd_name == "help":
                args = ["--help"]
                cmd_name = "--help"
            
            # Interactive file picker for 'spec' command when no arguments given
            if cmd_name == "spec" and len(args) == 1:
                console.print("\n[bold cyan]📄 Spec-to-Code Generator[/bold cyan]")
                console.print("[dim]Drag a file from Finder into this terminal, or type the path:[/dim]\n")
                
                spec_path = Prompt.ask("[bold]  Spec file path[/bold]").strip()
                # macOS drag-and-drop wraps paths in quotes and escapes spaces
                spec_path = spec_path.strip("'\"").replace("\\ ", " ")
                
                if not spec_path:
                    console.print("[yellow]Cancelled.[/yellow]")
                    continue
                
                import os
                if not os.path.exists(spec_path):
                    console.print(f"[bold red]Error:[/bold red] File not found: {spec_path}")
                    continue
                
                proj_name = Prompt.ask("[bold]  Project name[/bold] [dim](Enter to auto-detect)[/dim]", default="").strip()
                
                # File selection menu
                from buscraft.core.generator import FILE_CATEGORIES
                console.print("\n[bold]  Select files to generate:[/bold]")
                cat_list = list(FILE_CATEGORIES.items())
                for i, (key, desc) in enumerate(cat_list, 1):
                    console.print(f"    [cyan]{i:2d}[/cyan]. {key:12s} — [dim]{desc}[/dim]")
                console.print(f"    [green] A[/green]. [bold]All files[/bold] [dim](full simulation-ready testbench)[/dim]")
                console.print(f"    [yellow] D[/yellow]. [bold]Default[/bold]  [dim](agent + env + sim scripts)[/dim]")
                
                selection = Prompt.ask("\n[bold]  Enter choice[/bold] [dim](numbers separated by commas, A for all, D for default)[/dim]", default="A").strip()
                
                selected = set()
                if selection.upper() == "A":
                    selected = set(FILE_CATEGORIES.keys())
                elif selection.upper() == "D":
                    from buscraft.core.generator import MINIMAL_FILES
                    selected = MINIMAL_FILES
                else:
                    for part in selection.split(","):
                        part = part.strip()
                        if part.isdigit():
                            idx = int(part) - 1
                            if 0 <= idx < len(cat_list):
                                selected.add(cat_list[idx][0])
                
                gen_now = Prompt.ask("[bold]  Generate UVM code now?[/bold] [dim](y/n)[/dim]", default="y").strip().lower()
                
                args = ["spec", spec_path]
                if proj_name:
                    args += ["--name", proj_name]
                if gen_now in ("y", "yes"):
                    args += ["--generate"]
                # Store selection for the spec command to pick up
                os.environ["BUSCRAFT_GEN_FILES"] = ",".join(selected)
                
                console.print()
            
            if cmd_name in cli_commands or cmd_name.startswith("-"):
                import sys
                old_argv = sys.argv.copy()
                try:
                    sys.argv = ["buscraftcli"] + args
                    app()
                except SystemExit:
                    pass
                except Exception as e:
                    console.print(f"[bold red]CLI Error:[/bold red] {e}")
                finally:
                    sys.argv = old_argv
            else:
                # LLM execution
                if llm:
                    messages.append({"role": "user", "content": command_str})
                    console.print()
                    
                    import re
                    import os
                    import subprocess
                    
                    import random
                    craft_messages = [
                        "⚙️  Architecting verification components...",
                        "🔧 Forging UVM infrastructure...",
                        "🏗️  Constructing testbench scaffolding...",
                        "✨ Weaving SystemVerilog magic...",
                        "🧬 Synthesizing verification logic...",
                        "🔩 Assembling protocol handlers...",
                        "🛠️  Engineering signal interfaces...",
                        "⚡ Generating IEEE 1800.2 compliant code...",
                        "🧪 Brewing verification sequences...",
                        "🚀 Crafting production-grade UVM modules...",
                    ]
                    
                    while True:
                        response_text = ""
                        in_code_block = False
                        code_block_spinner = None
                        
                        try:
                            stream = llm.create_chat_completion(
                                messages=messages,
                                stream=True,
                                max_tokens=2048,
                                stop=["</bash>", "</read>"]
                            )
                            for chunk in stream:
                                delta = chunk["choices"][0]["delta"].get("content", "")
                                if delta:
                                    response_text += delta
                                    
                                    # Detect code block boundaries
                                    if "```" in delta and not in_code_block:
                                        in_code_block = True
                                        creative_msg = random.choice(craft_messages)
                                        console.print(f"\n[bold magenta]{creative_msg}[/bold magenta]")
                                        continue
                                    elif "```" in delta and in_code_block:
                                        in_code_block = False
                                        console.print("[dim]  ...done[/dim]")
                                        continue
                                    
                                    # Only print non-code content (explanations, tool tags, etc.)
                                    if not in_code_block:
                                        console.print(delta, end="")
                            
                            console.print("\n")
                            
                            # If model stopped due to a tool tag, reconstruct the closing tag so we can parse it
                            if "<bash>" in response_text and "</bash>" not in response_text:
                                response_text += "</bash>"
                            if "<read>" in response_text and "</read>" not in response_text:
                                response_text += "</read>"
                        except KeyboardInterrupt:
                            console.print("\n[yellow]Generation stopped by user (Ctrl+C).[/yellow]")
                            break # Break the agentic loop on manual interrupt
                        except Exception as e:
                            console.print(f"\n[bold red]AI Error:[/bold red] {e}\n")
                            break
                        
                        messages.append({"role": "assistant", "content": response_text})

                        # Process auto-file saves
                        pattern = r"//\s*File:\s*([^\n]+)\s*\n.*?(```[a-zA-Z0-9_\-]*\s*\n(.*?)\n```)"
                        matches = re.finditer(pattern, response_text, re.DOTALL)
                        saved_files = 0
                        for match in matches:
                            filename = match.group(1).strip()
                            code_content = match.group(3).strip()
                            try:
                                os.makedirs(os.path.dirname(filename), exist_ok=True) if os.path.dirname(filename) else None
                                with open(filename, "w") as f:
                                    f.write(code_content + "\n")
                                console.print(f"[bold green]✓ Saved file:[/bold green] [cyan]{filename}[/cyan] (in {os.getcwd()})")
                                saved_files += 1
                            except Exception as e:
                                console.print(f"[bold red]✗ Failed to save {filename}:[/bold red] {e}")
                        
                        if saved_files > 0:
                            console.print(f"[dim]Auto-saved {saved_files} file(s) to current directory.[/dim]\n")
                            
                        # Process Tool Calls
                        bash_match = re.search(r"<bash>(.*?)</bash>", response_text, re.DOTALL)
                        read_match = re.search(r"<read>(.*?)</read>", response_text, re.DOTALL)
                        
                        if bash_match:
                            cmd = bash_match.group(1).strip()
                            console.print(f"[bold yellow]⚡ Executing Bash:[/bold yellow] {cmd}")
                            try:
                                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                                output = (result.stdout + result.stderr).strip()
                                if not output:
                                    output = "Command executed successfully with no output."
                            except Exception as e:
                                output = f"Failed to execute command: {e}"
                            
                            messages.append({"role": "user", "content": f"Tool Execution Result for <bash>{cmd}</bash>:\n{output}"})
                            console.print(f"[dim]Output fed back to AI...[/dim]\n")
                            continue # Continue the loop so the AI can read the output
                            
                        elif read_match:
                            filepath = read_match.group(1).strip()
                            console.print(f"[bold cyan]📖 Reading File:[/bold cyan] {filepath}")
                            try:
                                with open(filepath, "r") as f:
                                    output = f.read()
                            except Exception as e:
                                output = f"Failed to read file: {e}"
                            
                            messages.append({"role": "user", "content": f"Tool Execution Result for <read>{filepath}</read>:\n{output}"})
                            console.print(f"[dim]File content fed back to AI...[/dim]\n")
                            continue # Continue the loop so the AI can read the output
                            
                        # If no tool calls were made, break the autonomous loop
                        break
                else:
                    console.print(f"[red]Command not found:[/red] {cmd_name} (AI fallback disabled)")
                
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting interactive mode...[/dim]")
            break

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
        interactive_mode()


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
    no_scoreboard: bool = typer.Option(False, "--no-scoreboard", help="Disable generating UVM Scoreboard"),
    no_coverage: bool = typer.Option(False, "--no-coverage", help="Disable generating UVM Coverage"),
    no_assertions: bool = typer.Option(False, "--no-assertions", help="Disable generating SVA Assertions"),
    no_sim_scripts: bool = typer.Option(False, "--no-scripts", help="Disable generating Makefiles/run scripts"),
):
    """Create a new BusCraft project."""
    show_banner()
    
    project = Project(
        name=name,
        output_dir=output_dir,
        simulator=simulator,
    )
    
    # Apply feature toggles (default is true in core/models.py, so we only need to disable them if checked)
    if no_scoreboard: project.features["scoreboard_enable"] = False
    if no_coverage: project.features["coverage_enable"] = False
    if no_assertions: project.features["assertions_enable"] = False
    if no_sim_scripts: project.features["sim_scripts_enable"] = False
    
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
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory for diagrams"),
    diagram_type: str = typer.Option("all", "--type", "-t", help="Diagram type: block, sequence, state, all"),
    fmt: str = typer.Option("png", "--format", "-f", help="Output format: png, svg, pdf"),
):
    """Generate architecture diagrams (Graphviz + PlantUML) and GTKWave config."""
    from buscraft.core.visualizer import (
        generate_diagram, generate_puml_sequence, generate_puml_state,
        generate_gtkwave_savefile, render_puml,
    )
    
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
    
    out_dir = output or f"{project.name}_diagrams"
    import os
    os.makedirs(out_dir, exist_ok=True)
    
    console.print(f"\n[bold]Generating diagrams for:[/bold] [cyan]{project.name}[/cyan]\n")
    
    generated = []
    
    try:
        # --- Graphviz Block Diagram ---
        if diagram_type in ("block", "all"):
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                progress.add_task("🏗️  Generating Graphviz block diagram...", total=None)
                block_path = generate_diagram(project, f"{out_dir}/{project.name}_architecture", fmt=fmt)
                generated.append(("Block diagram (Graphviz)", block_path))
        
        # --- PlantUML Sequence Diagram ---
        if diagram_type in ("sequence", "all"):
            console.print("  📝 Generating PlantUML sequence diagram...")
            seq_path = generate_puml_sequence(project, f"{out_dir}/{project.name}_sequence")
            generated.append(("Sequence diagram (.puml)", seq_path))
            
            # Try to render to image
            rendered = render_puml(seq_path, fmt=fmt)
            if rendered:
                generated.append(("Sequence diagram (rendered)", rendered))
        
        # --- PlantUML State Diagram ---
        if diagram_type in ("state", "all"):
            console.print("  📝 Generating PlantUML state diagram...")
            state_path = generate_puml_state(project, f"{out_dir}/{project.name}_state")
            generated.append(("State diagram (.puml)", state_path))
            
            rendered = render_puml(state_path, fmt=fmt)
            if rendered:
                generated.append(("State diagram (rendered)", rendered))
        
        # --- GTKWave Save File ---
        if diagram_type == "all":
            console.print("  📊 Generating GTKWave signal config...")
            gtkw_path = generate_gtkwave_savefile(project, f"{out_dir}/{project.name}_waves")
            generated.append(("GTKWave config (.gtkw)", gtkw_path))
        
        # --- Summary ---
        console.print(f"\n[bold green]✓ Generated {len(generated)} files:[/bold green]\n")
        for label, path in generated:
            console.print(f"  [green]✓[/green] [dim]{label}:[/dim] [cyan]{path}[/cyan]")
        
        # Auto-open the block diagram
        block_files = [p for l, p in generated if "Block" in l]
        if block_files:
            import sys
            import subprocess
            if sys.platform == "darwin":
                subprocess.run(["open", block_files[0]])
            elif sys.platform == "win32":
                os.startfile(block_files[0])
            else:
                subprocess.run(["xdg-open", block_files[0]])
        
        if any(".puml" in p for _, p in generated):
            console.print(f"\n[dim]Render .puml files at: https://www.plantuml.com/plantuml/uml/[/dim]")
            console.print(f"[dim]Or install PlantUML: brew install plantuml[/dim]")
            
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] Failed to generate diagrams: {e}")
        console.print("[dim]Make sure Graphviz is installed on your system.[/dim]")
        raise typer.Exit(1)


@app.command()
def config(
    project_file: str = typer.Argument(..., help="Path to project JSON file"),
    set_simulator: Optional[str] = typer.Option(None, "--sim", help="Set the simulator (vcs, questa, xcelium, verilator)"),
    set_output: Optional[str] = typer.Option(None, "--out", help="Change output directory"),
):
    """Modify existing project configuration."""
    try:
        project = load_project(project_file)
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] Project file not found: {project_file}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to load project: {e}")
        raise typer.Exit(1)
    
    modified = False
    
    if set_simulator:
        project.simulator = set_simulator
        console.print(f"[green]✓[/green] Changed simulator to: [cyan]{set_simulator}[/cyan]")
        modified = True
        
    if set_output:
        project.output_dir = set_output
        console.print(f"[green]✓[/green] Changed output directory to: [cyan]{set_output}[/cyan]")
        modified = True
        
    if modified:
        save_project(project, project_file)
        console.print(f"\n[bold]Saved updates to project file.[/bold]")
    else:
        console.print("[dim]No configuration changes requested.[/dim]")


@app.command()
def wave(
    project_file: str = typer.Argument(..., help="Path to project JSON file"),
    waveform_file: Optional[str] = typer.Option(None, "--file", "-f", help="Specific VCD/FST file to open"),
):
    """Launch GTKWave to view simulation waveforms."""
    import shutil
    import subprocess
    import glob
    import os
    
    # 1. Check if GTKWave is installed
    if not shutil.which("gtkwave"):
        console.print("[bold red]Error:[/bold red] GTKWave is not installed or not in PATH.")
        if sys.platform == "darwin":
            console.print("[dim]You can install it on macOS using: brew install --cask gtkwave[/dim]")
        elif sys.platform == "linux":
            console.print("[dim]You can install it on Linux using: sudo apt install gtkwave[/dim]")
        raise typer.Exit(1)

    try:
        project = load_project(project_file)
    except Exception as e:
        console.print(f"[bold red]Error loading project:[/bold red] {e}")
        raise typer.Exit(1)
        
    target_file = None

    # 2. If no file provided, auto-find the latest one in the output dir
    if waveform_file:
        target_file = waveform_file
    else:
        search_dir = Path(project.output_dir)
        if not search_dir.exists():
            console.print(f"[yellow]Warning:[/yellow] Output directory {search_dir} does not exist yet.")
            raise typer.Exit(1)
            
        # Look for .vcd or .fst files
        vcd_files = list(search_dir.rglob("*.vcd"))
        fst_files = list(search_dir.rglob("*.fst"))
        all_waves = vcd_files + fst_files
        
        if not all_waves:
            console.print(f"[yellow]No waveform files (.vcd or .fst) found in {search_dir}[/yellow]")
            console.print("[dim]Make sure you have run a simulation that dumps waveforms.[/dim]")
            raise typer.Exit(1)
            
        # Get the most recently modified file
        target_file = str(max(all_waves, key=os.path.getmtime))
        console.print(f"[dim]Auto-selected latest waveform:[/dim] {target_file}")

    if not os.path.exists(target_file):
        console.print(f"[bold red]Error:[/bold red] File not found: {target_file}")
        raise typer.Exit(1)
        
    # 3. Launch GTKWave asynchronously
    console.print(f"[bold cyan]Launching GTKWave...[/bold cyan]")
    try:
        # We use Popen so we do not block the terminal
        subprocess.Popen(
            ["gtkwave", target_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        console.print(f"[bold red]Failed to launch GTKWave:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def spec(
    spec_file: str = typer.Argument(..., help="Path to IP spec document (.pdf, .md, .txt)"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Project name (auto-detected from spec if not given)"),
    output_dir: str = typer.Option("./buscraft_out", "--output", "-o", help="Output directory"),
    simulator: str = typer.Option("vcs", "--simulator", "-s", help="Target simulator"),
    save_to: Optional[str] = typer.Option(None, "--save", help="Save generated project JSON to file"),
    generate_code: bool = typer.Option(False, "--generate", "-g", help="Immediately generate UVM code after analysis"),
    deep: bool = typer.Option(False, "--deep", "-d", help="Use AI-powered deep analysis (slower but handles unknown protocols)"),
):
    """Analyze an IP spec sheet and auto-generate a complete UVM project."""
    from buscraft.core.spec_parser import parse_spec, chunk_text
    from buscraft.core.spec_analyzer import analyze_spec
    from buscraft.core.spec_to_project import spec_to_project, spec_summary
    from buscraft.core.project_io import save_project
    from buscraft.core.generator import Generator
    
    show_banner()
    
    # --- Stage 1: Ingest the spec ---
    console.print(f"\n[bold cyan]📄 Reading specification:[/bold cyan] {spec_file}")
    
    try:
        raw_text = parse_spec(spec_file)
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] File not found: {spec_file}")
        raise typer.Exit(1)
    except ImportError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print("[dim]Run: pip install pymupdf[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to read spec: {e}")
        raise typer.Exit(1)
    
    console.print(f"[green]✓[/green] Extracted {len(raw_text):,} characters")
    
    # --- Stage 2: Analysis ---
    analysis_messages = [
        "🔬 Scanning for signal definitions...",
        "🧬 Decoding protocol handshake patterns...",
        "📐 Mapping register address space...",
        "⚡ Extracting timing constraints...",
    ]
    msg_idx = [0]
    
    def on_progress(stage: str, current: int, total: int):
        idx = msg_idx[0] % len(analysis_messages)
        console.print(f"  [magenta]{analysis_messages[idx]}[/magenta] [dim]({stage})[/dim]")
        msg_idx[0] += 1
    
    if deep:
        console.print(f"\n[bold cyan]🧠 Deep AI-powered analysis...[/bold cyan] [dim](this may take a while)[/dim]")
        llm = get_llm()
        if not llm:
            console.print("[bold red]Error:[/bold red] AI backend not available for deep analysis.")
            console.print("[dim]Run 'buscraftcli install' or try without --deep[/dim]")
            raise typer.Exit(1)
    else:
        console.print(f"\n[bold cyan]⚡ Fast pattern-matching analysis...[/bold cyan]")
        llm = None
    
    try:
        spec_model = analyze_spec(raw_text, llm=llm, on_progress=on_progress, deep=deep)
    except Exception as e:
        console.print(f"\n[bold red]Analysis Error:[/bold red] {e}")
        raise typer.Exit(1)
    
    # --- Stage 3: Show results ---
    console.print(f"\n[bold green]✓ Specification analysis complete![/bold green]\n")
    
    summary = spec_summary(spec_model)
    from rich.panel import Panel
    console.print(Panel(summary, title="[bold]Extracted Spec Summary[/bold]", border_style="cyan"))
    
    # --- Stage 4: Convert to project ---
    console.print(f"\n[bold cyan]🏗️  Assembling BusCraft project...[/bold cyan]")
    
    project = spec_to_project(
        spec_model,
        project_name=name,
        output_dir=output_dir,
        simulator=simulator,
    )
    
    console.print(f"[green]✓[/green] Project: [bold]{project.name}[/bold]")
    console.print(f"  Protocol: [cyan]{project.protocols_used[0] if project.protocols_used else 'unknown'}[/cyan]")
    console.print(f"  Agents:   [cyan]{len(project.agents)}[/cyan]")
    console.print(f"  Simulator: [cyan]{project.simulator}[/cyan]")
    
    # --- Save project JSON ---
    if save_to:
        save_project(project, save_to)
        console.print(f"\n[bold green]✓[/bold green] Saved project to: [cyan]{save_to}[/cyan]")
    else:
        # Auto-save with a default name
        default_save = f"{project.name}_spec.json"
        save_project(project, default_save)
        console.print(f"\n[bold green]✓[/bold green] Auto-saved project to: [cyan]{default_save}[/cyan]")
        save_to = default_save
    
    # --- Optional: Generate code immediately ---
    if generate_code:
        console.print(f"\n[bold cyan]🚀 Generating UVM code...[/bold cyan]")
        
        # Read file selection from interactive wizard (or default to all)
        import os
        gen_files_env = os.environ.pop("BUSCRAFT_GEN_FILES", "")
        if gen_files_env:
            selected_files = set(gen_files_env.split(","))
        else:
            from buscraft.core.generator import FULL_FILES
            selected_files = FULL_FILES
        
        try:
            gen = Generator(project)
            output_files = gen.generate_all(selected_files=selected_files)
            console.print(f"\n[bold green]✓[/bold green] Generated {len(output_files)} files in [cyan]{output_dir}[/cyan]\n")
            for file_type, file_path in output_files.items():
                console.print(f"  [green]✓[/green] [dim]{file_type}:[/dim] {file_path}")
        except Exception as e:
            console.print(f"[bold red]Generation Error:[/bold red] {e}")
            console.print(f"[dim]You can retry with: buscraftcli generate {save_to} --verbose[/dim]")
    else:
        console.print(f"\n[dim]To generate UVM code, run:[/dim]")
        console.print(f"  [cyan]buscraftcli generate {save_to} --verbose[/cyan]")


@app.command()
def install():
    """Install all necessary dependencies and tools for BusCraft (Mac/Linux)."""
    import shutil
    import subprocess
    import sys
    from huggingface_hub import hf_hub_download
    
    console.print("[bold cyan]Starting BusCraft Installation & Verification...[/bold cyan]")
    
    # 1. Graphviz
    console.print("\n[bold]1. Checking Graphviz (for block diagram generation)...[/bold]")
    if shutil.which("dot"):
        console.print("[green]✓ Graphviz is already installed.[/green]")
    else:
        if sys.platform == "darwin":
            if shutil.which("brew"):
                console.print("[yellow]Graphviz not found. Installing via Homebrew...[/yellow]")
                subprocess.run(["brew", "install", "graphviz"])
                console.print("[green]✓ Graphviz installed successfully.[/green]")
            else:
                console.print("[red]✗ Homebrew not found. Please install Graphviz manually.[/red]")
        elif sys.platform == "linux":
            console.print("[yellow]Graphviz not found. Please run: sudo apt-get install graphviz[/yellow]")
        else:
            console.print("[red]✗ Graphviz not found. Please install it manually for your OS.[/red]")
            
    # 2. GTKWave
    console.print("\n[bold]2. Checking GTKWave (for waveform viewing)...[/bold]")
    if shutil.which("gtkwave"):
        console.print("[green]✓ GTKWave is already installed.[/green]")
    else:
        if sys.platform == "darwin":
            if shutil.which("brew"):
                console.print("[yellow]GTKWave not found. Installing via Homebrew...[/yellow]")
                subprocess.run(["brew", "install", "--cask", "gtkwave"])
                console.print("[green]✓ GTKWave installed successfully.[/green]")
            else:
                console.print("[red]✗ Homebrew not found. Please install GTKWave manually.[/red]")
        elif sys.platform == "linux":
            console.print("[yellow]GTKWave not found. Please run: sudo apt-get install gtkwave[/yellow]")
        else:
            console.print("[red]✗ GTKWave not found. Please install it manually for your OS.[/red]")
            
    # 3. Local AI Model
    console.print("\n[bold]3. Verifying Local AI Model (Qwen Coder 7B)...[/bold]")
    try:
        console.print("[dim]Checking model cache or pulling from HuggingFace (this is a ~4GB file if not cached)[/dim]")
        # hf_hub_download automatically handles caching and progress bars
        model_path = hf_hub_download(
            repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
            filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf"
        )
        console.print(f"[green]✓ AI Model verified and cached at:[/green] [dim]{model_path}[/dim]")
    except Exception as e:
        console.print(f"[red]✗ Failed to download/verify AI model: {e}[/red]")
        
    console.print("\n[bold green]BusCraft setup complete![/bold green]")
    console.print("[dim]You can now use the 'buscraft' or 'buscraftcli' commands anywhere on your system.[/dim]")


if __name__ == "__main__":
    app()
