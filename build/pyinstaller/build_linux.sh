#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

python3 -m pip install --upgrade pip
pip3 install -r ../../requirements.txt

pyinstaller \
  --name buscraft \
  --noconfirm \
  --onedir \
  --windowed \
  --icon ../../src/buscraft/assets/icons/buscraft_icon.png \
  --add-data "../../src/buscraft/templates:buscraft/templates" \
  --add-data "../../src/buscraft/plugins:buscraft/plugins" \
  --add-data "../../src/buscraft/assets:buscraft/assets" \
  ../../src/buscraft/main.py
