#!/usr/bin/env python3
"""OWNEX Portable Package Builder.

Creates a self-contained portable distribution in build/portable/.

The output folder can be copied anywhere and run without dependencies
on the original repo, .venv, or VSCode.

Usage:
    python scripts/package_portable.py [--dev] [--skip-pyinstaller]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BUILD_DIR = PROJECT_ROOT / "build"
PORTABLE_DIR = BUILD_DIR / "portable"
DIST_DIR = PROJECT_ROOT / "dist"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def log(step: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{step:>20}] {msg}")


def _run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> bool:
    try:
        result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            log("CMD", f"FAILED: {' '.join(cmd)}")
            log("CMD", result.stderr[-500:] if result.stderr else "no stderr")
            return False
        return True
    except subprocess.TimeoutExpired:
        log("CMD", f"TIMEOUT after {timeout}s")
        return False
    except FileNotFoundError as exc:
        log("CMD", f"NOT FOUND: {exc}")
        return False


def build_frontend() -> bool:
    dist = FRONTEND_DIR / "dist"
    if dist.is_dir() and list(dist.rglob("*.html")):
        log("FRONTEND", "Already built — skipping")
        return True

    log("FRONTEND", "Building frontend...")
    if not _run_cmd(["npm", "install", "--silent"], cwd=FRONTEND_DIR, timeout=120):
        return False
    if not _run_cmd(["npm", "run", "build"], cwd=FRONTEND_DIR, timeout=120):
        return False
    if not dist.is_dir():
        log("FRONTEND", "FAILED — no dist/ generated")
        return False
    log("FRONTEND", f"OK — {sum(1 for _ in dist.rglob('*'))} files")
    return True


def build_pyinstaller() -> bool:
    # The canonical spec lives at the repo root. `CATEYE.spec` was the old
    # name and no longer exists — this path silently skipped the build.
    spec = PROJECT_ROOT / "OWNEX-Backend.spec"
    if not spec.exists():
        log("PYINSTALLER", "SKIP — no OWNEX-Backend.spec found")
        return False

    binary = DIST_DIR / ("ownex-backend.exe" if sys.platform.startswith("win") else "ownex-backend")
    if binary.exists():
        log("PYINSTALLER", f"Already built ({binary}) — skipping")
        return True

    if not shutil.which("pyinstaller"):
        log("PYINSTALLER", "SKIP — PyInstaller not installed (install with: pip install pyinstaller)")
        return False

    log("PYINSTALLER", "Building binary...")
    if not _run_cmd([sys.executable, "-m", "PyInstaller", "OWNEX-Backend.spec", "--noconfirm"], timeout=900):
        return False

    if not binary.exists():
        log("PYINSTALLER", f"FAILED — {binary} not found")
        return False

    log("PYINSTALLER", f"OK — {binary.stat().st_size / 1024 / 1024:.1f} MB")
    return True


def create_portable_dist(skip_pyinstaller: bool) -> Path:
    log("PORTABLE", f"Creating portable distribution in {PORTABLE_DIR}")

    # Clean
    if PORTABLE_DIR.exists():
        shutil.rmtree(PORTABLE_DIR)
    PORTABLE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Binary ──
    # The spec emits a ONEFILE executable at dist/ownex-backend[.exe]
    # (not a dist/CATEYE/ directory — that was the old ONEDIR layout).
    if not skip_pyinstaller and build_pyinstaller():
        binary = DIST_DIR / ("ownex-backend.exe" if sys.platform.startswith("win") else "ownex-backend")
        if binary.exists():
            log("PORTABLE", "Copying PyInstaller build...")
            shutil.copy2(binary, PORTABLE_DIR / binary.name)

    # ── Frontend dist (fallback if PyInstaller didn't bundle it) ──
    frontend_dist = FRONTEND_DIR / "dist"
    if frontend_dist.is_dir():
        dest = PORTABLE_DIR / "frontend_dist"
        if not dest.exists():
            shutil.copytree(frontend_dist, dest)
            log("PORTABLE", f"Frontend dist copied ({sum(1 for _ in frontend_dist.rglob('*'))} files)")

    # ── Create directory structure ──
    dirs = [
        "data/database",
        "data/uploads",
        "data/evidence",
        "config",
        "logs",
        "backups",
        "tools",
        "docs",
    ]
    for d in dirs:
        (PORTABLE_DIR / d).mkdir(parents=True, exist_ok=True)

    # ── Documentation ──
    docs = [
        "README.md",
        "SYSTEM.md",
        "FUNCTIONAL_SPEC.md",
        "USER_GUIDE.md",
        "DAILY_WORKFLOW.md",
        "SETUP_GUIDE.md",
        "RELEASE_NOTES_v3.0.0.md",
        "CHANGELOG.md",
        "LICENSE",
    ]
    for doc in docs:
        src = PROJECT_ROOT / doc
        if src.exists():
            shutil.copy2(src, PORTABLE_DIR / "docs" / doc)

    # ── VERSION file at root ──
    version_src = PROJECT_ROOT / "VERSION"
    if version_src.exists():
        version = version_src.read_text().strip()
        shutil.copy2(version_src, PORTABLE_DIR / "VERSION")
        log("PORTABLE", f"VERSION: {version}")
    else:
        version = "3.0.0"
        (PORTABLE_DIR / "VERSION").write_text(f"{version}\n")

    # ── LICENSE at root ──
    license_src = PROJECT_ROOT / "LICENSE"
    if license_src.exists():
        shutil.copy2(license_src, PORTABLE_DIR / "LICENSE")

    # ── README.txt at root ──
    readme = PORTABLE_DIR / "README.txt"
    readme.write_text(
        f"OWNEX v{version}\n"
        f"{'=' * 40}\n"
        f"Autonomous Work Operating Platform\n"
        f"\n"
        f"QUICK START:\n"
        f"  Windows: run install.bat (one-time setup), then run.bat (daily launch)\n"
        f"  Linux:   run ./ownex-backend.sh\n"
        f"\n"
        f"Backend:  http://127.0.0.1:8000\n"
        f"Data dir: ./data/\n"
        f"See docs/ for full documentation.\n"
    )

    # ── install.bat (Windows) ──
    install_bat_src = SCRIPT_DIR / "install_portable.bat"
    if install_bat_src.exists():
        shutil.copy2(install_bat_src, PORTABLE_DIR / "install.bat")
        log("PORTABLE", "install.bat copied")

    # ── run.bat (Windows, minimal — run.py handles portable detection) ──
    run_bat_src = SCRIPT_DIR / "run_portable.bat"
    if run_bat_src.exists():
        shutil.copy2(run_bat_src, PORTABLE_DIR / "run.bat")
        log("PORTABLE", "run.bat copied")

    # ── Launcher (Linux/macOS) ──
    # The backend entrypoint accepts --port/--host/--data-dir/--log-level.
    # `--browser` never existed as a flag, so the old launcher failed on
    # the first argument it passed.
    launcher = PORTABLE_DIR / "ownex-backend.sh"
    launcher.write_text(
        "#!/usr/bin/env bash\n"
        "# OWNEX Portable Launcher\n"
        'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
        'export OWNEX_DATA_DIR="${SCRIPT_DIR}/data"\n'
        'exec "${SCRIPT_DIR}/ownex-backend" --host 127.0.0.1 --port 8000 --data-dir "${SCRIPT_DIR}/data" "$@"\n'
    )
    launcher.chmod(0o755)

    # ── Verify ──
    log("PORTABLE", "Verifying portable distribution...")
    all_ok = True
    for name in dirs + ["install.bat", "run.bat", "ownex-backend.sh", "VERSION", "LICENSE", "README.txt"]:
        path = PORTABLE_DIR / name
        if path.exists():
            size = ""
            if path.is_file():
                size = f" ({path.stat().st_size / 1024:.0f} KB)"
            log("PORTABLE", f"  [OK] {name}{size}")
        else:
            log("PORTABLE", f"  [MISSING] {name}")
            all_ok = False

    # Check for binary
    for bin_name in ["ownex-backend", "ownex-backend.exe"]:
        if (PORTABLE_DIR / bin_name).exists():
            log("PORTABLE", f"  [OK] {bin_name} ({(PORTABLE_DIR / bin_name).stat().st_size / 1024 / 1024:.1f} MB)")
            break
    else:
        log("PORTABLE", "  [--] Binary not found (build with --skip-pyinstaller only for dev mode)")
        if not skip_pyinstaller:
            log("PORTABLE", "  Build failed or PyInstaller not available")

    total_mb = sum(f.stat().st_size for f in PORTABLE_DIR.rglob("*") if f.is_file()) / 1024 / 1024
    log("PORTABLE", f"\nTotal size: {total_mb:.1f} MB")
    log("PORTABLE", f"Output: {PORTABLE_DIR}")

    if all_ok:
        log("PORTABLE", "✓ All directories and launchers created")
    else:
        log("PORTABLE", "⚠ Some components missing — check output above")

    return PORTABLE_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="OWNEX Portable Package Builder")
    parser.add_argument("--dev", action="store_true", help="Skip PyInstaller (for development testing)")
    parser.add_argument("--skip-pyinstaller", action="store_true", help="Skip PyInstaller build")
    args = parser.parse_args()

    skip_pyinstaller = args.dev or args.skip_pyinstaller

    log("BUILD", "OWNEX Portable Package Builder")
    log("BUILD", f"Platform: {sys.platform}")
    log("BUILD", f"Dev mode (skip PyInstaller): {skip_pyinstaller}")

    if not skip_pyinstaller and not build_frontend():
        log("BUILD", "Frontend build failed — aborting")
        sys.exit(1)

    create_portable_dist(skip_pyinstaller)

    log("BUILD", "")
    log("BUILD", "To test on a clean machine:")
    log("BUILD", f"  1. Copy {PORTABLE_DIR} to a USB drive or empty folder")
    log("BUILD", "  Windows: run install.bat (one-time), then run.bat (daily)")
    log("BUILD", "  Linux:   run ./ownex-backend.sh")
    log("BUILD", "  3. The setup wizard will open automatically")
    log("BUILD", "Done.")


if __name__ == "__main__":
    main()
