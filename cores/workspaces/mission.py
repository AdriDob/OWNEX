"""Mission — monthly income target + gap + suggested mix.

A mission is an OPERATIONAL TARGET, never a guarantee. Every output carries
that disclaimer plus what is missing to close the gap.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.workspaces.mission")


@dataclass(slots=True)
class Mission:
    """$X THIS MONTH: target, verified earned, gap, suggested mix."""

    target_usd: float
    earned_usd: float = 0.0
    month: str = ""
    suggested: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.month:
            self.month = datetime.now(UTC).strftime("%Y-%m")

    @property
    def gap_usd(self) -> float:
        return round(max(0.0, self.target_usd - self.earned_usd), 2)

    @property
    def progress_pct(self) -> float:
        if self.target_usd <= 0:
            return 0.0
        return round(min(100.0, self.earned_usd / self.target_usd * 100), 1)

    @property
    def is_met(self) -> bool:
        return self.earned_usd >= self.target_usd

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_usd": self.target_usd,
            "earned_usd": self.earned_usd,
            "gap_usd": self.gap_usd,
            "progress_pct": self.progress_pct,
            "is_met": self.is_met,
            "month": self.month,
            "suggested_mix": self.suggested,
            "disclaimer": "TARGET, not a guarantee. Projected from verified history and honest priors only.",
        }


def get_earned_usd() -> float:
    """Verified earned total (RevenueTracker realized). 0.0 when unavailable."""
    try:
        from cores.revenue_tracker.revenue_tracker import get_revenue_tracker

        tracker = get_revenue_tracker()
        metrics = tracker.get_platform_metrics("all") if hasattr(tracker, "get_platform_metrics") else None
        total = 0.0
        if isinstance(metrics, dict):
            total = float(metrics.get("completed_amount", 0) or 0)
        else:
            for opp in getattr(tracker, "opportunities", {}).values():
                if getattr(getattr(opp, "status", None), "value", opp.status) == "paid":
                    try:
                        total += float(getattr(opp, "amount", 0) or 0)
                    except (TypeError, ValueError):
                        continue
        return round(total, 2)
    except Exception as exc:
        logger.debug("Mission earned-usd unavailable: %s", exc)
        return 0.0


def get_mission(target_usd: float, earned_usd: float | None = None) -> Mission:
    """Build the current mission. Earned defaults to verified tracker total."""
    earned = float(earned_usd) if earned_usd is not None else get_earned_usd()
    return Mission(target_usd=float(target_usd), earned_usd=earned)
