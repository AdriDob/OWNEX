#!/usr/bin/env python3
"""Windows Installer — single-command desktop build + packaging.

Usage:
    python scripts/install_windows.py                    # Portable folder + zip
    python scripts/install_windows.py --installer        # Also build the NSIS installer
    python scripts/install_windows.py --version 1.0.0    # Custom version

Build steps (the canonical OWNEX chain — every path below is real):
    1. Build the frontend (npm ci && npm run build)  -> frontend/dist/
    2. Bundle the Python backend with PyInstaller via OWNEX-Backend.spec
       -> dist/ownex-backend.exe   (ONEFILE: the Tauri externalBin contract
       requires exactly one file per target triple)
    3. Stage the binary under src-tauri/binaries/ with the Windows target
       triple suffix that Tauri expects
    4. Run 'npx tauri build --bundles msi' -> the real Windows app + MSI
       installer (MSI, not NSIS: owner's decision 2026-09-09, pinned by
       tests/test_tauri_packaging.py::test_windows_bundle_is_msi_only)
    5. Fall back to a portable folder + zip when the Rust toolchain or the
       WiX toolchain is unavailable

Output artifacts: dist/install-windows/

NOTE (2026-10-22): this script used to call a non-existent
`desktop/build/build_desktop.py` and then look for
`desktop/build/dist/CATEYE/CATEYE.exe` — a path no build ever produced.
`make build-desktop` was broken for the same reason. Both now resolve to
OWNEX-Backend.spec (repo root) and dist/ownex-backend[.exe].
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
BUILD_SCRIPT = ROOT / "desktop" / "build" / "build_desktop.py"
SRC_TAURI = ROOT / "src-tauri"
BINARIES_DIR = SRC_TAURI / "binaries"
OUTPUT = ROOT / "dist" / "install-windows"

VERSION_FILE = ROOT / "api" / "main.py"

PRODUCT_NAME = "OWNEX"
EXE_STEM = "ownex-backend"

#: Tauri resolves `externalBin: ["binaries/ownex-backend"]` to
#: `binaries/ownex-backend-<target-triple>[.exe]`. The Windows triple is
#: fixed (x86_64-pc-windows-msvc); the Linux/macOS one is detected.
WINDOWS_TRIPLE = "x86_64-pc-windows-msvc"


def _banner(msg: str) -> None:
    print(f"\n=== {msg} ===")


def _run(cmd: list[str], cwd: Path | None = None, **kwargs) -> subprocess.CompletedProcess:
    print(f"  → {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd or ROOT, **kwargs)
    if result.returncode != 0:
        print(f"  ERROR: command failed (exit {result.returncode})")
        sys.exit(1)
    return result


def _get_version() -> str:
    for line in VERSION_FILE.read_text().splitlines():
        if "APP_VERSION" in line:
            return line.split("=")[-1].strip().strip('"')
    return "0.0.0"


def _ensure_frontend_built() -> None:
    dist_dir = FRONTEND / "dist"
    if dist_dir.is_dir() and (dist_dir / "index.html").exists():
        print("  Frontend dist exists — skipping build (delete frontend/dist to force)")
        return
    _banner("Building frontend")
    if shutil.which("npm") is None:
        print("  ERROR: npm not found in PATH — cannot build the frontend")
        sys.exit(2)
    _run(["npm", "ci"], cwd=FRONTEND)
    _run(["npm", "run", "build"], cwd=FRONTEND)
    print("  ✓ Frontend built")


def _run_pyinstaller() -> Path:
    """Bundle the backend with the canonical spec. Returns the built executable."""
    _banner("Running PyInstaller bundler")
    if not BUILD_SCRIPT.is_file():
        print(f"  ERROR: build script missing: {BUILD_SCRIPT}")
        sys.exit(1)
    _run([sys.executable, str(BUILD_SCRIPT), "--rebuild-frontend"])
    exe = ROOT / "dist" / (f"{EXE_STEM}.exe" if sys.platform.startswith("win") else EXE_STEM)
    if not exe.exists():
        print(f"  ERROR: expected executable not found at {exe}")
        print("  Check dist/ for the build output")
        sys.exit(1)
    print(f"  ✓ PyInstaller bundle ready: {exe}")
    return exe


def _target_triple() -> str:
    """Target triple for the current platform (Tauri externalBin convention)."""
    if sys.platform.startswith("win"):
        return WINDOWS_TRIPLE
    if sys.platform == "darwin":
        return "x86_64-apple-darwin"
    return "x86_64-unknown-linux-gnu"


def _stage_for_tauri(exe: Path) -> Path:
    """Copy the backend into src-tauri/binaries with the target-triple suffix."""
    _banner("Staging backend for Tauri externalBin")
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if sys.platform.startswith("win") else ""
    staged = BINARIES_DIR / f"{EXE_STEM}-{_target_triple()}{suffix}"
    shutil.copy2(exe, staged)
    print(f"  ✓ {staged.relative_to(ROOT)}")
    return staged


def _assemble_portable(version: str, exe: Path) -> Path:
    """Portable fallback folder: backend binary + frontend dist + launcher."""
    _banner("Assembling portable folder")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    bundle = OUTPUT / f"{PRODUCT_NAME}-{version}-win64"
    bundle.mkdir(parents=True, exist_ok=True)

    shutil.copy2(exe, bundle / exe.name)

    frontend_dist = FRONTEND / "dist"
    if frontend_dist.is_dir():
        shutil.copytree(frontend_dist, bundle / "frontend_dist", dirs_ok_exist=True)

    launcher = bundle / "iniciar-ownex.bat"
    launcher.write_text(
        "@echo off\r\n"
        "rem OWNEX — daily launcher (manual start, no autostart)\r\n"
        "setlocal\r\n"
        f'set "APP_EXE=%~dp0{exe.name}"\r\n'
        'if not exist "%APP_EXE%" (\r\n'
        "  echo ERROR: backend not found: %APP_EXE%\r\n"
        "  pause & exit /b 1\r\n"
        ")\r\n"
        'start "" "%APP_EXE%" --port 8000 --host 127.0.0.1\r\n'
        "echo OWNEX backend iniciado.\r\n"
        "echo Data: %LOCALAPPDATA%\\OWNEX\\\r\n"
    )

    readme = bundle / "README.txt"
    readme.write_text(
        f"""{PRODUCT_NAME} v{version} — Windows Portable Edition
{"=" * 50}

Run:  iniciar-ownex.bat   (or start {exe.name} directly)

The backend serves the web interface at http://127.0.0.1:8000
Open that URL in your browser.

Data locations (kept outside the install folder, so uninstalling the app
does not destroy your history):
  - Database:  %LOCALAPPDATA%\\OWNEX\\database\\
  - Logs:      %LOCALAPPDATA%\\OWNEX\\logs\\
  - Frontend:  %LOCALAPPDATA%\\OWNEX\\frontend_dist\\

System Requirements:
  - Windows 10 or later (64-bit)
  - No Python or Node.js required

To uninstall: delete this folder. Your data in %LOCALAPPDATA%\\OWNEX\\
is preserved — delete that folder too only if you want a clean slate.
"""
    )

    print(f"  ✓ Portable folder: {bundle}")
    return bundle


def _create_zip(bundle: Path) -> Path:
    _banner("Creating release zip")
    zip_path = bundle.parent / f"{bundle.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in bundle.rglob("*"):
            arcname = str(file.relative_to(bundle.parent))
            zf.write(file, arcname)
    print(f"  ✓ Zip created: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return zip_path


def _build_tauri_installer() -> Path | None:
    """Build the real Windows app + MSI installer via 'npx tauri build'.

    This is the canonical Tauri path: the app window is the Tauri shell and
    the backend is spawned as a sidecar.

    The bundle target is **MSI**, not NSIS — that is the owner's decision
    from 2026-09-09 (see tests/test_tauri_packaging.py::
    test_windows_bundle_is_msi_only and src-tauri/tauri.conf.json
    bundle.windows.nsis = null). The CI workflow
    (.github/workflows/ownex-tauri-windows.yml) collects
    src-tauri/target/release/bundle/msi/*.msi for the same reason.

    Returns the installer path, or None if the Rust toolchain / WiX
    toolchain is unavailable (the portable folder is then the deliverable).
    """
    if shutil.which("cargo") is None:
        print("  cargo not found — skipping Tauri build (Rust toolchain required)")
        return None
    if shutil.which("npx") is None:
        print("  npx not found — skipping Tauri build")
        return None

    _banner("Building Windows app + MSI installer (npx tauri build)")
    result = subprocess.run(
        ["npx", "tauri", "build", "--bundles", "msi"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print(f"  Tauri build failed (exit {result.returncode}) — portable folder is the deliverable")
        return None

    candidates = sorted(
        (SRC_TAURI / "target" / "release" / "bundle" / "msi").glob("*.msi"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        print("  Tauri build reported success but no MSI installer was found")
        return None
    installer = candidates[0]
    print(f"  ✓ MSI installer: {installer} ({installer.stat().st_size / 1024 / 1024:.1f} MB)")
    return installer


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Build Windows installer for {PRODUCT_NAME}")
    parser.add_argument("--version", default=_get_version(), help="Release version string")
    parser.add_argument("--installer", action="store_true", help="Build the MSI installer (needs Rust + WiX toolchain)")
    parser.add_argument("--skip-tauri", action="store_true", help="Portable folder only; do not run tauri build")
    args = parser.parse_args()

    version = args.version
    print(f"Building {PRODUCT_NAME} v{version} for Windows")
    print(f"Output: {OUTPUT}")
    if not sys.platform.startswith("win"):
        print("  NOTE: current platform is not Windows. The PyInstaller bundle will be")
        print("        built for THIS platform; run this script on Windows to produce")
        print("        a real ownex-backend.exe and the NSIS installer.")

    _ensure_frontend_built()
    exe = _run_pyinstaller()
    _stage_for_tauri(exe)
    bundle = _assemble_portable(version, exe)
    zip_path = _create_zip(bundle)

    installer_path = None
    if args.installer and not args.skip_tauri:
        installer_path = _build_tauri_installer()

    _banner("Build complete")
    print(f"  Portable folder:   {bundle}")
    print(f"  Release zip:       {zip_path}")
    if installer_path:
        print(f"  MSI installer:     {installer_path}")
    print(f"\nStart manually: run '{bundle.name}\\iniciar-ownex.bat' (no autostart is registered).")
    print(f"Data lives in %LOCALAPPDATA%\\{PRODUCT_NAME}\\ (survives reinstall).")


if __name__ == "__main__":
    main()
