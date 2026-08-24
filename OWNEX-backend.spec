# -*- mode: python ; coding: utf-8 -*-
# ruff: noqa
#
# OWNEX Backend — PyInstaller build spec for standalone FastAPI sidecar.
# Entrypoint: api/main.py
# Output: dist/OWNEX-backend/OWNEX-backend.exe (Windows) or dist/OWNEX-backend/OWNEX-backend (Linux)
#
# Usage:
#   pyinstaller OWNEX-backend.spec -y
#
# CLI args:
#   --port <port>          (default: 8000)
#   --data-dir <path>     (default: %LOCALAPPDATA%\OWNEX on Windows, ~/.ownex on Linux)
#   --log-level <level>   (default: INFO)

import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.getcwd()).resolve()
IS_WINDOWS = sys.platform.startswith("win")
ICON_PATH = str(PROJECT_ROOT / "installer" / "icons" / "cateye.ico") if IS_WINDOWS else None

# ── Collect all router modules (automatically discovered) ──────────────
ROUTERS_DIR = PROJECT_ROOT / "api" / "routers"
router_modules = []
if ROUTERS_DIR.is_dir():
    for f in sorted(ROUTERS_DIR.iterdir()):
        if f.suffix == ".py" and f.stem != "__init__":
            router_modules.append(f"api.routers.{f.stem}")

# ── Collect all cores subpackages for hidden imports ──────────
CORE_DIR = PROJECT_ROOT / "cores"
core_packages = []
if CORE_DIR.is_dir():
    for d in sorted(CORE_DIR.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.stem != "__pycache__":
            core_packages.append(f"cores.{d.stem}")

# ── Hidden imports ────────────────────────────────────────────────────
HIDDEN_IMPORTS = [
    # API layer
    'api', 'api.main', *router_modules,
    # Database
    'database', 'database.db', 'database.models',
    # Core engines
    'cores', 'cores.env', 'cores.env.config',
    'cores.platform', 'cores.platform.system',
    'cores.log_config', 'cores.observability',
    *core_packages,
    # Web server
    'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets.auto',
    # HTTP / networking
    'httpx', 'sniffio', 'h11', 'anyio',
    # Config / serialization
    'dotenv', 'pydantic',
    'pydantic_settings',
    # Database ORM
    'sqlalchemy',
    # Prom metrics
    'prometheus_client',
    # Async runtime
    'asyncio',
]

# ── Data files ────────────────────────────────────────────────────────
DATAS = [
    (str(PROJECT_ROOT / "VERSION"), '.'),
]

# ── Binary files ───────────────────────────────────────────────────────
BINARIES = []

# ── Excludes ───────────────────────────────────────────────────────────
EXCLUDES = [
    'matplotlib', 'scipy', 'notebook', 'jupyter',
    'PyQt5', 'PyQt6', 'PySide2', 'PySide6',  # No Qt needed for backend
    'tkinter',  # No GUI
]

UPX_AVAILABLE = os.getenv("UPX_PATH") is not None or bool(shutil.which("upx"))

a = Analysis(
    ['api/main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=BINARIES,
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OWNEX-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console needed for logging/debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=UPX_AVAILABLE,
    upx_exclude=[],
    name='OWNEX-backend',
)
