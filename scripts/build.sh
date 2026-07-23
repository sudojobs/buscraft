#!/bin/bash
# Nuitka build script for BusCraft MVP

echo "Compiling BusCraft with Nuitka..."

# Ensure we are in the project root
cd "$(dirname "$0")/.."

# Compile the main entry point
.venv/bin/python -m nuitka \
    --standalone \
    --include-package=buscraft \
    --include-data-dir=src/buscraft/gui/assets=buscraft/gui/assets \
    --include-data-dir=src/buscraft/templates=buscraft/templates \
    --output-dir=build \
    src/buscraft/main.py

echo "Build complete. Output is in the build/main.dist directory."
