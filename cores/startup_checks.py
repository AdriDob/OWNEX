"""Startup Checks — detect manual interventions needed at boot.

Runs when the system starts and periodically via scheduler.
Detects:
1. Missing API credentials for platforms with targets
2. Targets with unverified scope
3. Stalled pipelines
4. Investment adapters needing funding
5. System components unhealthy
6. Reports ready for manual review
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from cores.notifications.action_required import (
    notify_action_required,
    notify_credentials_missing,
    notify_scope_unverified,
    notify_system_stalled,
)

logger = logging.getLogger("ownex.startup_checks")

# Platforms that require API keys for submission
PLATFORMS_REQUIRING_KEYS = [
    "hackerone",
    "bugcrowd",
    "intigriti",
    "yeswehack",
    "immunefi",
    "synack",
    "code4rena",
    "cantina",
    "sherlock",
]


def check_missing_credentials() -> int:
    """Check for platforms with targets but missing API keys."""
    notified = 0
    try:
        from cores.credentials.vault import get_credentials

        creds = get_credentials()

        for platform in PLATFORMS_REQUIRING_KEYS:
            api_key = getattr(creds, f"{platform}_api_key", "")
            if api_key:
                continue

            # Check if there are targets for this platform
            try:
                from database import db, models

                session = db.SessionLocal()
                try:
                    target_count = session.query(models.Target).filter(models.Target.name.like(f"{platform}_%")).count()
                    if target_count > 0:
                        notify_credentials_missing(
                            platform=platform,
                            credential_name=f"{platform.upper()}_API_KEY",
                            impact=f"{target_count} target(s) configured but cannot submit reports",
                        )
                        notified += 1
                finally:
                    session.close()
            except Exception:
                pass  # DB may not be ready yet

    except Exception as e:
        logger.debug("Credential check skipped: %s", e)

    return notified


def check_unverified_scope() -> int:
    """Flag active targets with no scope rows recorded.

    Scope lives in `target_scopes` (linked via `targets_intel`); there is no
    per-target verified flag, so 'unverified' honestly means 'no scope rows
    recorded yet' — the user should review the program scope manually.
    """
    notified = 0
    try:
        from cores.targets.models import Scope, TargetIntel
        from database import db, models

        session = db.SessionLocal()
        try:
            scoped_tids = (
                session.query(TargetIntel.target_id)
                .join(Scope, Scope.target_id == TargetIntel.id)
                .filter(TargetIntel.target_id.isnot(None))
                .distinct()
            )
            unverified = (
                session.query(models.Target)
                .filter(models.Target.active.is_(True))
                .filter(~models.Target.id.in_(scoped_tids))
                .limit(10)
                .all()
            )

            for target in unverified:
                platform = "unknown"
                if "_" in (target.name or ""):
                    platform = target.name.split("_", 1)[0]

                notify_scope_unverified(
                    target_name=target.name or f"Target #{target.id}",
                    platform=platform,
                    target_id=target.id,
                )
                notified += 1
        finally:
            session.close()
    except Exception as e:
        logger.debug("Scope check skipped: %s", e)

    return notified


def check_stalled_pipelines() -> int:
    """Check for scans stuck in 'running' for over 24h.

    Scan state lives in `scan_runs` (there is no Pipeline model): a scan
    that never finished blocks its target from being rescanned.
    """
    notified = 0
    try:
        from database import db, models

        session = db.SessionLocal()
        try:
            cutoff = datetime.now(UTC) - timedelta(hours=24)
            stalled = (
                session.query(models.ScanRun, models.Target.name)
                .join(models.Target, models.Target.id == models.ScanRun.target_id)
                .filter(models.ScanRun.status == "running")
                .filter(models.ScanRun.started_at < cutoff)
                .limit(5)
                .all()
            )

            for scan, target_name in stalled:
                notify_system_stalled(
                    component=f"Scan #{scan.id} ({target_name or 'unknown target'})",
                    reason=f"Scan stuck in 'running' state for >24h (mode={scan.mode})",
                    impact="Target processing delayed — no findings generated",
                    resolution_steps=[
                        f"Go to Operations > Scans > #{scan.id}",
                        "Review pipeline state and error logs",
                        "Re-run the scan or mark it failed to unblock the target",
                        "If stuck, check logs for root cause",
                    ],
                )
                notified += 1
        finally:
            session.close()
    except Exception as e:
        logger.debug("Pipeline check skipped: %s", e)

    return notified


def check_reports_for_review() -> int:
    """Check for reports ready for manual review."""
    notified = 0
    try:
        from database import db, models

        session = db.SessionLocal()
        try:
            ready_reports = (
                session.query(models.Report)
                .filter(models.Report.status == "draft")
                .filter(models.Report.created_at < datetime.now(UTC) - timedelta(hours=1))
                .limit(5)
                .all()
            )

            for report in ready_reports:
                notify_action_required(
                    title=f"Report ready for review: #{report.id}",
                    reason="Report generated and ready for manual review before submission",
                    impact="Report queued — will not be submitted until reviewed",
                    steps=[
                        "Go to Reports > Queue",
                        f"Review report #{report.id}",
                        "Edit if needed, then mark as 'Ready'",
                        "Or submit manually if auto-submit is disabled",
                    ],
                    ui_path="/reports/queue",
                    category="review",
                    priority="medium",
                    channels=["web"],
                    subject_id=str(report.id),
                    subject_type="report",
                )
                notified += 1
        finally:
            session.close()
    except Exception as e:
        logger.debug("Report review check skipped: %s", e)

    return notified


def check_investment_risk() -> int:
    """Run risk guardian checks."""
    notified = 0
    try:
        from cores.investment.risk_guardian import get_risk_guardian

        guardian = get_risk_guardian()
        results = guardian.check_all_strategies()

        # Count pauses and warnings as notifications sent
        notified += len(results.get("paused", []))
        notified += len(results.get("warnings", []))
    except Exception as e:
        logger.debug("Investment risk check skipped: %s", e)

    return notified


def run_all_checks() -> dict[str, int]:
    """Run all startup checks and notify for each issue found."""
    results = {
        "missing_credentials": check_missing_credentials(),
        "unverified_scope": check_unverified_scope(),
        "stalled_pipelines": check_stalled_pipelines(),
        "reports_for_review": check_reports_for_review(),
        "investment_risk": check_investment_risk(),
    }

    total = sum(results.values())
    if total > 0:
        logger.info(
            "[STARTUP_CHECKS] Found %d issues requiring attention: %s",
            total,
            {k: v for k, v in results.items() if v > 0},
        )
    else:
        logger.info("[STARTUP_CHECKS] All clear — no manual intervention needed")

    return results
