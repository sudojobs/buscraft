@echo off
setlocal

cd /d %~dp0

python -m pip install --upgrade pip
pip install -r ..\..\requirements.txt

pyinstaller ^
  --name buscraft ^
  --noconfirm ^
  --onedir ^
  --windowed ^
  --icon "..\..\src\buscraft\assets\icons\buscraft_icon.ico" ^
  --add-data "..\..\src\buscraft\templates;buscraft/templates" ^
  --add-data "..\..\src\buscraft\plugins;buscraft/plugins" ^
  --add-data "..\..\src\buscraft\assets;buscraft/assets" ^
  "..\..\src\buscraft\main.py"

endlocal
