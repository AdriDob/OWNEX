# Installer Build Instructions

## Requirements
- Windows Server / Desktop
- NSIS (https://nsis.sourceforge.io)
- Inno Setup (recommended for newer features)

## Build Steps

### Windows
1. Install NSIS
2. Ensure makensis is in PATH (`makensis installer/orion.nsi`)
3. If makensis not available, use Inno Setup

### Linux/macOS
1. Install pyinstaller via pip
2. Build with: `python run.py`  # This runs PyInstaller
3. Build Linux: `bash scripts/build_linux.sh`

## Branch Notes
- installer/ directory contains current Windows installer files
- android/app/ contains Capacitor Android app
system-requirements.android.yml shows dependencies
script build and scripts contain build instructions
