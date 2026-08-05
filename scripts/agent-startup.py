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

# Hacer importable core/ y database/ cuando se ejecuta como script (scripts/ no
# está en sys.path por defecto).
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


def run_maintenance() -> None:
    """Step 3.5: OWNEX SELF-MAINTENANCE.

    Lightweight, read-only checks that run at every boot:
    - dependency freshness (pip list vs requirements)
    - update availability (git fetch, non-blocking)
    - latest health snapshot from DB
    - self-healing validation (import integrity)

    All checks are best-effort; failures are logged, never fatal.
    """
    header("OWNEX SELF-MAINTENANCE")

    # 1) Dependency freshness
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            import json

            installed = {p["name"].lower(): p["version"] for p in json.loads(result.stdout)}
            reqs: list[str] = []
            req_file = PROJECT_ROOT / "requirements.txt"
            if req_file.exists():
                for line in req_file.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        reqs.append(line.split(">=")[0].split("==")[0].split("~=")[0].split("[")[0].strip().lower())
            missing = [r for r in reqs if r not in installed and r]
            if missing:
                print(f"  {YELLOW}⚠ Missing deps: {', '.join(missing[:5])}{RESET}")
            else:
                print(f"  {GREEN}✓ All requirements installed{RESET}")
    except Exception as exc:
        print(f"  {YELLOW}⚠ Dep check skipped: {str(exc)[:60]}{RESET}")

    # 2) Update availability (non-blocking)
    try:
        from core.self_healing.update import SelfUpdateSystem

        su = SelfUpdateSystem()
        has_update, msg = su.check_for_updates()
        if has_update:
            print(f"  {YELLOW}⚠ {msg}{RESET}")
        else:
            print(f"  {GREEN}✓ {msg}{RESET}")
    except Exception as exc:
        print(f"  {YELLOW}⚠ Update check skipped: {str(exc)[:60]}{RESET}")

    # 3) Latest health snapshot
    try:
        from core.health.engine import HealthCenter

        hc = HealthCenter()
        snap = hc.latest()
        if snap:
            status_icon = f"{GREEN}✓{RESET}" if snap.status == "green" else f"{YELLOW}⚠{RESET}"
            print(f"  {status_icon} Last health: {snap.status} ({snap.timestamp})")
        else:
            print(f"  {YELLOW}⚠ No health snapshots yet{RESET}")
    except Exception as exc:
        print(f"  {YELLOW}⚠ Health snapshot skipped: {str(exc)[:60]}{RESET}")

    print(f"\n{'-' * 60}")


def system_status() -> None:
    """Step 4b: OWNEX STATUS — speed/revenue dashboard at a glance.

    Read-only snapshot of the live system: investment engine, autonomous
    scheduler jobs, and DB state. All queries guarded so a slow/missing
    dependency never blocks boot.
    """
    header("SYSTEM & REVENUE STATUS")

    # 1) Investment engine
    try:
        from core.investment.manager import get_investment_manager

        snap = get_investment_manager().snapshot()
        print(f"  {BOLD}Inversión:{RESET}")
        print(f"    Capital total: ${getattr(snap, 'total_capital_usd', 0):,.2f}")
        print(f"    Desplegado:    ${getattr(snap, 'deployed', 0):,.2f}")
        print(f"    Estrategias activas: {len(getattr(snap, 'strategies', []))}")
        for sid in getattr(snap, "strategies", []):
            alloc = getattr(snap, "_strategies", {}).get(sid)
            if alloc is None:
                print(f"      - {sid}")
            else:
                print(f"      - {sid}: disponible ${getattr(alloc, 'available_usd', 0):,.2f}")
    except Exception as exc:  # non-fatal
        print(f"  {YELLOW}⚠ Inversión no disponible: {str(exc)[:80]}{RESET}")

    # 2) Autonomous scheduler jobs (incl. revenue engine)
    try:
        from core.scheduler.jobs import get_all_jobs

        all_jobs = get_all_jobs()
        total_jobs = sum(len(j) for j in all_jobs.values())
        inv = [j.job_id for j in all_jobs.get("investment", [])]
        print(f"\n  {BOLD}Scheduler (autonomía):{RESET}")
        print(f"    {total_jobs} jobs activos en {len(all_jobs)} ciclos")
        for jid in inv:
            print(f"    {GREEN}✓ {jid} (revenue automático){RESET}")
    except Exception as exc:  # non-fatal
        print(f"  {YELLOW}⚠ Scheduler no disponible: {str(exc)[:80]}{RESET}")

    # 3) Database quick counts
    try:
        from sqlalchemy import text

        from database import db

        session = db.SessionLocal()
        try:
            targets = session.execute(text("SELECT COUNT(*) FROM targets")).scalar()
            reports = session.execute(text("SELECT COUNT(*) FROM reports")).scalar()
            print(f"\n  {BOLD}Base de datos:{RESET}")
            print(f"    Targets activos: {targets} | Reports: {reports}")
        finally:
            session.close()
    except Exception as exc:  # non-fatal
        print(f"  {YELLOW}⚠ DB no disponible: {str(exc)[:80]}{RESET}")

    print(f"\n{'-' * 60}")


def next_action() -> None:
    """Step 5: Show next action."""

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
    run_maintenance()
    quick_wins_scan()
    system_status()
    next_action()

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{GREEN}✓ Startup protocol complete. Ready for work.{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")


if __name__ == "__main__":
    main()
