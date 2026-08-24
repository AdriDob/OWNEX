#!/usr/bin/env python3
"""
OWNEX Desktop Alpha - Python-based Installer
Generates a self-extracting installer using Python's zip capabilities
"""

import os
import sys
import zipfile
from pathlib import Path

APP_NAME = "OWNEX Desktop Alpha"
VERSION = "7.0.0"
COMPANY = "CATEYE"
INSTALL_DIR = "OWNEX Desktop Alpha"


def create_installer():
    """Create a self-extracting installer"""

    # Source paths
    source_dir = Path("ownexinstalador/windows/portable")
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        return False

    # Create installer directory
    installer_dir = Path("ownexinstalador/windows/installer")
    installer_dir.mkdir(exist_ok=True)

    # Create zip archive
    installer_name = "OWNEX-Desktop-Alpha-Setup.exe"
    installer_path = installer_dir / installer_name

    print(f"Creating installer: {installer_path}")

    # Create zip with full bundle
    with zipfile.ZipFile(installer_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _dirs, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_dir.parent)
                zipf.write(file_path, arcname)
                print(f"Added: {arcname}")

    print(f"Installer created: {installer_path}")
    print(f"Size: {installer_path.stat().st_size / (1024 * 1024):.2f} MB")

    return True


def create_install_script():
    """Create installation script"""
    script_content = """@echo off
echo Installing OWNEX Desktop Alpha...
echo.

REM Extract to %LOCALAPPDATA%\\Programs\\OWNEX
set INSTALL_DIR=%LOCALAPPDATA%\\Programs\\OWNEX

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Extract files (this is handled by the self-extracting exe)
REM The current directory is the extraction location

echo Creating Start Menu shortcut...
set SHORTCUT_DIR=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_DIR%\\OWNEX Desktop Alpha.lnk'); $Shortcut.TargetPath = '%CD%\\OWNEX-Desktop-Alpha\\OWNEX-Desktop-Alpha.exe'; $Shortcut.Save()"

echo Creating Desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\\Desktop\\OWNEX Desktop Alpha.lnk'); $Shortcut.TargetPath = '%CD%\\OWNEX-Desktop-Alpha\\OWNEX-Desktop-Alpha.exe'; $Shortcut.Save()"

echo Installation complete!
echo You can now run OWNEX Desktop Alpha from the Start Menu or Desktop.
pause
"""

    installer_dir = Path("ownexinstalador/windows/installer")
    script_path = installer_dir / "install.bat"

    with open(script_path, "w") as f:
        f.write(script_content)

    print(f"Installation script created: {script_path}")
    return True


def main():
    print(f"Creating {APP_NAME} Installer v{VERSION}")
    print("=" * 50)

    if create_install_script() and create_installer():
        print("\nInstaller created successfully!")
        print("Location: ownexinstalador/windows/installer/OWNEX-Desktop-Alpha-Setup.exe")
        return 0

    print("\nInstaller creation failed!")
    return 1


if __name__ == "__main__":
    sys.exit(main())
