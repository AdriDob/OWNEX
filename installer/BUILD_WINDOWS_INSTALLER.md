# Windows Installer Build Instructions

## Prerequisites

1. **NSIS 3.0+**: Download from https://nsis.sourceforge.io/
2. **Windows OS**: NSIS is Windows-only software
3. **PyInstaller Bundle**: Bundle must be built first

## Build PyInstaller Bundle

```bash
# From project root
.venv/bin/python -m PyInstaller OWNEX-Desktop-Alpha.spec
```

Bundle will be at: `dist/OWNEX-Desktop-Alpha/`

## Build NSIS Installer

### Option 1: Using NSIS Command Line

```bash
# From project root (requires NSIS in PATH)
makensis installer/OWNEX-Desktop-Alpha.nsi
```

### Option 2: Using NSIS GUI

1. Open NSIS
2. Load `installer/OWNEX-Desktop-Alpha.nsi`
3. Click "Compile"
4. Installer will be generated as `OWNEX-Desktop-Alpha-Setup.exe`

### Option 3: On Linux (requires Wine)

```bash
# Install Wine and NSIS via Wine
sudo apt install wine nsis

# Build installer
makensis installer/OWNEX-Desktop-Alpha.nsi
```

## Installer Features

- **Installation Directory**: `%LOCALAPPDATA%\Programs\OWNEX\` (user-level, no admin required)
- **Start Menu Shortcut**: Created automatically
- **Desktop Shortcut**: Created automatically
- **Uninstaller**: Clean uninstall via Add/Remove Programs
- **Registry**: User-level registry entries (HKCU)

## Verification

### Test Installation
1. Run `OWNEX-Desktop-Alpha-Setup.exe`
2. Verify installation directory
3. Test Start Menu shortcut
4. Test Desktop shortcut
5. Launch application
6. Verify all 8 sections work
7. Test theme switching

### Test Uninstallation
1. Uninstall via Add/Remove Programs
2. Verify shortcuts removed
3. Verify installation directory removed
4. Verify registry entries cleaned

## Installer Script Details

The NSIS script (`installer/OWNEX-Desktop-Alpha.nsi`) includes:
- User-level installation (no admin required)
- Complete bundle copy (preserves `_internal` structure)
- Registry entries for uninstall
- Start Menu and Desktop shortcuts
- Clean uninstall routine

## Customization

### Change Installation Directory
Edit line 19 in `OWNEX-Desktop-Alpha.nsi`:
```nsis
InstallDir "$LOCALAPPDATA\Programs\${APPNAME}"
```

### Disable Desktop Shortcut
Comment out line 34 in `OWNEX-Desktop-Alpha.nsi`:
```nsis
; CreateShortCut "$DESKTOP\${APPNAME}.lnk" ...
```

### Change Version
Edit lines 9-11 in `OWNEX-Desktop-Alpha.nsi`:
```nsis
!define VERSIONMAJOR 0
!define VERSIONMINOR 1
!define VERSIONBUILD 0
```

## Troubleshooting

### NSIS not found
- Download from https://nsis.sourceforge.io/Download/
- Add to PATH or use full path to makensis

### Bundle not found
- Ensure PyInstaller bundle exists at `dist/OWNEX-Desktop-Alpha/`
- Run PyInstaller build first

### Installer size too large
- The bundle is ~1.2GB due to Python dependencies
- This is expected for PySide6 applications
- Consider using UPX compression in PyInstaller spec

## Linux/Wine Limitations

The current environment is WSL2 Linux without NSIS. To build the installer:
1. Copy project to Windows machine
2. Install NSIS on Windows
3. Run makensis command
4. Copy resulting `.exe` back

Alternatively, use Wine on Linux (less tested).