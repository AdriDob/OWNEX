#!/usr/bin/env python3
"""OWNEX First-Run Wizard — Interactive setup for new users."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_step(num: int, total: int, title: str) -> None:
    print(f"\n[{num}/{total}] {title}")
    print("-" * 40)


def ask_yes_no(prompt: str, default: bool = True, non_interactive: bool = False) -> bool:
    if non_interactive:
        return default
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        resp = input(prompt + suffix).strip().lower()
        if not resp:
            return default
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("Please answer y or n.")


def ask_input(prompt: str, default: str = "", non_interactive: bool = False) -> str:
    if non_interactive:
        return default
    suffix = f" [{default}]: " if default else ": "
    resp = input(prompt + suffix).strip()
    return resp or default


def run_command(cmd: str) -> bool:
    import subprocess

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Failed: {result.stderr.strip()}")
        return False
    print("  ✓ Done")
    return True


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="OWNEX First-Run Wizard")
    parser.add_argument("--non-interactive", action="store_true", help="Run without prompts (use defaults)")
    args = parser.parse_args()
    non_interactive = args.non_interactive or not sys.stdin.isatty()

    print_header("OWNEX FIRST-RUN WIZARD")
    print("Welcome! This will set up OWNEX for daily use.")
    print("Estimated time: 5-10 minutes\n")

    steps = [
        ("Environment", "Check Python, venv, and dependencies"),
        ("Database", "Initialize databases"),
        ("Credentials", "Configure API keys"),
        ("Scheduler", "Start background jobs"),
        ("Verification", "Run health checks"),
    ]

    # Step 1: Environment
    print_step(1, len(steps), steps[0][0])
    print(steps[0][1])

    if not Path(".venv").exists():
        if ask_yes_no("Virtual environment not found. Create one now?", True, non_interactive):
            run_command("make venv")
        else:
            print("  ⚠ Skipping - you'll need to run 'make venv' manually")
    else:
        print("  ✓ Virtual environment exists")

    # Step 2: Database
    print_step(2, len(steps), steps[1][0])
    print(steps[1][1])
    run_command(
        "python -c 'from database.db import SessionLocal; from database.models import Base; from database.db import engine; Base.metadata.create_all(engine); print(\"  ✓ Tables created\")'"
    )

    # Step 3: Credentials
    print_step(3, len(steps), steps[2][0])
    print(steps[2][1])
    print("  You'll need API keys for the platforms you want to use.")
    print("  We'll open the Settings UI where you can enter them.")

    if ask_yes_no("Open Settings UI in browser now?", True, non_interactive):
        # Start API server in background if not running
        import subprocess
        import time
        import webbrowser

        subprocess.Popen([sys.executable, "-m", "api.main"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        webbrowser.open("http://localhost:8000/settings")
        print("  ✓ Opened http://localhost:8000/settings")
        print("  Go to the 'API Keys' tab and enter your keys.")
        print("  Key priorities:")
        print("    1. GITHUB_TOKEN (unlocks dev bounties)")
        print("    2. HACKERONE_API_KEY, BUGCROWD_API_KEY, INTIGRITI_API_KEY (bug bounty)")
        print("    3. Payment method (Wise/PayPal) for payouts")

    # Step 4: Scheduler
    print_step(4, len(steps), steps[3][0])
    print(steps[3][1])
    if ask_yes_no(
        "Start scheduler now? (runs background jobs: security scans, investment scans, etc.)", True, non_interactive
    ):
        print("  Starting scheduler in background...")
        import subprocess

        subprocess.Popen([sys.executable, "-m", "api.scheduler"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("  ✓ Scheduler started (run 'make scheduler-logs' to see output)")

    # Step 5: Verification
    print_step(5, len(steps), steps[4][0])
    print(steps[4][1])
    print("  Running health check...")
    from scripts.daily import get_db_stats, get_health_status, get_security_cycle_status

    health = get_health_status()
    print(f"  System Health: {health['status'].upper()} ({health['score']:.0%})")
    cycle = get_security_cycle_status()
    print(f"  Security Cycle: {cycle['status'].upper()}")
    db = get_db_stats()
    print(f"  Targets: {db['targets_active']} active, Findings: {db['findings_confirmed']} confirmed")

    # Summary
    print_header("SETUP COMPLETE!")
    print("✓ OWNEX is ready for daily use")
    print("\nNext steps:")
    print("  1. Add credentials in Settings UI (if not done)")
    print("  2. Run 'make daily' each morning for your briefing")
    print("  3. Run 'make security-run DOMAIN=target.com' to scan a target")
    print("  4. Check 'make status' anytime for system health")
    print("\nQuick commands:")
    print("  make daily          # Full morning briefing")
    print("  make daily-quick    # Essentials only")
    print("  make watch          # Live briefing every 5 min")
    print("  make status         # Full health check")
    print("  make help           # All available commands")

    return 0


if __name__ == "__main__":
    sys.exit(main())
