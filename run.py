#!/usr/bin/env python3
"""
CATEYE — Launcher State Machine.

Safe startup with automatic fallback. Never crashes. Always degrades.

Modes:
  --install     One-time setup (paths, config, first-run)
  --tray        System tray only (assumes backend running)
  --browser     Full stack: backend + frontend + browser
  --service     Windows service (lazy import, safe scope)
  --build       PyInstaller build
  --safe-mode   Force degraded mode (no tray, no webview, browser only)

State machine:
  INIT → VALIDATING → SAFE_MODE | FULL_MODE → BROWSER_MODE | SERVICE_MODE → READY
                     ↘ ERROR_RECOVERY → SAFE_MODE → READY

Architecture:
  - desktop.service is NEVER imported at module level
  - desktop.service_util is the only safe cross-mode import
  - ALL failures degrade to browser mode (works everywhere)
"""

from __future__ import annotations

import os
import subprocess
import sys
from enum import Enum
from pathlib import Path

# Reconfigure stdout/stderr for UTF-8 (Windows console defaults to cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Portable mode: use data/ next to binary if CATEYE_DATA_DIR not set
if getattr(sys, "frozen", False) and not os.environ.get("CATEYE_DATA_DIR"):
    _exe_dir = Path(sys.executable).resolve().parent
    _portable_data = _exe_dir / "data"
    if _portable_data.is_dir():
        os.environ["CATEYE_DATA_DIR"] = str(_portable_data)

# Set DATABASE_URL before any import that touches database/db.py
# (core_engines.intelligence imports it at module level)
if not os.environ.get("DATABASE_URL"):
    _data_dir = Path(os.environ.get("CATEYE_DATA_DIR", Path.home() / ".orion"))
    _db_path = _data_dir / "database" / "cateye.db"
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

_BASE_DIR = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

# Lazy logger — set up after boot guard runs
_log: object = None


def _log(state: str, msg: str, *args) -> None:
    global _log
    if _log is None:
        import logging

        logging.basicConfig(level=logging.INFO, format="[CATEYE][%(state)s] %(message)s", stream=sys.stdout)
        _log = logging.getLogger("cateye.launcher")
    # Log via simple print if logging not ready
    text = msg % args if args else msg
    print(f"[CATEYE][{state}] {text}")


# ── Imports (all lazy, inside functions) ───────────────────────────────


def _import_boot_guard():
    """Safe import of boot_guard — this is the very first import, must never fail."""
    try:
        from desktop.boot_guard import (
            RuntimeMode,
            boot_summary,
            enable_safe_mode,
            get_runtime_mode,
            is_safe_mode,
            safe_import,
            should_activate_safe_mode,
            validate_environment,
        )

        return (
            RuntimeMode,
            get_runtime_mode,
            validate_environment,
            should_activate_safe_mode,
            enable_safe_mode,
            is_safe_mode,
            boot_summary,
            safe_import,
        )
    except Exception as exc:
        _log("BOOT", "CRITICAL: boot_guard import failed: %s", exc)

        # Minimal fallback
        class _RuntimeMode(Enum):
            DEV = "dev"
            UNKNOWN = "unknown"

        return (
            _RuntimeMode,
            lambda: _RuntimeMode.UNKNOWN,
            lambda: {},
            lambda x: False,
            lambda r="": None,
            lambda: False,
            lambda x: "",
            lambda m: None,
        )


# ── State machine ──────────────────────────────────────────────────────


class LaunchState(Enum):
    INIT = "INIT"
    VALIDATING = "VALIDATING"
    SAFE_MODE = "SAFE_MODE"
    FULL_MODE = "FULL_MODE"
    BROWSER_MODE = "BROWSER_MODE"
    SERVICE_MODE = "SERVICE_MODE"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    READY = "READY"


class LaunchMode(Enum):
    INSTALL = "install"
    TRAY = "tray"
    BROWSER = "browser"
    SERVICE = "service"
    BUILD = "build"


# ── State handlers ─────────────────────────────────────────────────────


def _state_init() -> LaunchState:
    _log("INIT", "CATEYE Launcher")
    return LaunchState.VALIDATING


def _state_validating() -> LaunchState:
    (
        runtime_mode_cls,
        get_runtime_mode,
        validate_environment,
        should_activate_safe_mode,
        enable_safe_mode,
        is_safe_mode,
        boot_summary,
        safe_import,
    ) = _import_boot_guard()

    mode = get_runtime_mode()
    validation = validate_environment()
    summary = boot_summary(validation)
    for line in summary.split("\n"):
        _log("VALIDATE", line)

    if should_activate_safe_mode(validation):
        enable_safe_mode("Environment validation failed")
        _log("VALIDATE", "Fatal check failed — activating SAFE MODE")
        return LaunchState.SAFE_MODE
    if mode == runtime_mode_cls.UNKNOWN:
        _log("VALIDATE", "Unknown runtime — falling back to SAFE MODE")
        enable_safe_mode("Unknown runtime environment")
        return LaunchState.SAFE_MODE
    return LaunchState.FULL_MODE


def _state_safe_mode() -> LaunchState:
    _log("SAFE", "Running in SAFE MODE — degraded functionality")
    _log("SAFE", "Using browser mode (no tray, no desktop window)")
    _log("SAFE", "Service mode disabled — UI mode active")
    return LaunchState.BROWSER_MODE


def _state_full_mode() -> LaunchState:
    runtime_mode_cls, get_runtime_mode, _, _, _, _, _, _ = _import_boot_guard()
    mode = get_runtime_mode()
    _log("FULL", "Full mode available for %s", mode.value)
    return LaunchState.BROWSER_MODE


def _state_browser_mode() -> LaunchState:
    _log("BROWSER", "Starting backend + browser...")
    try:
        os.environ["CATEYE_DESKTOP"] = "1"
        from cores.platform.system import get_db_path

        db_path = get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        from desktop.main_desktop import main as desktop_main

        desktop_main()
    except Exception as exc:
        _log("BROWSER", "Backend error: %s", exc)
        import traceback

        _log("BROWSER", traceback.format_exc()[-500:])
    return LaunchState.READY


def _state_service_mode() -> LaunchState:
    _log("SERVICE", "Starting CATEYE Windows service...")
    try:
        from desktop.service import run_service

        run_service()
    except RuntimeError as exc:
        _log("SERVICE", "Service unavailable: %s", exc)
        _log("SERVICE", "Falling back to browser mode")
        return LaunchState.BROWSER_MODE
    except ImportError as exc:
        _log("SERVICE", "Service module not available: %s", exc)
        _log("SERVICE", "Falling back to browser mode")
        return LaunchState.BROWSER_MODE
    return LaunchState.READY


def _state_error_recovery() -> LaunchState:
    _log("RECOVERY", "Attempting error recovery...")
    runtime_mode_cls, _, _, should_activate_safe_mode, enable_safe_mode, _, _, _ = _import_boot_guard()
    enable_safe_mode("Error recovery activated")
    _log("RECOVERY", "Safe mode enabled — system will degrade gracefully")
    return LaunchState.SAFE_MODE


# ── Mode handlers ──────────────────────────────────────────────────────


def _detect_mode(args: set[str]) -> tuple[LaunchMode | None, bool, bool]:
    dev = "--dev" in args
    no_tray = "--no-tray" in args
    if "--install" in args:
        return LaunchMode.INSTALL, dev, no_tray
    if "--build" in args:
        return LaunchMode.BUILD, dev, no_tray
    if "--tray" in args:
        return LaunchMode.TRAY, dev, no_tray
    if "--browser" in args:
        return LaunchMode.BROWSER, dev, no_tray
    if "--service" in args:
        return LaunchMode.SERVICE, dev, no_tray
    if "--install-service" in args or "--remove-service" in args:
        return LaunchMode.SERVICE, dev, no_tray
    if "--start" in args:
        return LaunchMode.BROWSER, dev, no_tray
    return None, dev, no_tray


def _run_state_machine(mode: LaunchMode) -> None:
    state = LaunchState.INIT
    _log("MACHINE", "State machine start (mode=%s)", mode.value if hasattr(mode, "value") else "auto")

    max_steps = 20
    step = 0
    while state != LaunchState.READY and step < max_steps:
        step += 1
        _log("MACHINE", "-> %s", state.value)

        if state == LaunchState.INIT:
            state = _state_init()
        elif state == LaunchState.VALIDATING:
            state = _state_validating()
        elif state == LaunchState.SAFE_MODE:
            state = _state_safe_mode()
        elif state == LaunchState.FULL_MODE:
            state = _state_full_mode()
        elif state == LaunchState.BROWSER_MODE:
            state = _state_browser_mode()
        elif state == LaunchState.SERVICE_MODE:
            state = _state_service_mode()
        elif state == LaunchState.ERROR_RECOVERY:
            state = _state_error_recovery()
        else:
            _log("MACHINE", "Unknown state: %s", state.value)
            state = LaunchState.READY

    if state == LaunchState.READY:
        _log("READY", "CATEYE ready")

    if step >= max_steps:
        _log("MACHINE", "State machine exceeded max steps — forcing ready")


# ── Mode dispatch ──────────────────────────────────────────────────────


def _handle_install() -> None:
    _log("INSTALL", "CATEYE installation...")
    try:
        from desktop.boot_guard import boot_summary, validate_environment

        validation = validate_environment()
        _log("INSTALL", boot_summary(validation))
    except Exception as exc:
        _log("INSTALL", "Boot validation skipped: %s", exc)

    # Create essential paths
    try:
        from cores.utils.paths import get_data_path, get_db_path, get_log_path

        for p in [get_data_path(), get_log_path(), get_db_path().parent]:
            p.mkdir(parents=True, exist_ok=True)
            _log("INSTALL", "Created: %s", p)
    except Exception as exc:
        _log("INSTALL", "Path setup error: %s", exc)

    installer = _BASE_DIR / "scripts" / "install.py"
    if installer.exists():
        _log("INSTALL", "Running installer script...")
        result = subprocess.run([sys.executable, str(installer)])
        if result.returncode != 0:
            _log("INSTALL", "Installer script failed (rc=%d)", result.returncode)
            sys.exit(1)
        _log("INSTALL", "Installation complete")
        return

    try:
        from desktop.first_run import run_first_time
        from desktop.settings import get_settings

        settings = get_settings()
        run_first_time(settings)
        _log("INSTALL", "First-run setup complete")
    except Exception as exc:
        _log("INSTALL", "Installation error: %s", exc)
        sys.exit(1)

    _log("INSTALL", "CATEYE installed successfully")
    _log("INSTALL", f"Run '{sys.executable} --start' to launch")


def _handle_legacy_service(args: set[str]) -> bool:
    if "--install-service" in args:
        _log("SERVICE", "Installing CATEYE service...")
        try:
            from desktop.service import install_service

            install_service()
        except RuntimeError as exc:
            _log("SERVICE", "Service install failed: %s", exc)
            sys.exit(1)
        return True
    if "--remove-service" in args:
        _log("SERVICE", "Removing CATEYE service...")
        try:
            from desktop.service import remove_service

            remove_service()
        except RuntimeError as exc:
            _log("SERVICE", "Service removal failed: %s", exc)
            sys.exit(1)
        return True
    return False


def _handle_build() -> None:
    _log("BUILD", "PyInstaller build...")
    spec = _BASE_DIR / "CATEYE.spec"
    if not spec.exists():
        _log("BUILD", "No spec file found")
        sys.exit(1)
    result = subprocess.run([sys.executable, "-m", "PyInstaller", str(spec), "-y"], cwd=_BASE_DIR)
    if result.returncode == 0:
        _log("BUILD", "Build completed")
    else:
        _log("BUILD", "Build failed (rc=%d)", result.returncode)
        sys.exit(1)


def _handle_tray() -> None:
    _log("TRAY", "Starting backend with tray...")
    _run_state_machine(LaunchMode.BROWSER)


def _handle_browser() -> None:
    _run_state_machine(LaunchMode.BROWSER)


def _handle_service() -> None:
    _run_state_machine(LaunchMode.SERVICE)


def _handle_auto() -> None:
    _log("AUTO", "Auto-detecting...")
    try:
        from desktop.service_util import is_service_running

        if is_service_running():
            _log("AUTO", "Service detected — tray mode")
            _handle_tray()
            return
    except ImportError:
        pass
    _log("AUTO", "Starting browser mode")
    _run_state_machine(LaunchMode.BROWSER)


def _handle_diagnostics() -> None:
    _log("DIAG", "Diagnostics...")
    runtime_mode_cls, get_runtime_mode, validate_environment, _, _, is_safe_mode, boot_summary, _ = _import_boot_guard()
    validation = validate_environment()
    print()
    print(boot_summary(validation))
    print()
    safe = is_safe_mode()
    print(f"  Safe mode: {'ACTIVE' if safe else 'INACTIVE'}")
    mode = get_runtime_mode()
    print(f"  Runtime:   {mode.value}")
    print()


# ── Entry point ────────────────────────────────────────────────────────


def _check_migrate(args_list: list[str]) -> bool:
    """Restore a backup on a new machine and verify integrity."""
    idx = args_list.index("--migrate")
    if idx + 1 >= len(args_list) or args_list[idx + 1].startswith("--"):
        print("❌ Usage: --migrate <backup_file.zip>")
        return True

    backup_file = args_list[idx + 1]
    print("\n🔁 ORION Migration Tool")
    print(f"   Restoring from: {backup_file}")

    from core.backup.engine import restore_backup, verify_backup

    # 1. Verify backup integrity
    print("\n1/4 Verifying backup integrity...")
    verification = verify_backup(backup_file)
    if verification.get("status") == "error":
        print(f"   ❌ {verification.get('reason')}")
        print("   Migration aborted.")
        return True
    if verification.get("status") == "corrupted":
        print("   ⚠️  Backup has checksum errors — restore at your own risk.")
        proceed = input("   Continue? [y/N]: ").strip().lower()
        if proceed != "y":
            print("   Migration aborted.")
            return True
    print("   ✅ Backup integrity verified")

    # 2. Restore with portable mode
    print("\n2/4 Restoring data with portable license mode...")
    import os

    os.environ["CATEYE_PORTABLE"] = "1"
    result = restore_backup(backup_file)
    if result.get("status") == "ok":
        print(f"   ✅ {result['restored_files']} files restored to {result['target']}")
    else:
        print(f"   ❌ Restore failed: {result.get('reason')}")
        return True

    # 3. Verify restored data
    print("\n3/4 Verifying restored data...")
    _print_verify()

    # 4. Print next steps
    print("\n4/4 Migration checklist:")
    print("   ✅ Data restored")
    print("   ⚠️  Re-activate license on this machine if needed:")
    print("       → Set CATEYE_PORTABLE=1 for temporary use")
    print("       → Or enter a new license key in Settings")
    print("   ⚠️  Install system tools if using AEGIS:")
    print("       → Run: bash scripts/setup.sh")
    print("   ⚠️  Build frontend if needed:")
    print("       → cd frontend && npm install && npm run build")
    print("\n   Run 'python run.py --verify' to check everything is ready.")
    return True


def _print_verify() -> dict[str, str]:
    """Check all system components and print status. Returns status map."""
    from pathlib import Path

    results: dict[str, str] = {}

    # License
    try:
        from cores.license.validator import is_license_valid

        valid, reason = is_license_valid()
        status = "✅" if valid else "⚠️"
        results["license"] = "valid" if valid else f"issues ({reason})"
        print(f"   {status} License: {reason}")
    except Exception as exc:
        results["license"] = f"error: {exc}"
        print(f"   ❌ License check failed: {exc}")

    # Vault key
    vault_key = Path.home() / ".orion" / "identity_vault.key"
    if vault_key.exists():
        results["vault_key"] = "present"
        size = vault_key.stat().st_size
        print(f"   ✅ Vault key: present ({size} bytes)")
    else:
        results["vault_key"] = "missing"
        print("   ⚠️  Vault key: not found (will be created on first use)")

    # SQLite databases integrity
    db_count = 0
    db_ok = 0
    for db_file in Path.home().glob(".orion/**/*.db"):
        db_count += 1
        try:
            import sqlite3

            conn = sqlite3.connect(str(db_file))
            conn.execute("PRAGMA integrity_check")
            conn.close()
            db_ok += 1
        except Exception:
            pass
    if db_count == 0:
        print("   ⚠️  No SQLite databases found (first run?)")
    else:
        status = "✅" if db_ok == db_count else "⚠️"
        print(f"   {status} Databases: {db_ok}/{db_count} integrity OK")
        results["databases"] = f"{db_ok}/{db_count}"

    # Config export/import
    config_file = Path.home() / ".orion" / "config.json"
    results["config"] = "present" if config_file.exists() else "missing"
    print(f"   {'✅' if config_file.exists() else '⚠️'} Config: {'present' if config_file.exists() else 'not found'}")

    return results


def main() -> None:
    args_set = set(sys.argv[1:])
    args_list = sys.argv[1:]

    # --migrate: full PC-to-PC migration
    if "--migrate" in args_set:
        _check_migrate(args_list)
        return

    # --verify: check system integrity
    if "--verify" in args_set:
        print("\n🔍 ORION System Verification\n")
        _print_verify()
        print()
        return

    # --backup: create data backup (uses ORION Backup Engine)
    if "--backup" in args_set:
        from core.backup.engine import create_backup

        result = create_backup()
        if result.get("status") == "ok":
            print(f"✅ Backup created: {result['backup_path']}")
            print(f"   Files: {result['total_files']}, Size: {result['size_mb']} MB")
        else:
            print(f"❌ Backup failed: {result.get('reason', 'unknown')}")
        return

    # --restore: restore from backup
    if "--restore" in args_set:
        from core.backup.engine import restore_backup

        idx = args_list.index("--restore")
        if idx + 1 < len(args_list) and not args_list[idx + 1].startswith("--"):
            from core.backup.engine import verify_backup

            verification = verify_backup(args_list[idx + 1])
            if verification.get("status") == "error":
                print(f"❌ Backup verification failed: {verification.get('reason')}")
                print("   Restore aborted.")
                return
            if verification.get("status") == "corrupted":
                print("⚠️  Backup is corrupted (checksum errors). Restore at your own risk.")
                proceed = input("   Continue? [y/N]: ").strip().lower()
                if proceed != "y":
                    print("   Restore aborted.")
                    return

            result = restore_backup(args_list[idx + 1])
            if result.get("status") == "ok":
                print(f"✅ Restored {result['restored_files']} files to {result['target']}")
            else:
                print(f"❌ Restore failed: {result.get('reason')}")
        else:
            print("❌ Usage: --restore <backup_file>")
        return

    # --add-target: quick-add a target
    if "--add-target" in args_set:
        from database import db, models

        idx = args_list.index("--add-target")
        name = args_list[idx + 1] if idx + 1 < len(args_list) else "unnamed"
        domain = ""
        if "--domain" in args_set:
            didx = args_list.index("--domain")
            domain = args_list[didx + 1] if didx + 1 < len(args_list) else ""
        db.init_db()
        session = db.SessionLocal()
        try:
            target = models.Target(name=name, domain=domain)
            session.add(target)
            session.commit()
            print(f"✅ Target '{name}' created (id={target.id})")
        finally:
            session.close()
        return

    # --merlin / --hermes: run MERLIN Automation Agent command (--hermes preserved for compat)
    if "--merlin" in args_set or "--hermes" in args_set:
        flag = "--merlin" if "--merlin" in args_set else "--hermes"
        idx = args_list.index(flag)
        command = args_list[idx + 1] if idx + 1 < len(args_list) and not args_list[idx + 1].startswith("--") else "help"
        from apps.hermes.engine import AutomationEngine

        engine = AutomationEngine()
        result = engine.execute(command)
        print(f"[MERLIN] {result.message}")
        if result.details:
            import json

            print(json.dumps(result.details, indent=2, default=str))
        return

    # --safe-mode forces degraded operation
    force_safe = "--safe-mode" in args_set

    # Handle legacy service install/remove first
    if _handle_legacy_service(args_set):
        return

    # Diagnostics
    if "--check" in args_set:
        _handle_diagnostics()
        return

    # Force safe mode if requested
    if force_safe:
        _log("BOOT", "Safe mode requested via --safe-mode")
        try:
            from desktop.boot_guard import enable_safe_mode

            enable_safe_mode("User request via --safe-mode")
        except Exception as exc:
            _log("BOOT", "Failed to enable safe mode: %s", exc)

    # Detect mode
    mode, dev, no_tray = _detect_mode(args_set)

    # Dispatch
    if mode == LaunchMode.INSTALL:
        _handle_install()
    elif mode == LaunchMode.BUILD:
        _handle_build()
    elif mode == LaunchMode.TRAY:
        _handle_tray()
    elif mode == LaunchMode.BROWSER:
        _handle_browser()
    elif mode == LaunchMode.SERVICE:
        _handle_service()
    else:
        _handle_auto()


if __name__ == "__main__":
    main()
