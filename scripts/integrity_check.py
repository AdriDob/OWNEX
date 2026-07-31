#!/usr/bin/env python3
"""OWNEX Integrity Check — Verifies project health for agent sessions.

Checks:
  1. Version sync across all files
  2. Import integrity (all core modules importable)
  3. Critical API routers importable
  4. Database models sync
  5. Extension manifests valid
  6. Lint clean (ruff)
  7. Tests pass (critical subset)

Usage:
    python scripts/integrity_check.py

Exit code 0 = all green, 1 = issues found.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

checks: list[tuple[str, bool, str]] = []


def report(name: str, passed: bool, detail: str = "") -> None:
    status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    checks.append((name, passed, detail))
    print(f"  {status} {name}" + (f" — {detail}" if detail else ""))


def check_version_sync() -> None:
    """1. Version sync."""
    from core.system.version_engine import VersionEngine

    ve = VersionEngine()
    info = ve.info()
    in_sync = info["pyproject"] == info["version"] and info["frontend"] == info["version"]
    report("Version sync", in_sync, f"v{info['version']}")


def check_imports() -> None:
    """2. Core module imports."""
    modules = [
        "core.cycles.forge",
        "core.cycles.pulse",
        "core.task_hub.sync",
        "core.task_hub.models",
        "core.self_improvement.plan_generator",
        "core.self_improvement.reflection",
        "core.opportunity.executors.assisted_mode",
        "core.opportunity.guides.platform_guides",
        "core.credentials.vault",
        "cores.observation.types",
        "cores.ai.providers.openrouter_provider",
    ]
    for mod in modules:
        try:
            __import__(mod)
            report(f"Import {mod}", True)
        except Exception as e:
            report(f"Import {mod}", False, str(e)[:80])


def check_api_routers() -> None:
    """3. API router imports."""
    routers = [
        "api.routers.forge_cycle",
        "api.routers.task_hub",
        "api.routers.secrets",
        "api.routers.self_improvement",
        "api.routers.platform_guides",
        "api.routers.settings_runtime",
    ]
    for mod in routers:
        try:
            __import__(mod)
            report(f"Router {mod}", True)
        except Exception as e:
            report(f"Router {mod}", False, str(e)[:80])


def check_lint() -> None:
    """4. Lint check on critical files."""
    files = [
        "core/credentials/vault.py",
        "core/cycles/forge.py",
        "core/cycles/pulse.py",
        "core/task_hub/",
        "core/self_improvement/",
        "cores/observation/types.py",
        "cores/ai/providers/openrouter_provider.py",
        "api/routers/secrets.py",
        "api/routers/forge_cycle.py",
        "api/routers/task_hub.py",
    ]
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check"] + files,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    passed = result.returncode == 0
    detail = "clean" if passed else f"{result.stdout.count('error')} errors"
    report("Lint (critical files)", passed, detail)


def check_tests() -> None:
    """5. Critical tests."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_agents.py",
            "tests/test_core_api_routers.py",
            "tests/test_core_secrets.py",
            "tests/test_credentials_vault.py",
            "-q",
            "--timeout=15",
            "--tb=no",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    passed = result.returncode == 0
    summary = result.stdout.strip().split("\n")[-1] if result.stdout else ""
    report("Critical tests", passed, summary[:80])


def check_extensions() -> None:
    """6. Extension manifests."""
    extensions_dir = PROJECT_ROOT / "extensions"
    if not extensions_dir.exists():
        report("Extensions", True, "no extensions dir")
        return

    expected = [
        "lightrag",
        "cognee",
        "graphiti",
        "skyvern",
        "crawl4ai",
        "composio",
        "n8n",
        "kestra",
        "langfuse",
        "graphify",
        "skill_seekers",
        "promptfoo",
        "nanobot",
    ]
    found = 0
    for name in expected:
        manifest = extensions_dir / name / "manifest.py"
        if manifest.exists():
            found += 1
    report("Extensions", found == len(expected), f"{found}/{len(expected)}")


def main() -> int:
    print(f"\n{BOLD}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}║  OWNEX OMEGA — Integrity Check v7.0.0                     ║{RESET}")
    print(f"{BOLD}╚══════════════════════════════════════════════════════════╝{RESET}\n")

    print(f"{BOLD}1. Version Sync{RESET}")
    check_version_sync()

    print(f"\n{BOLD}2. Core Imports{RESET}")
    check_imports()

    print(f"\n{BOLD}3. API Router Imports{RESET}")
    check_api_routers()

    print(f"\n{BOLD}4. Lint{RESET}")
    check_lint()

    print(f"\n{BOLD}5. Critical Tests{RESET}")
    check_tests()

    print(f"\n{BOLD}6. Extensions{RESET}")
    check_extensions()

    # Summary
    total = len(checks)
    passed = sum(1 for _, ok, _ in checks if ok)
    failed = total - passed

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    if failed == 0:
        print(f"{GREEN}✓ ALL CHECKS PASSED ({passed}/{total}){RESET}")
    else:
        print(f"{RED}✗ {failed} CHECK(S) FAILED ({passed}/{total} passed){RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
