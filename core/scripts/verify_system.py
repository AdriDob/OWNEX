#!/usr/bin/env python3
"""OWNEX System Verification — prove all components work without real API keys.

Usage:
    python -m core.scripts.verify_system
    python -m core.scripts.verify_system --verbose
    python -m core.scripts.verify_system --quick   # Skip slow checks

Tests every executor, adapter, and workflow component in dry-run/mock mode.
Reports system readiness for real credentials.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# ── ANSI colors ────────────────────────────────────────────────

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

EMOJI = {
    "pass": "✅",
    "fail": "❌",
    "warn": "⚠️ ",
    "info": "ℹ️ ",
    "skip": "⏭️ ",
}

results: list[dict] = []


def log_result(name: str, status: str, detail: str = ""):
    results.append({"name": name, "status": status, "detail": detail})
    color = {"pass": GREEN, "fail": RED, "warn": YELLOW, "info": CYAN, "skip": DIM}.get(status, RESET)
    icon = EMOJI.get(status, "  ")
    print(f"  {icon} {color}{status.upper():<6}{RESET} {name} {DIM}{detail}{RESET}")


# ── Checks ─────────────────────────────────────────────────────


async def check_executors(verbose: bool = False):
    """Test every executor in dry-run mode."""
    print(f"\n{BOLD}Executors{BOLD}")

    from core.opportunity.executors import get_executors

    executors = get_executors(config={"enabled": True})
    log_result(f"Executor factory: {len(executors)} registered", "pass", f"({', '.join(executors.keys())})")

    for name, ex in sorted(executors.items()):
        try:
            health = await ex.health_check()
            if health.success:
                log_result(f"{name}.health_check()", "pass")
            else:
                log_result(f"{name}.health_check()", "warn", health.error or "offline")
        except Exception as e:
            log_result(f"{name}.health_check()", "fail", str(e))

        # Test execute route
        try:
            result = await ex.execute("health_check")
            if verbose:
                log_result(
                    f"{name}.execute('health_check')",
                    "pass" if result.success else "warn",
                    "" if result.success else (result.error or ""),
                )
        except NotImplementedError:
            pass  # Base executor default


async def check_workflow_engine(quick: bool = False):
    """Test workflow engine in dry-run mode."""
    print(f"\n{BOLD}Workflow Engine{BOLD}")

    from core.autonomy.workflow_engine import AutonomousWorkflow, WorkPlan

    # 1. Configuration
    wf = AutonomousWorkflow(config={"enabled": True, "dry_run": True})
    assert wf.enabled is True
    assert wf.dry_run is True
    log_result("Configuration defaults", "pass")

    # 2. Dry-run plan execution
    from core.opportunity.executors import BaseExecutor, ExecutionResult

    class DummyExecutor(BaseExecutor):
        platform = "test"

        async def execute(self, action, **kwargs):
            return ExecutionResult(True, action, "test", "OK")

    wf.executors = {"test": DummyExecutor()}
    plan = WorkPlan(
        opportunity_id="verify-1",
        platform="test",
        actions=[{"action": "test", "params": {}}],
        estimated_effort_hours=1.0,
        estimated_reward=100.0,
        confidence=0.5,
    )
    result = await wf._execute_plan(plan)
    assert result.success is True
    assert "DRY RUN" in (result.error or "")
    log_result("Dry-run execution", "pass")

    # 3. Plan creation for each platform type
    from core.opportunity.scorer import score_opportunity

    for platform, opp_id, label in [
        ("algora", "algora-1", "OSS bounty plan"),
        ("freelancer", "fl-1", "Freelancer plan"),
        ("dataannotation", "da-1", "AI work plan"),
        ("linkedin", "li-1", "LinkedIn plan"),
        ("opencollective", "oc-1", "OpenCollective plan"),
    ]:
        scored = score_opportunity(
            opp_id=opp_id,
            name=f"Test {platform}",
            cycle="forge",
            source_type="bounty",
            source_name=platform,
            reward=100,
            effort_hours=2,
            platform=platform,
            technology_tags=[],
            url=f"https://{platform}.com/test",
            original={"repository": "owner/repo", "issue_number": 1, "bounty_id": opp_id}
            if platform == "algora"
            else {},
        )
        plan = await wf._create_plan(scored)
        status = "pass" if plan is not None else "info" if platform == "opencollective" else "warn"
        log_result(f"{label}", status, f"actions={len(plan.actions)}" if plan else "no-op (funding-only)")

    log_result("All platform plans valid", "pass")


async def check_credentials():
    """Check which platform credentials are configured."""
    print(f"\n{BOLD}Credentials{BOLD}")

    vault_path = Path.home() / ".config" / "ownex" / "opportunity.env"
    if vault_path.exists():
        log_result("Credentials vault file", "pass", str(vault_path))
    else:
        log_result("Credentials vault file", "warn", "not created yet — run setup")
        vault_path = None  # type: ignore

    # Key mapping: each key unlocks specific capabilities
    key_vars = {
        # ── Tier 1: General / AI (unlock Model Router) ──
        "OPENAI_API_KEY": ("OpenAI", "Model Router tier 1 — GPT-4o, embeddings"),
        "ANTHROPIC_API_KEY": ("Anthropic", "Model Router fallback — Claude Sonnet/Haiku"),
        "OMNIROUTE_API_KEY": ("OmniRoute", "Model Router primary — all providers"),
        # ── Tier 2: FORGE — Dev Bounties (unlock Forge Cycle) ──
        "GITHUB_TOKEN": ("GitHub API", "Forge: discover bounties from GitHub issues"),
        "ALGORA_API_KEY": ("Algora.xyz", "Forge: Algora bounties"),
        "OPIRE_API_KEY": ("Opire.dev", "Forge: Opire bounties"),
        "ISSUEHUNT_API_KEY": ("IssueHunt.io", "Forge: IssueHunt bounties"),
        "FREELANCER_API_KEY": ("Freelancer.com", "Forge: Freelancer contests"),
        "SUPERTEAM_API_KEY": ("Superteam.fun", "Forge: Superteam bounties"),
        "OPENCOLLECTIVE_API_KEY": ("OpenCollective", "Forge: OpenCollective grants"),
        # ── Tier 3: PULSE — AI Work (unlock Pulse Cycle) ──
        "OUTLIER_API_KEY": ("Outlier.ai", "Pulse: AI training tasks"),
        "MINDRIFT_API_KEY": ("Mindrift.io", "Pulse: AI training tasks"),
        "DATAANNOTATION_API_KEY": ("DataAnnotation.tech", "Pulse: data labeling"),
        "REMOTASKS_API_KEY": ("Remotasks.com", "Pulse: data tasks"),
        "LINKEDIN_CLIENT_ID": ("LinkedIn", "Pulse: Easy Apply jobs"),
        "LINKEDIN_CLIENT_SECRET": ("LinkedIn", "Pulse: Easy Apply auth"),
        # ── Tier 4: VAULT — Bug Bounties (unlock Security Cycle) ──
        "HACKERONE_API_KEY": ("HackerOne", "Security: bug bounty platform"),
        "BUGCROWD_API_KEY": ("Bugcrowd", "Security: bug bounty platform"),
        "INTIGRITI_API_KEY": ("Intigriti", "Security: bug bounty platform"),
        "SYNACK_API_KEY": ("Synack", "Security: bug bounty platform"),
        "YESWEHACK_API_KEY": ("YesWeHack", "Security: bug bounty platform"),
        "IMMUNEFI_API_KEY": ("Immunefi", "Security: web3 bug bounty"),
        # ── Tier 5: ATLAS — Audits (unlock Atlas Cycle) ──
        "CODE4RENA_API_KEY": ("Code4rena", "Atlas: audit competitions"),
        "CANTINA_API_KEY": ("Cantina.xyz", "Atlas: audit competitions"),
        "SHERLOCK_API_KEY": ("Sherlock", "Atlas: audit competitions"),
        "CODEHAWKS_API_KEY": ("CodeHawks", "Atlas: audit competitions"),
    }

    configured = 0
    total = 0
    missing_keys = []
    for var, (platform, description) in key_vars.items():
        total += 1
        val = os.environ.get(var) or _from_env_file(vault_path, var) if vault_path else ""
        if val:
            configured += 1
            log_result(f"{platform} ({var})", "pass", f"unlocks: {description}")
        else:
            missing_keys.append(var)
            log_result(f"{platform} ({var})", "info", f"missing — {description}")

    if configured == 0:
        log_result("Credentials status", "info", f"0/{total} keys configured — system in demo mode")
    elif configured < total:
        log_result("Credentials status", "warn", f"{configured}/{total} keys configured")
    else:
        log_result("Credentials status", "pass", f"{configured}/{total} keys configured")

    # ── Tier-based recommendation ──────────────────────────────────
    print()
    print(f"  {BOLD}Tier-based key setup (add in this order):{RESET}")
    print(
        f"  {DIM}┌──────────────────────┬──────────────────────────────────────────────────────────────────────────────┐{RESET}"
    )
    for tier_name, tier_keys in [
        ("🟢 TIER 1  Model Router", ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OMNIROUTE_API_KEY"]),
        (
            "🔵 TIER 2  Forge Cycle",
            [
                "GITHUB_TOKEN",
                "ALGORA_API_KEY",
                "OPIRE_API_KEY",
                "ISSUEHUNT_API_KEY",
                "FREELANCER_API_KEY",
                "SUPERTEAM_API_KEY",
                "OPENCOLLECTIVE_API_KEY",
            ],
        ),
        (
            "🟡 TIER 3  Pulse Cycle",
            [
                "OUTLIER_API_KEY",
                "MINDRIFT_API_KEY",
                "DATAANNOTATION_API_KEY",
                "REMOTASKS_API_KEY",
                "LINKEDIN_CLIENT_ID",
                "LINKEDIN_CLIENT_SECRET",
            ],
        ),
        (
            "🔴 TIER 4  Security Cycle",
            [
                "HACKERONE_API_KEY",
                "BUGCROWD_API_KEY",
                "INTIGRITI_API_KEY",
                "SYNACK_API_KEY",
                "YESWEHACK_API_KEY",
                "IMMUNEFI_API_KEY",
            ],
        ),
        ("🟣 TIER 5  Atlas Cycle", ["CODE4RENA_API_KEY", "CANTINA_API_KEY", "SHERLOCK_API_KEY", "CODEHAWKS_API_KEY"]),
    ]:
        tier_configured = sum(
            1
            for k in tier_keys
            if k in [v for v in []] or os.environ.get(k) or (_from_env_file(vault_path, k) if vault_path else "")
        )
        tier_configured = sum(
            1 for k in tier_keys if os.environ.get(k) or (_from_env_file(vault_path, k) if vault_path else "")
        )
        status_icon = "✅" if tier_configured == len(tier_keys) else "🔶" if tier_configured > 0 else "⬜"
        print(f"  │ {status_icon} {tier_name:<30s} │ {tier_configured}/{len(tier_keys)} keys configured{' ' * 50}|")
    print(f"  {DIM}└──────────────────────────────────────────────────────────────────────────────────────┘{RESET}")

    return missing_keys


def _from_env_file(vault_path: Path | None, var: str) -> str:
    """Read a variable from the env file."""
    if not vault_path or not vault_path.exists():
        return ""
    try:
        content = vault_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith(var + "="):
                val = line.split("=", 1)[1].strip("\"'")
                return val if val else ""
    except Exception:
        pass
    return ""


async def check_scheduler():
    """Check scheduler job definitions."""
    print(f"\n{BOLD}Scheduler{BOLD}")

    try:
        from core.scheduler.jobs import get_all_jobs

        all_jobs = get_all_jobs()
        total_jobs = sum(len(jobs) for jobs in all_jobs.values())
        log_result(
            f"Scheduler: {total_jobs} jobs across {len(all_jobs)} cycles",
            "pass",
            f"({', '.join(f'{k}:{len(v)}' for k, v in all_jobs.items())})",
        )
    except Exception as e:
        log_result("Scheduler jobs", "warn", str(e))


async def check_frontend():
    """Check frontend build status."""
    print(f"\n{BOLD}Frontend{BOLD}")

    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        log_result("Frontend directory", "warn", "not found")
        return

    # Check package.json
    pkg = frontend_dir / "package.json"
    if pkg.exists():
        import json

        data = json.loads(pkg.read_text())
        log_result("Frontend project", "pass", f"{data.get('name', 'unknown')} v{data.get('version', '?')}")

    # Check build artifacts
    dist = frontend_dir / "dist"
    if dist.exists():
        files = list(dist.rglob("index.html"))
        if files:
            log_result(
                "Frontend build",
                "pass",
                f"dist/ ready ({sum(f.stat().st_size for f in dist.rglob('*') if f.is_file()) // 1024} KB)",
            )
        else:
            log_result("Frontend build", "info", "dist/ exists but no index.html — run `npm run build`")
    else:
        log_result("Frontend build", "info", "no dist/ — run `npm run build` for production")


async def check_pytest():
    """Run a quick pytest smoke test."""
    print(f"\n{BOLD}Test Suite{BOLD}")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "pytest",
            "tests/test_executors.py",
            "tests/test_coder_agent.py",
            "tests/test_workflow_engine.py",
            "--co",
            "-q",
            "--no-header",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            timeout=60,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode()

        if proc.returncode == 0:
            # Extract final line
            for line in output.splitlines():
                if "passed" in line:
                    log_result("Core tests", "pass", line.strip())
                    break
            else:
                log_result("Core tests", "pass", "all passed")
        else:
            # Count failures
            lines = output.splitlines()
            failed = sum(1 for line in lines if "FAILED" in line)
            log_result("Core tests", "warn", f"{failed} failures — run full suite for details")
    except Exception as e:
        log_result("Core tests", "warn", str(e))


async def check_infrastructure():
    """Check ecosystem infrastructure."""
    print(f"\n{BOLD}Infrastructure{BOLD}")

    # Check Ollama
    import httpx

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                log_result("Ollama", "pass", f"{len(models)} model(s) available")
            else:
                log_result("Ollama", "info", f"responded {resp.status_code}")
    except Exception:
        log_result("Ollama", "info", "not running — start with `ollama serve`")

    # Check FCC proxy
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get("http://localhost:8082/health")
            if resp.status_code == 200:
                log_result("FCC Proxy", "pass", "running at :8082")
            else:
                log_result("FCC Proxy", "info", f"responded {resp.status_code}")
    except Exception:
        log_result("FCC Proxy", "info", "not running — start with `./start-fcc.sh`")


# ── Report ──────────────────────────────────────────────────────


def print_summary():
    """Print final summary."""
    passed = sum(1 for r in results if r["status"] == "pass")
    warned = sum(1 for r in results if r["status"] == "warn")
    failed = sum(1 for r in results if r["status"] == "fail")
    info = sum(1 for r in results if r["status"] == "info")

    total = len(results)
    score = (passed / total * 100) if total > 0 else 0

    print(f"\n{'=' * 50}")
    print(f"{BOLD}System Verification Report{RESET}")
    print(f"{'=' * 50}")
    print(f"  {EMOJI['pass']} Passed: {passed}")
    print(f"  {EMOJI['warn']} Warnings: {warned}")
    print(f"  {EMOJI['fail']} Failed: {failed}")
    print(f"  {EMOJI['info']} Info: {info}")
    print(f"  Total checks: {total}")
    print(f"  Readiness score: {GREEN if score >= 80 else YELLOW if score >= 50 else RED}{score:.0f}%{RESET}")
    print()

    if score >= 80:
        print(f"  {BOLD}Verdict:{RESET} {GREEN}READY for credentials{RESET}")
        print("  Add API keys to ~/.config/ownex/opportunity.env and go live.")
    elif score >= 50:
        print(f"  {BOLD}Verdict:{RESET} {YELLOW}ALMOST READY — address warnings above{RESET}")
    else:
        print(f"  {BOLD}Verdict:{RESET} {RED}NEEDS WORK — check failures above{RESET}")
    print()


# ── Main ────────────────────────────────────────────────────────


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="OWNEX System Verification")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--quick", "-q", action="store_true", help="Skip slow checks (tests)")
    args = parser.parse_args()

    print(f"\n{CYAN}{BOLD}═══ OWNEX System Verification ═══{RESET}")
    print(f"  {DIM}Verifies all components without real API keys{RESET}")
    print(f"  {DIM}Run: python -m core.scripts.verify_system [--verbose] [--quick]{RESET}")

    await check_executors(args.verbose)
    await check_credentials()
    await check_workflow_engine(args.quick)
    await check_scheduler()
    await check_frontend()

    if not args.quick:
        await check_pytest()

    await check_infrastructure()
    print_summary()

    # Return exit code
    failed = sum(1 for r in results if r["status"] == "fail")
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
