"""Learning feedback loop — makes the recommender improve with real outcomes.

OWNEX only learns from verified history. Applications that are still pending or
under review are not counted as outcomes; accepted/paid count as success,
failed/cancelled count as failure. Empty history leaves the profile untouched —
the engine never invents success rates.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from cores.direct_work_engine.models import OpportunityCategory, UserProfile

logger = logging.getLogger("ownex.direct_work_engine.feedback")

# Map RevenueTracker platform names to DWE categories when they align.
_PLATFORM_TO_CATEGORY: dict[str, OpportunityCategory] = {
    "bug_bounty": OpportunityCategory.BUG_BOUNTY,
    "dev_bounty": OpportunityCategory.DEV_BOUNTY,
    "data_annotation": OpportunityCategory.DATA_ANNOTATION,
}

_TERMINAL_SUCCESS_STATUSES = frozenset({"accepted", "paid"})
_TERMINAL_FAILURE_STATUSES = frozenset({"failed", "cancelled"})


@dataclass(slots=True)
class LearningRecord:
    """One verified application outcome used to update the profile."""

    platform: str
    accepted: bool
    amount: float = 0.0
    category: OpportunityCategory | None = None
    time_to_payout_days: float | None = None


def apply_learning(profile: UserProfile, records: list[LearningRecord]) -> UserProfile:
    """Fold verified outcomes into a profile's success-rate fields (in place).

    Returns the profile so it can be chained into the recommender.
    """
    if not records:
        return profile

    outcomes = [r for r in records if r.accepted is not None]
    if not outcomes:
        return profile

    accepted = [r for r in outcomes if r.accepted]
    profile.applications_submitted = len(outcomes)
    profile.applications_accepted = len(accepted)
    profile.total_earnings = round(sum(r.amount for r in accepted), 2)

    profile.platform_success_rates = _rates(outcomes, lambda r: r.platform)
    profile.category_success_rates = _rates(
        [r for r in outcomes if r.category is not None], lambda r: r.category.value if r.category else ""
    )

    payout_days = [r.time_to_payout_days for r in accepted if r.time_to_payout_days is not None]
    if payout_days:
        profile.avg_time_to_payment_days = round(sum(payout_days) / len(payout_days), 2)

    logger.info(
        "Learning: %d outcomes, %d accepted, %.2f earned across %d platforms",
        len(outcomes),
        len(accepted),
        profile.total_earnings,
        len(profile.platform_success_rates),
    )
    return profile


def build_history_from_revenue_tracker(tracker: object) -> list[LearningRecord]:
    """Derive verified LearningRecords from a RevenueTracker instance.

    Works on any object exposing an ``opportunities`` mapping of
    RevenueOpportunity-like records, keeping the DWE package decoupled.
    """
    records: list[LearningRecord] = []
    opportunities = getattr(tracker, "opportunities", {}) or {}

    for opp in opportunities.values():
        status = getattr(opp, "status", None)
        if status is None:
            continue
        status_value = status.value if hasattr(status, "value") else str(status)

        if status_value in _TERMINAL_SUCCESS_STATUSES:
            accepted = True
        elif status_value in _TERMINAL_FAILURE_STATUSES:
            accepted = False
        else:
            continue  # pending/reviewing are not outcomes yet

        platform = str(getattr(opp, "platform", "")).lower()
        category = _PLATFORM_TO_CATEGORY.get(platform)

        provider = getattr(opp, "provider_info", {}) or {}
        source_platform = str(provider.get("platform", "")).lower()
        if source_platform and source_platform != platform:
            platform = f"{platform}:{source_platform}"

        records.append(
            LearningRecord(
                platform=platform,
                category=category,
                accepted=accepted,
                amount=float(getattr(opp, "amount", 0) or 0),
                time_to_payout_days=_payout_days(opp),
            )
        )

    return records


def _payout_days(opp: object) -> float | None:
    created = getattr(opp, "created_at", None)
    updated = getattr(opp, "updated_at", None)
    if not created or not updated:
        return None
    seconds = (updated - created).total_seconds()
    return max(0.0, round(seconds / 86400.0, 2))


def _rates(records: list[LearningRecord], key: Callable[[LearningRecord], str]) -> dict[str, float]:
    totals: dict[str, int] = {}
    accepted_counts: dict[str, int] = {}
    for record in records:
        k = key(record)
        if not k:
            continue
        totals[k] = totals.get(k, 0) + 1
        if record.accepted:
            accepted_counts[k] = accepted_counts.get(k, 0) + 1
    return {k: round(accepted_counts.get(k, 0) / total, 3) for k, total in totals.items() if total > 0}
