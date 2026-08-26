"""Freshness Tracker — Temporal decay for opportunities.

Prevents stale opportunities from competing with fresh ones.
Implements exponential decay with configurable half-life.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

logger = logging.getLogger("ownex.freshness")


@dataclass(slots=True)
class FreshnessConfig:
    """Configuration for freshness decay."""

    half_life_hours: float = 168.0  # 1 week default half-life
    min_score: float = 0.1  # floor for decay
    critical_age_hours: float = 720.0  # 30 days = critical


@dataclass(slots=True)
class FreshnessSnapshot:
    """Freshness assessment for an opportunity."""

    opportunity_id: str
    age_hours: float
    score: float  # 0–1
    is_critical: bool
    decay_rate: float
    recommended_action: str
    computed_at: str


class FreshnessTracker:
    """Tracks and computes freshness scores for opportunities."""

    def __init__(self, config: FreshnessConfig | None = None) -> None:
        self.config = config or FreshnessConfig()
        self._decay_constant = self._compute_decay_constant()

    def _compute_decay_constant(self) -> float:
        """Compute decay constant from half-life."""
        import math

        return math.log(2) / self.config.half_life_hours

    def compute_age_hours(self, discovered_at: datetime | str | None) -> float | None:
        """Compute age in hours from discovery timestamp."""
        if not discovered_at:
            return None
        if isinstance(discovered_at, str):
            try:
                dt = datetime.fromisoformat(discovered_at.replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            dt = discovered_at

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)

        age = datetime.now(UTC) - dt
        return max(0.0, age.total_seconds() / 3600)

    def compute_score(self, age_hours: float | None) -> float:
        """Compute freshness score (0–1) using exponential decay.

        Score = max(min_score, e^(-λ * age))

        Where λ = ln(2) / half_life
        """
        if age_hours is None:
            return 0.5  # unknown age = neutral

        import math

        score = math.exp(-self._decay_constant * age_hours)
        return max(self.config.min_score, min(1.0, score))

    def assess(self, discovered_at: datetime | str | None) -> FreshnessSnapshot:
        """Compute complete freshness snapshot."""
        age_hours = self.compute_age_hours(discovered_at)

        if age_hours is None:
            action = "Age unknown — verify freshness manually"
        elif age_hours < 24:
            action = "Fresh — prioritize immediately"
        elif age_hours < 168:  # 1 week
            action = "Recent — good to pursue"
        elif age_hours < 168 * 2:  # 2 weeks
            action = "Aging — verify still active before investing time"
        elif age_hours < 720:  # 30 days
            action = "Aging — verify still active, check for duplicates"
        else:
            action = "Critical age — likely stale, verify before any work"

        return FreshnessSnapshot(
            opportunity_id="",
            age_hours=age_hours if age_hours else 0.0,
            score=self.compute_score(age_hours),
            is_critical=age_hours is not None and age_hours >= self.config.critical_age_hours,
            decay_rate=self._decay_constant,
            recommended_action=action if age_hours is not None else "Age unknown — verify freshness manually",
            computed_at=datetime.now(UTC).isoformat(),
        )


# ──────────────────────────────────────────────────────────────────────
# Batch Processing
# ──────────────────────────────────────────────────────────────────────


class FreshnessBatchProcessor:
    """Batch process freshness for WorkBank / opportunity lists."""

    def __init__(self, tracker: FreshnessTracker | None = None) -> None:
        self.tracker = tracker or FreshnessTracker()

    def score_opportunities(self, opportunities: list) -> list[dict]:
        """Add freshness scores to a list of opportunities.

        Expects each opportunity to have a `discovered_at` attribute or key.
        """
        results = []
        for opp in opportunities:
            # Extract discovery time
            discovered = None
            if hasattr(opp, "discovered_at"):
                discovered = opp.discovered_at
            elif isinstance(opp, dict):
                discovered = opp.get("discovered_at") or opp.get("created_at")

            if not discovered:
                continue

            try:
                if isinstance(discovered, str):
                    dt = datetime.fromisoformat(discovered.replace("Z", "+00:00"))
                else:
                    dt = discovered
            except Exception:
                continue

            freshness = self.tracker.assess(dt)
            results.append(
                {
                    "opportunity_id": getattr(opp, "id", None)
                    or (discovered if isinstance(discovered, dict) else None),
                    "freshness_score": freshness.score,
                    "age_hours": freshness.age_hours,
                    "is_critical": freshness.is_critical,
                    "recommended_action": freshness.recommended_action,
                }
            )

        return results

    def filter_stale(self, opportunities: list, threshold: float = 0.3) -> tuple[list, list]:
        """Split opportunities into fresh and stale.

        Returns: (fresh, stale)
        """
        fresh = []
        stale = []
        for opp in opportunities:
            discovered = getattr(opp, "discovered_at", None) or (
                opp.get("discovered_at") if isinstance(opp, dict) else None
            )
            if not discovered:
                stale.append(opp)
                continue

            try:
                score = self.tracker.compute_score(self.tracker.compute_age_hours(getattr(opp, "discovered_at", None)))
            except Exception:
                stale.append(opp)
                continue

            if score >= 0.3:
                fresh.append(opp)
            else:
                stale.append(opp)

        return fresh, stale

    def get_decay_schedule(self, hours_ahead: int = 168) -> list[dict]:
        """Get projected decay over time for planning.

        Returns list of {hours_from_now, score} for visualization.
        """
        import math

        decay = self.tracker._decay_constant
        datetime.now(UTC)
        schedule = []
        for h in range(0, hours_ahead + 1, 24):
            future_time = datetime.now(UTC) + timedelta(hours=h)
            math.exp(-decay * h)
            schedule.append(
                {
                    "hours_from_now": h,
                    "date": future_time.date().isoformat(),
                    "score": max(0.1, min(1.0, math.exp(-decay * h))),
                }
            )
        return schedule


# ──────────────────────────────────────────────────────────────────────
# Convenience
# ──────────────────────────────────────────────────────────────────────

_freshness_tracker: FreshnessTracker | None = None


def get_freshness_tracker(config: FreshnessConfig | None = None) -> FreshnessTracker:
    global _freshness_tracker
    global _freshness_tracker
    if _freshness_tracker is None:
        _freshness_tracker = FreshnessTracker(config)
    return _freshness_tracker


def compute_freshness_score(discovered_at: datetime | str | None, half_life_hours: float = 168.0) -> float:
    """Convenience function for quick freshness scoring."""
    tracker = FreshnessTracker(FreshnessConfig(half_life_hours=half_life_hours))
    return tracker.compute_score(tracker.compute_age_hours(discovered_at))


def is_stale(discovered_at: datetime | str | None, threshold: float = 0.3, half_life_hours: float = 168.0) -> bool:
    """Quick check if opportunity is stale."""
    return compute_freshness_score(discovered_at, half_life_hours) < threshold
