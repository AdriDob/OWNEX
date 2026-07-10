@echo off
REM Hermes Agent v1 — Windows WSL Launcher
REM Place this file on your Desktop or pin to taskbar

echo [Hermes] ORION Automation Agent v0.1.0
echo [Hermes] Conectando a WSL Ubuntu...
echo.

wsl -d Ubuntu -- cd ~/projects/Rastro && python run.py --hermes %*

echo.
echo [Hermes] Comando completado. Presione cualquier tecla para cerrar...
pause > nul
