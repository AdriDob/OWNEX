#!/usr/bin/env python3
"""OWNEX Desktop build — PyInstaller bundler for the Tauri sidecar.

This is the script referenced by:

- ``Makefile`` targets ``build-desktop`` / ``build-desktop-onefile``
- ``scripts/install_windows.py`` (``_run_pyinstaller``)

It is a thin, deliberate wrapper around the canonical PyInstaller spec
``OWNEX-Backend.spec`` (repo root). The spec is the single source of truth
for the bundle: it auto-discovers routers and core packages, collects
datas/binaries, and emits a **ONEFILE** executable.

Why ONEFILE (and why this wrapper does not fight it):
``src-tauri/tauri.conf.json`` declares ``externalBin: ["binaries/ownex-backend"]``.
Tauri bundles and spawns exactly one file per target triple, so the sidecar
must be self-contained. A ONEDIR copy without its ``_internal/`` directory
cannot import ``api.main`` — that is the failure that shipped in the
2026-08-24 MSI. The spec's own header says the same thing.

Usage:
    python desktop/build/build_desktop.py                    # onefile (default)
    python desktop/build/build_desktop.py --onedir           # accepted, spec decides
    python desktop/build/build_desktop.py --rebuild-frontend
    python desktop/build/build_desktop.py --clean --noconfirm

Output:
    dist/ownex-backend          (Linux/macOS)
    dist/ownex-backend.exe      (Windows)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = ROOT / "OWNEX-Backend.spec"
FRONTEND = ROOT / "frontend"
DIST = ROOT / "dist"

EXE_STEM = "ownex-backend"


def _log(msg: str) -> None:
    print(f"[build-desktop] {msg}", flush=True)


def _fail(msg: str, code: int = 1) -> None:
    print(f"\n[build-desktop] ERROR: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def _spec_path() -> Path:
    if not SPEC.is_file():
        _fail(
            f"PyInstaller spec not found: {SPEC}\n           The canonical spec is OWNEX-Backend.spec at the repo root."
        )
    return SPEC


def _rebuild_frontend() -> None:
    """Build the frontend if requested and the toolchain is available."""
    if not (FRONTEND / "package.json").is_file():
        _log("no frontend/package.json — skipping frontend build")
        return
    if shutil.which("npm") is None:
        _fail("npm not found in PATH — cannot rebuild frontend", code=2)
    _log("building frontend (npm ci && npm run build)")
    for cmd in (["npm", "ci"], ["npm", "run", "build"]):
        result = subprocess.run(cmd, cwd=FRONTEND)
        if result.returncode != 0:
            _fail(f"frontend command failed: {' '.join(cmd)}", code=result.returncode or 2)
    _log("frontend built")


def _run_pyinstaller(spec: Path, clean: bool, noconfirm: bool) -> Path:
    cmd = [sys.executable, "-m", "PyInstaller", str(spec)]
    if clean:
        cmd.append("--clean")
    if noconfirm:
        cmd.append("--noconfirm")
    _log(f"running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        _fail(f"PyInstaller failed with exit code {result.returncode}", code=result.returncode or 2)

    exe = DIST / (f"{EXE_STEM}.exe" if sys.platform.startswith("win") else EXE_STEM)
    if not exe.exists():
        _fail(
            f"PyInstaller reported success but no executable at {exe}\n"
            f"           Contents of dist/: {[p.name for p in DIST.iterdir()] if DIST.is_dir() else '(no dist dir)'}"
        )
    return exe


def build(
    *,
    spec: Path | None = None,
    clean: bool = False,
    noconfirm: bool = False,
    rebuild_frontend: bool = False,
) -> Path:
    """Build the desktop sidecar and return the path to the executable.

    This is the programmatic entry point. The historical contract expected a
    module-level ``build`` symbol here (pinned by
    tests/test_desktop_release.py::TestBuildScripts), so the name and the
    "CATEYE Desktop binary" wording are kept even though the product was
    renamed to OWNEX.
    """
    spec = spec or _spec_path()
    if rebuild_frontend:
        _rebuild_frontend()
    return _run_pyinstaller(spec, clean, noconfirm)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build CATEYE Desktop binary (OWNEX PyInstaller sidecar)",
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Accepted for backwards compatibility. The canonical spec emits ONEFILE, "
        "which the Tauri externalBin contract requires.",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Explicitly request ONEFILE (the spec default; no-op).",
    )
    parser.add_argument(
        "--rebuild-frontend",
        action="store_true",
        help="Run 'npm ci && npm run build' in frontend/ before bundling.",
    )
    parser.add_argument("--clean", action="store_true", help="PyInstaller --clean")
    parser.add_argument("--noconfirm", action="store_true", help="PyInstaller --noconfirm")
    args = parser.parse_args()

    if args.onedir:
        _log(
            "--onedir requested, but OWNEX-Backend.spec is ONEFILE by design "
            "(Tauri externalBin bundles exactly one file). Proceeding with ONEFILE."
        )

    spec = _spec_path()
    _log(f"spec: {spec.relative_to(ROOT)}")
    _log(f"target: {sys.platform} ({'windows' if sys.platform.startswith('win') else 'posix'})")

    if args.rebuild_frontend:
        _rebuild_frontend()

    exe = build(
        spec=spec,
        clean=args.clean,
        noconfirm=args.noconfirm,
    )
    size_mb = exe.stat().st_size / (1024 * 1024)
    _log(f"OK -> {exe} ({size_mb:.1f} MB)")

    print("\nNext step: copy the binary to src-tauri/binaries/ (Tauri externalBin) or")
    print("          run 'python scripts/install_windows.py' to assemble the Windows bundle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
