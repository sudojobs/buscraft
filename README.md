# BusCraft

**Version**: 0.1.0 (Prototype)  
**Type**: Electronic Design Automation (EDA) Tool / Code Generator

BusCraft is a powerful automation tool designed to streamline the creation of **Universal Verification Methodology (UVM)** environments. It takes a high-level Python object model of a system and generates syntactically correct SystemVerilog UVM source code, simulation scripts, and visualization diagrams.

## Quick Start

### Prerequisites
- Python 3.9+
- Graphviz (for diagram generation)

### Installation

```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate the environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Running the Tool

To launch the GUI:
```bash
python -m buscraft.main
```

---

## Core Functionality

BusCraft simplifies the UVM verification process by automating the boilerplate code generation.

- **Input**: High-level Python object model defining bus agents and global parameters.
- **Output**: Complete UVM environment including agents, drivers, monitors, and Makefiles.
- **Interfaces**:
    - **GUI**: PySide6-based desktop application for visual configuration.
    - **CLI**: Command-line interface for batch processing (planned).

## Supported Protocols

The tool features a plugin architecture to support various standard interfaces:

### AMBA Family
- **APB** (Advanced Peripheral Bus)
- **AHB** (Advanced High-performance Bus)
- **AXI** (Advanced eXtensible Interface)
- **CHI** (Coherent Hub Interface)

### Serial Protocols
- **I2C** (Inter-Integrated Circuit)

### Generic
- **Template**: Blank starter for custom implementation

## Configuration

Each agent and interface can be highly customized:
- **Role**: Master, Slave, or Monitor-only.
- **Bus Widths**: Configurable Address and Data widths (e.g., 32, 64, 128 bits).
- **Modes**: Full VIP (Verification IP) or BFM (Bus Functional Model).

## Generated Artifacts

Executing "Generate" produces a complete verification package:
- **Agent Packages**: `*_agent.sv`, `*_driver.sv`, `*_monitor.sv`, etc.
- **Top-Level Environment**: `buscraft_env.sv` (instantiates and connects all agents).
- **Simulation Scripts**: Makefile for Synopsys VCS (extensible).
- **Visualization**: System connectivity diagrams via Graphviz.

## Verification Features

Global verification toggles:
- **Scoreboarding**: Automatic data integrity checking between master and slave.
- **Functional Coverage**: Covergroups for bus states and transitions.
- **Assertions (SVA)**: Built-in protocol rule checks.

## Technical Stack

- **Language**: Python 3.9+
- **GUI Framework**: Qt (PySide6 >= 6.6)
- **Templating**: Jinja2 (for SystemVerilog generation)
- **Rendering**: Graphviz (for block diagrams)
- **OS Support**: Windows, Linux, macOS
