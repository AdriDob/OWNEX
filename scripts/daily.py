#!/usr/bin/env python3
"""OWNEX Daily Briefing — One command to start your day.

Usage:
    python scripts/daily.py           # Full briefing
    python scripts/daily.py --quick   # Just the essentials
    python scripts/daily.py --json    # Machine-readable
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ruff: noqa: E402 — the project root must be on sys.path before the
# local packages are importable (this file runs as a CLI script).
from cores.credentials.sync import get_missing_credentials  # noqa: E402
from cores.cycles.security import get_security_cycle  # noqa: E402
from cores.daily_tasks import get_daily_task_board  # noqa: E402
from cores.health.checks import register_default_checks  # noqa: E402
from cores.health.engine import HealthCenter  # noqa: E402
from cores.identity_vault import get_identity_vault  # noqa: E402
from database.db import SessionLocal  # noqa: E402
from database.models import Finding, Report, Target, Verdict  # noqa: E402


def format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def get_health_status() -> dict:
    hc = HealthCenter()
    register_default_checks(hc)
    result = hc.run_all()
    return {
        "status": result.status,
        "score": result.score,
        "checks": result.checks,
    }


def get_security_cycle_status() -> dict:
    security = get_security_cycle()
    cycle = security.ensure_cycle()
    return {
        "id": cycle.id,
        "status": cycle.status,
        "next_action": cycle.config_dict.get("next_action", "unknown"),
    }


def get_db_stats() -> dict:
    session = SessionLocal()
    try:
        return {
            "targets_active": session.query(Target).filter(Target.active.is_(True)).count(),
            "targets_total": session.query(Target).count(),
            "findings_confirmed": session.query(Finding).filter(Finding.status == "confirmed").count(),
            "findings_total": session.query(Finding).count(),
            "reports_total": session.query(Report).count(),
            "reports_draft": session.query(Report).filter(Report.status == "draft").count(),
            "verdicts_total": session.query(Verdict).count(),
        }
    finally:
        session.close()


def get_daily_tasks() -> dict:
    board = get_daily_task_board()
    tasks = board.get_tasks(force_refresh=True)
    pending = [t for t in tasks.get("tasks", []) if not t.get("done")]
    done = [t for t in tasks.get("tasks", []) if t.get("done")]
    return {
        "day": tasks.get("day", 0),
        "total": tasks.get("total", 0),
        "done": len(done),
        "pending": len(pending),
        "pending_items": [t.get("title", "") for t in pending[:5]],
    }


def get_credentials_status() -> dict:
    missing = get_missing_credentials()
    vault = get_identity_vault()
    accounts = vault.list_accounts()
    connected = sum(1 for a in accounts if a.get("session_state") == "connected")
    return {
        "missing_count": len(missing),
        "missing_by_section": {},
        "vault_accounts": len(accounts),
        "vault_connected": connected,
    }


def get_investment_status() -> dict:
    try:
        from cores.investment.manager import get_investment_manager

        snap = get_investment_manager().snapshot()
        return {
            "total_capital": getattr(snap, "total_capital_usd", 0),
            "deployed": getattr(snap, "deployed", 0),
            "strategies": len(getattr(snap, "strategies", [])),
        }
    except Exception:
        return {"error": "unavailable"}


def get_scheduler_jobs() -> dict:
    try:
        from cores.scheduler.jobs import get_all_jobs

        all_jobs = get_all_jobs()
        return {
            "total_jobs": sum(len(j) for j in all_jobs.values()),
            "cycles": len(all_jobs),
            "investment_jobs": len(all_jobs.get("investment", [])),
            "security_jobs": len(all_jobs.get("security", [])),
        }
    except Exception:
        return {"error": "unavailable"}


def print_briefing(data: dict, quick: bool = False) -> None:
    """Pretty print the daily briefing."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    print(f"\n{'=' * 50}")
    print(f"  OWNEX DAILY BRIEFING  —  {now}")
    print(f"{'=' * 50}")

    # Health
    h = data["health"]
    status_icon = "🟢" if h["status"] == "green" else "🟡" if h["status"] == "yellow" else "🔴"
    print(f"\n{status_icon} SYSTEM HEALTH: {h['status'].upper()} ({h['score']:.0%})")
    if not quick:
        for name, ok in h["checks"].items():
            icon = "✓" if ok else "✗"
            print(f"  {icon} {name}")

    # Security Cycle
    sc = data["security_cycle"]
    cycle_icon = "🔄" if sc["status"] == "running" else "⏸️" if sc["status"] == "paused" else "✅"
    print(f"\n{cycle_icon} SECURITY CYCLE #{sc['id']}: {sc['status'].upper()} → {sc['next_action']}")

    # DB Stats
    db = data["db"]
    print("\n📊 DATABASE:")
    print(f"  🎯 Targets: {db['targets_active']} active / {db['targets_total']} total")
    print(f"  🔍 Findings: {db['findings_confirmed']} confirmed / {db['findings_total']} total")
    print(f"  📄 Reports: {db['reports_draft']} draft / {db['reports_total']} total")

    # Daily Tasks
    dt = data["daily_tasks"]
    print(f"\n📋 DAILY TASKS (Day {dt['day']}): {dt['done']}/{dt['total']} done")
    if dt["pending_items"]:
        for item in dt["pending_items"]:
            print(f"  ⬜ {item}")
    elif not quick:
        print("  ✅ All caught up!")

    # Credentials
    cred = data["credentials"]
    cred_icon = "🔑" if cred["missing_count"] == 0 else "⚠️"
    print(
        f"\n{cred_icon} CREDENTIALS: {cred['missing_count']} missing, {cred['vault_connected']}/{cred['vault_accounts']} connected"
    )
    if cred["missing_count"] > 0 and not quick:
        print(
            '  Run: python -c "from cores.credentials.sync import prompt_missing_credentials; prompt_missing_credentials()"'
        )

    # Investment
    inv = data["investment"]
    if "error" not in inv:
        print(
            f"\n💰 INVESTMENT: ${inv['deployed']:,.0f} deployed / ${inv['total_capital']:,.0f} total ({inv['strategies']} strategies)"
        )

    # Scheduler
    sched = data["scheduler"]
    if "error" not in sched:
        print(f"\n⚙️  SCHEDULER: {sched['total_jobs']} jobs in {sched['cycles']} cycles")

    # Quick actions
    if not quick:
        print(f"\n{'=' * 50}")
        print("  QUICK ACTIONS:")
        print("  make work         # Full startup check")
        print("  make test-fast    # Quick test suite")
        print("  make status       # Health check")
        print("  python scripts/daily.py --quick  # This briefing")
        print("  python -m api.scheduler &       # Start scheduler")

    print(f"\n{'=' * 50}\n")


def main():
    parser = argparse.ArgumentParser(description="OWNEX Daily Briefing")
    parser.add_argument("--quick", "-q", action="store_true", help="Essential info only")
    parser.add_argument("--json", "-j", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    # Gather all data
    data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "health": get_health_status(),
        "security_cycle": get_security_cycle_status(),
        "db": get_db_stats(),
        "daily_tasks": get_daily_tasks(),
        "credentials": get_credentials_status(),
        "investment": get_investment_status(),
        "scheduler": get_scheduler_jobs(),
    }

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_briefing(data, quick=args.quick)


if __name__ == "__main__":
    main()
