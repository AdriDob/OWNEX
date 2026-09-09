"""Execution → Revenue bridge.

Closes the automated-execution loop honestly:
WorkBank prepares → AutoSubmitEngine / DevBountyPipeline executes →
this bridge records → RevenueTracker tracks.

Rules (Economic Rule §39, enforced by tests):
- SUBMITTED → REVIEWING (pending, NOT cash).
- CONFIRMED → ACCEPTED (platform accepted, still NOT cash).
- FAILED / DLQ / error → FAILED (documented loss).
- NEVER transitions to PAID here. PAID is only reachable via real
  payment confirmation (platform webhook payout_received or manual verify).
- Idempotent: re-recording the same execution is a no-op status refresh.

Callers MUST guard with try/except: revenue recording never breaks delivery.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger("ownex.revenue.execution_bridge")

# Single source of truth: WorkPlatform key -> PaymentPlatform.
# Freelance (Workana) is an OPTIONAL commercial channel, scored by the
# same engine — it maps to DEV_BOUNTY like any other dev-work payout.
WORK_PLATFORM_TO_PAYMENT: dict[str, str] = {
    "hackerone": "bug_bounty",
    "bugcrowd": "bug_bounty",
    "intigriti": "bug_bounty",
    "yeswehack": "bug_bounty",
    "synack": "bug_bounty",
    "immunefi": "bug_bounty",
    "code4rena": "bug_bounty",
    "opire": "dev_bounty",
    "issuehunt": "dev_bounty",
    "algora": "dev_bounty",
    "opencollective": "dev_bounty",
    "workana": "dev_bounty",
    "fiverr": "dev_bounty",
    "github": "dev_bounty",
    "superteam": "dev_bounty",
    "outlier": "data_annotation",
    "mindrift": "data_annotation",
    "linkedin": "dev_bounty",
    "opyre_microtask": "data_annotation",
    "company_website": "dev_bounty",
}


def _resolve_payment_platform(platform_key: str) -> Any:
    from cores.revenue_tracker.revenue_tracker import PaymentPlatform

    mapped = WORK_PLATFORM_TO_PAYMENT.get((platform_key or "").strip().lower(), "dev_bounty")
    try:
        return PaymentPlatform(mapped)
    except ValueError:
        return PaymentPlatform.DEV_BOUNTY


def resolve_payment_platform(platform_key: str) -> Any:
    """Public resolver: WorkPlatform key -> PaymentPlatform (SSOT map above)."""
    return _resolve_payment_platform(platform_key)


def _get_or_create_opp(
    tracker: Any,
    opp_id: str,
    platform_key: str,
    title: str,
    reward: float,
    url: str,
    source: str,
    extra_tracking: dict[str, Any] | None = None,
) -> Any:
    """Return existing opportunity or create it in PENDING/expected."""
    from cores.revenue_tracker.revenue_tracker import PaymentStatus, RevenueOpportunity

    existing = tracker.opportunities.get(opp_id)
    if existing is not None:
        return existing
    now = datetime.now(UTC)
    opp = RevenueOpportunity(
        id=opp_id,
        platform=_resolve_payment_platform(platform_key),
        title=title or opp_id,
        description=f"Automated execution via {source} on {platform_key}.",
        amount=Decimal(str(reward or 0)),
        currency="USD",
        status=PaymentStatus.PENDING,
        deadline=None,
        provider_info={"source": source, "platform_key": platform_key, "url": url or ""},
        tracking_data={"source": source, **(extra_tracking or {})},
        created_at=now,
        updated_at=now,
        barriers=[],
        difficulty="medium",
        success_rate=0.5,
        time_estimate="",
        tags=[source, platform_key],
        skills_required=[],
        url=url or "",
        revenue_state="expected",
        revenue_state_history=[{"state": "expected", "at": now.isoformat()}],
    )
    tracker.create_opportunity(opp)
    return opp


def record_submission_outcome(record: Any, opportunity: dict[str, Any] | None = None) -> str | None:
    """Record an AutoSubmitEngine SubmissionRecord in the RevenueTracker.

    Returns the revenue opportunity id, or None when recording is skipped
    (unknown/transient submission status — NOT an error).
    """
    from cores.revenue_tracker.revenue_tracker import PaymentStatus, get_revenue_tracker

    status = str(getattr(getattr(record, "status", ""), "value", getattr(record, "status", "")) or "").lower()
    opp_data = opportunity or (getattr(record, "metadata", {}) or {}).get("opportunity", {}) or {}
    platform_key = str(getattr(record, "platform", "") or "").strip().lower()
    reward = float(opp_data.get("reward", opp_data.get("payment", opp_data.get("amount", 0.0))) or 0.0)
    title = str(opp_data.get("title", "") or getattr(record, "opportunity_title", "") or record.opportunity_id)
    url = str(opp_data.get("url", "") or "")

    tracker = get_revenue_tracker()
    opp_id = f"sub_{getattr(record, 'id', 'unknown')}"
    _get_or_create_opp(
        tracker,
        opp_id,
        platform_key,
        title,
        reward,
        url,
        source="auto_submit",
        extra_tracking={
            "submission_id": getattr(record, "id", ""),
            "workbank_item_id": getattr(record, "opportunity_id", ""),
            "attempts": getattr(record, "attempts", 0),
        },
    )

    if status == "confirmed":
        # CONFIRMED implies it was submitted first: walk the honest chain
        # PENDING -> REVIEWING -> ACCEPTED so revenue_state tracks committed -> earned.
        tracker.update_opportunity_status(
            opp_id, PaymentStatus.REVIEWING, {"submission_id": getattr(record, "id", ""), "awaiting_review": True}
        )
        tracker.update_opportunity_status(
            opp_id, PaymentStatus.ACCEPTED, {"submission_id": getattr(record, "id", ""), "platform_confirmed": True}
        )
    elif status == "submitted":
        tracker.update_opportunity_status(
            opp_id, PaymentStatus.REVIEWING, {"submission_id": getattr(record, "id", ""), "awaiting_review": True}
        )
    elif status in ("failed", "dlq"):
        tracker.update_opportunity_status(
            opp_id,
            PaymentStatus.FAILED,
            {"submission_id": getattr(record, "id", ""), "last_error": getattr(record, "last_error", "")},
        )
    else:
        # PENDING/PREPARING/READY/SUBMITTING: created as PENDING, nothing more to do.
        return opp_id
    return opp_id


def record_pipeline_outcome(
    platform: str,
    bounty_id: str,
    verdict: str,
    reward: float = 0.0,
    url: str = "",
    title: str = "",
) -> str | None:
    """Record a DevBountyPipeline result in the RevenueTracker.

    verdict: submitted | rejected | failed | error (pipeline vocabulary).
    submitted → REVIEWING; rejected/failed/error → FAILED.
    """
    from cores.revenue_tracker.revenue_tracker import PaymentStatus, get_revenue_tracker

    verdict_norm = (verdict or "").strip().lower()
    if verdict_norm not in ("submitted", "rejected", "failed", "error"):
        return None
    tracker = get_revenue_tracker()
    opp_id = f"pipe_{platform}_{bounty_id}"
    _get_or_create_opp(
        tracker,
        opp_id,
        platform,
        title or f"{platform} bounty {bounty_id}",
        reward,
        url,
        source="dev_bounty_pipeline",
        extra_tracking={"bounty_id": bounty_id, "verdict": verdict_norm},
    )
    if verdict_norm == "submitted":
        tracker.update_opportunity_status(
            opp_id, PaymentStatus.REVIEWING, {"bounty_id": bounty_id, "awaiting_review": True}
        )
    else:
        tracker.update_opportunity_status(
            opp_id, PaymentStatus.FAILED, {"bounty_id": bounty_id, "verdict": verdict_norm}
        )
    return opp_id


def reconcile_from_persisted_state() -> dict[str, int]:
    """Rebuild the in-memory RevenueTracker from persisted execution state.

    The tracker is process-memory only; this replay runs at boot (background,
    non-fatal) so revenue truth survives restarts. Sources, in order:
    1. AutoSubmitEngine persisted queue (SUBMITTED/CONFIRMED/FAILED/DLQ).
    2. WorkBank delivered items (user-confirmed delivery; same semantics as
       the approve endpoint: REVIEWING -> ACCEPTED -> PAID chain).

    Idempotent: re-recording existing opportunities only refreshes status.
    Returns counts per source for boot logging.
    """
    from cores.revenue_tracker.revenue_tracker import PaymentStatus, get_revenue_tracker

    counts = {"submissions": 0, "delivered": 0, "skipped": 0}
    try:
        from cores.opportunity.executors.auto_submit import get_auto_submit_engine

        engine = get_auto_submit_engine()
        for record in engine.list_submissions():
            status = str(getattr(getattr(record, "status", ""), "value", getattr(record, "status", "")) or "")
            if status.lower() in ("submitted", "confirmed", "failed", "dlq"):
                try:
                    record_submission_outcome(record)
                    counts["submissions"] += 1
                except Exception as exc:
                    logger.warning("Reconcile skipped submission %s: %s", getattr(record, "id", "?"), exc)
                    counts["skipped"] += 1
    except Exception as exc:
        logger.warning("Reconcile submissions skipped: %s", exc)

    try:
        from cores.direct_work_engine.workbank import get_workbank

        bank = get_workbank()
        tracker = get_revenue_tracker()
        for item in getattr(bank, "_items", {}).values():
            if getattr(item, "status", "") != "delivered":
                continue
            try:
                opp_id = f"wb_{item.id}"
                if opp_id in tracker.opportunities:
                    counts["delivered"] += 1
                    continue
                platform_key = str(getattr(item, "platform", "") or "").lower().replace("workplatform.", "")
                platform = _resolve_payment_platform(platform_key)
                _get_or_create_opp(
                    tracker,
                    opp_id,
                    platform_key,
                    str(getattr(item, "title", "") or item.id),
                    float(getattr(item, "reward", 0.0) or 0.0),
                    str(getattr(item, "url", "") or ""),
                    source="workbank_reconcile",
                    extra_tracking={"workbank_item_id": item.id, "reconciled_at_boot": True},
                )
                tracker.update_opportunity_status(opp_id, PaymentStatus.REVIEWING, {"reconciled_at_boot": True})
                if platform in _paid_platforms():
                    tracker.update_opportunity_status(opp_id, PaymentStatus.ACCEPTED, {"reconciled_at_boot": True})
                    tracker.update_opportunity_status(opp_id, PaymentStatus.PAID, {"reconciled_at_boot": True})
                counts["delivered"] += 1
            except Exception as exc:
                logger.warning("Reconcile skipped workbank item %s: %s", getattr(item, "id", "?"), exc)
                counts["skipped"] += 1
    except Exception as exc:
        logger.warning("Reconcile workbank skipped: %s", exc)
    return counts


def _paid_platforms() -> Any:
    from cores.revenue_tracker.revenue_tracker import PaymentPlatform

    return (PaymentPlatform.BUG_BOUNTY, PaymentPlatform.DEV_BOUNTY)
