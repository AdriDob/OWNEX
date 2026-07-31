#!/usr/bin/env python3
"""OWNEX Agent Startup — "Ponte a trabajar" protocol.

Ejecuta la secuencia de arranque obligatoria para cualquier agente:
  1. Version check
  2. State snapshot (leer .ai/)
  3. Health check (lint + tests)
  4. Quick wins scan
  5. Next action

Usage:
    python scripts/agent-startup.py [--full-tests] [--no-tests]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_DIR = PROJECT_ROOT / ".ai"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def header(title: str) -> None:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")


def check_version() -> bool:
    """Step 1: Version check."""
    header("STEP 1: Version Check")
    result = subprocess.run(
        [sys.executable, "-m", "core.system.version_engine", "info"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"{RED}  ERROR: {result.stderr.strip()}{RESET}")
        return False

    lines = result.stdout.strip().split("\n")
    for line in lines:
        print(f"  {line}")

    # Check sync
    sync_result = subprocess.run(
        [sys.executable, "-m", "core.system.version_engine", "sync"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if "All files already in sync" in sync_result.stdout:
        print(f"  {GREEN}✓ All files in sync{RESET}")
        return True
    else:
        print(f"  {YELLOW}⚠ Version mismatch detected — running sync{RESET}")
        print(f"  {sync_result.stdout.strip()}")
        return True


def read_state_summary() -> None:
    """Step 2: State snapshot."""
    header("STEP 2: State Snapshot")

    checkpoint = AI_DIR / "SESSION_CHECKPOINT.md"
    if checkpoint.exists():
        content = checkpoint.read_text(encoding="utf-8")
        last_session = content.split("## Última Sesión")[1].split("##")[0] if "## Última Sesión" in content else ""
        if last_session:
            print(f"{BOLD}Última sesión:{RESET}")
            for line in last_session.strip().split("\n")[:10]:
                print(f"  {line}")

    task_queue = AI_DIR / "TASK_QUEUE.md"
    if task_queue.exists():
        content = task_queue.read_text(encoding="utf-8")
        active_section = content.split("TAREAS ACTIVAS")[1].split("---")[0] if "TAREAS ACTIVAS" in content else ""
        if active_section:
            print(f"\n{BOLD}Tareas activas:{RESET}")
            for line in active_section.strip().split("\n"):
                if line.strip().startswith("|"):
                    print(f"  {line.strip()}")

    current_state = AI_DIR / "CURRENT_STATE.md"
    if current_state.exists():
        content = current_state.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        print(f"\n{BOLD}Current State (primeras líneas):{RESET}")
        for line in lines[:5]:
            print(f"  {line}")


def health_check(run_tests: bool = True) -> bool:
    """Step 3: Health check."""
    header("STEP 3: Health Check")

    # Lint
    print(f"{BOLD}  Lint (ruff):{RESET}")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "core/", "api/", "cores/"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0:
        print(f"    {GREEN}✓ Ruff clean{RESET}")
    else:
        errors = result.stdout.strip().split("\n")
        len([e for e in errors if "Found" in e or "error" in e.lower()])
        print(f"    {YELLOW}⚠ {len(errors)} lint issues{RESET}")
        for e in errors[-3:]:
            print(f"    {e}")

    # Tests
    if run_tests:
        print(f"\n  {BOLD}Tests (pytest):{RESET}")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-x", "-q", "--timeout=15", "--tb=no"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print(f"    {GREEN}✓ All tests pass{RESET}")
        else:
            lines = result.stdout.strip().split("\n")
            print(f"    {RED}✗ Tests failing{RESET}")
            for line in lines[-3:]:
                print(f"    {line}")

    return True


def quick_wins_scan() -> None:
    """Step 4: Quick wins scan."""
    header("STEP 4: Quick Wins Scan")

    # Check for new opportunities
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from cores.opportunity.auto_scanner import run_scan; r = run_scan(); print(f'Opportunities: {r.opportunities_found}, Qualifying: {r.qualifying}')",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print(f"  {result.stdout.strip()}")
        else:
            print(f"  {YELLOW}⚠ Scan unavailable: {result.stderr.strip()[:100]}{RESET}")
    except Exception as e:
        print(f"  {YELLOW}⚠ Scan error: {e}{RESET}")


def next_action() -> None:
    """Step 5: Show next action."""
    header("STEP 5: Next Action")

    task_queue = AI_DIR / "TASK_QUEUE.md"
    if task_queue.exists():
        content = task_queue.read_text(encoding="utf-8")
        active_section = content.split("TAREAS ACTIVAS")[1].split("---")[0] if "TAREAS ACTIVAS" in content else ""
        if active_section:
            print(f"{BOLD}Prioridad máxima:{RESET}")
            for line in active_section.strip().split("\n"):
                if "Pendiente" in line or "🔄" in line:
                    print(f"  {YELLOW}{line.strip()}{RESET}")

    print(f"\n{BOLD}Comando de inicio:{RESET}")
    print(f"  {GREEN}make work{RESET}  —  Re-ejecuta este protocolo")
    print(f"  {GREEN}make lint{RESET}    —  Solo lint")
    print(f"  {GREEN}make test{RESET}    —  Solo tests")
    print(f"  {GREEN}make status{RESET}  —  Health check completo")


def main() -> None:
    run_tests = "--full-tests" in sys.argv
    skip_tests = "--no-tests" in sys.argv

    print(f"\n{BOLD}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}║  OWNEX OMEGA — Agent Startup Protocol v7.0.0             ║{RESET}")
    print(f"{BOLD}╚══════════════════════════════════════════════════════════╝{RESET}")

    check_version()
    read_state_summary()
    health_check(run_tests=run_tests and not skip_tests)
    quick_wins_scan()
    next_action()

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{GREEN}✓ Startup protocol complete. Ready for work.{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")


if __name__ == "__main__":
    main()
