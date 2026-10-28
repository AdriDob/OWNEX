"""Pillar Performance Tracker — Tracks REAL $/hour per pillar.

The difference between this and the orchestrator:
- Orchestrator = estimated potential (what COULD happen)
- Performance = actual results (what DID happen)

Key metric: PAID USD / HUMAN MINUTE
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.pillars.performance")


@dataclass
class PillarAction:
    """A single action within a pillar."""

    id: str
    pillar: str  # bug_bounty, ai_tasks, dev_bounty, qa, data_annotation
    platform: str
    title: str
    status: str  # discovered, applied, accepted, paid, rejected, expired
    human_minutes: float
    expected_value: float
    actual_revenue: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    paid_at: datetime | None = None
    notes: str = ""

    @property
    def real_hourly_rate(self) -> float:
        """Actual revenue per human hour."""
        if self.human_minutes <= 0:
            return 0.0
        return (self.actual_revenue / self.human_minutes) * 60

    @property
    def ev_hourly_rate(self) -> float:
        """Expected value per human hour."""
        if self.human_minutes <= 0:
            return 0.0
        return (self.expected_value / self.human_minutes) * 60

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pillar": self.pillar,
            "platform": self.platform,
            "title": self.title,
            "status": self.status,
            "human_minutes": self.human_minutes,
            "expected_value": self.expected_value,
            "actual_revenue": self.actual_revenue,
            "real_hourly_rate": round(self.real_hourly_rate, 2),
            "ev_hourly_rate": round(self.ev_hourly_rate, 2),
            "created_at": self.created_at.isoformat(),
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }


@dataclass
class PillarStats:
    """Aggregated stats for one pillar."""

    pillar: str
    total_actions: int = 0
    discovered: int = 0
    applied: int = 0
    accepted: int = 0
    paid: int = 0
    rejected: int = 0
    expired: int = 0
    total_human_minutes: float = 0.0
    total_expected_value: float = 0.0
    total_actual_revenue: float = 0.0
    platforms_used: list[str] = field(default_factory=list)

    @property
    def real_hourly_rate(self) -> float:
        """REAL $/hour — the only number that matters."""
        if self.total_human_minutes <= 0:
            return 0.0
        return (self.total_actual_revenue / self.total_human_minutes) * 60

    @property
    def ev_hourly_rate(self) -> float:
        """Expected $/hour."""
        if self.total_human_minutes <= 0:
            return 0.0
        return (self.total_expected_value / self.total_human_minutes) * 60

    @property
    def acceptance_rate(self) -> float:
        """What % of applications get accepted."""
        if self.applied <= 0:
            return 0.0
        return self.accepted / self.applied

    @property
    def conversion_rate(self) -> float:
        """What % of discoveries become paid."""
        if self.discovered <= 0:
            return 0.0
        return self.paid / self.discovered

    @property
    def ev_accuracy(self) -> float:
        """How accurate are our EV estimates?"""
        if self.total_expected_value <= 0:
            return 0.0
        return self.total_actual_revenue / self.total_expected_value

    def to_dict(self) -> dict[str, Any]:
        return {
            "pillar": self.pillar,
            "total_actions": self.total_actions,
            "discovered": self.discovered,
            "applied": self.applied,
            "accepted": self.accepted,
            "paid": self.paid,
            "rejected": self.rejected,
            "expired": self.expired,
            "total_human_minutes": round(self.total_human_minutes, 1),
            "total_human_hours": round(self.total_human_minutes / 60, 2),
            "total_expected_value": round(self.total_expected_value, 2),
            "total_actual_revenue": round(self.total_actual_revenue, 2),
            "real_hourly_rate": round(self.real_hourly_rate, 2),
            "ev_hourly_rate": round(self.ev_hourly_rate, 2),
            "acceptance_rate": round(self.acceptance_rate * 100, 1),
            "conversion_rate": round(self.conversion_rate * 100, 1),
            "ev_accuracy": round(self.ev_accuracy * 100, 1),
            "platforms_used": self.platforms_used,
        }


@dataclass
class PersonalForecast:
    """Forecast based on YOUR real data, not generic estimates."""

    conserv: float = 0.0
    base_val: float = 0.0
    optimist: float = 0.0
    exceptl: float = 0.0
    confidence: str = "low"  # low, medium, high
    based_on_days: int = 0
    data_points: int = 0
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "conservative": round(self.conserv, 2),
            "base": round(self.base_val, 2),
            "optimistic": round(self.optimist, 2),
            "exceptional": round(self.exceptl, 2),
            "confidence": self.confidence,
            "based_on_days": self.based_on_days,
            "data_points": self.data_points,
            "recommendation": self.recommendation,
        }


class PerformanceTracker:
    """Tracks REAL performance per pillar. The source of truth."""

    PILLARS = ["bug_bounty", "ai_tasks", "dev_bounty", "qa", "data_annotation"]

    def __init__(self) -> None:
        self.actions: list[PillarAction] = []
        self._counter = 0

    def record_action(
        self,
        pillar: str,
        platform: str,
        title: str,
        status: str,
        human_minutes: float,
        expected_value: float,
        actual_revenue: float = 0.0,
        notes: str = "",
    ) -> PillarAction:
        """Record a new action."""
        self._counter += 1
        action = PillarAction(
            id=f"pa_{self._counter}",
            pillar=pillar,
            platform=platform,
            title=title,
            status=status,
            human_minutes=human_minutes,
            expected_value=expected_value,
            actual_revenue=actual_revenue,
            notes=notes,
        )
        self.actions.append(action)
        logger.info(
            "[PERF] %s/%s: %s ($%.0f, %.0f min)",
            pillar,
            platform,
            title,
            actual_revenue,
            human_minutes,
        )
        return action

    def update_status(self, action_id: str, status: str, revenue: float = 0.0) -> bool:
        """Update an action's status."""
        for action in self.actions:
            if action.id == action_id:
                action.status = status
                if revenue > 0:
                    action.actual_revenue = revenue
                if status == "paid":
                    action.paid_at = datetime.now(UTC)
                elif status in ("accepted", "rejected"):
                    action.completed_at = datetime.now(UTC)
                return True
        return False

    def get_pillar_stats(self, pillar: str) -> PillarStats:
        """Get aggregated stats for a pillar."""
        stats = PillarStats(pillar=pillar)
        platforms = set()

        for action in self.actions:
            if action.pillar != pillar:
                continue

            stats.total_actions += 1
            platforms.add(action.platform)

            if action.status == "discovered":
                stats.discovered += 1
            elif action.status == "applied":
                stats.applied += 1
            elif action.status == "accepted":
                stats.accepted += 1
            elif action.status == "paid":
                stats.paid += 1
            elif action.status == "rejected":
                stats.rejected += 1
            elif action.status == "expired":
                stats.expired += 1

            stats.total_human_minutes += action.human_minutes
            stats.total_expected_value += action.expected_value
            stats.total_actual_revenue += action.actual_revenue

        stats.platforms_used = sorted(platforms)
        return stats

    def get_all_stats(self) -> dict[str, PillarStats]:
        """Get stats for all pillars."""
        return {pillar: self.get_pillar_stats(pillar) for pillar in self.PILLARS}

    def get_real_hourly_rates(self) -> dict[str, float]:
        """Get REAL $/hour for each pillar."""
        return {pillar: self.get_pillar_stats(pillar).real_hourly_rate for pillar in self.PILLARS}

    def get_best_pillar(self) -> str:
        """Which pillar actually pays the most per hour?"""
        rates = self.get_real_hourly_rates()
        if not any(r > 0 for r in rates.values()):
            return "ai_tasks"  # Default: fastest time to first pay
        return max(rates, key=rates.get)

    def generate_forecast(self) -> PersonalForecast:
        """Generate forecast based on YOUR real data."""
        stats = self.get_all_stats()

        # Calculate total real metrics
        total_paid = sum(s.total_actual_revenue for s in stats.values())
        total_minutes = sum(s.total_human_minutes for s in stats.values())
        total_actions = sum(s.total_actions for s in stats.values())
        paid_actions = sum(s.paid for s in stats.values())

        if total_actions < 5:
            return PersonalForecast(
                confidence="low",
                data_points=total_actions,
                recommendation="Need more data. Keep tracking actions.",
            )

        # Calculate real hourly rate
        real_rate = (total_paid / max(total_minutes, 1)) * 60

        # Calculate acceptance rate
        total_applied = sum(s.applied for s in stats.values())
        total_accepted = sum(s.accepted for s in stats.values())
        acceptance = total_accepted / max(total_applied, 1)

        # Project monthly (22 working days, 4.5 hours/day)
        daily_hours = 4.5
        working_days = 22
        monthly_hours = daily_hours * working_days

        base_monthly = real_rate * monthly_hours

        # Scenarios
        conservative = base_monthly * 0.7  # 30% buffer
        optimistic = base_monthly * 1.5  # 50% upside
        exceptional = base_monthly * 3.0  # Exceptional month

        # Confidence based on data quality
        if total_actions >= 50 and paid_actions >= 5:
            confidence = "medium"
        elif total_actions >= 100 and paid_actions >= 20:
            confidence = "high"
        else:
            confidence = "low"

        # Best pillar
        best = self.get_best_pillar()

        return PersonalForecast(
            conserv=conservative,
            base_val=base_monthly,
            optimist=optimistic,
            exceptl=exceptional,
            confidence=confidence,
            based_on_days=working_days,
            data_points=total_actions,
            recommendation=(
                f"Best performing pillar: {best}. "
                f"Your real $/hour: ${real_rate:.0f}. "
                f"Acceptance rate: {acceptance:.0%}. "
                f"Prioritize {best} for maximum income."
            ),
        )

    def get_dashboard(self) -> dict[str, Any]:
        """Get complete performance dashboard."""
        stats = self.get_all_stats()
        forecast = self.generate_forecast()

        # Summary
        total_paid = sum(s.total_actual_revenue for s in stats.values())
        total_expected = sum(s.total_expected_value for s in stats.values())
        total_minutes = sum(s.total_human_minutes for s in stats.values())
        total_actions = sum(s.total_actions for s in stats.values())

        real_rate = (total_paid / max(total_minutes, 1)) * 60

        return {
            "summary": {
                "total_actions": total_actions,
                "total_paid": round(total_paid, 2),
                "total_expected": round(total_expected, 2),
                "total_human_hours": round(total_minutes / 60, 2),
                "real_hourly_rate": round(real_rate, 2),
                "ev_accuracy": round(total_paid / max(total_expected, 1) * 100, 1),
            },
            "pillars": {k: v.to_dict() for k, v in stats.items()},
            "forecast": forecast.to_dict(),
            "best_pillar": self.get_best_pillar(),
            "hourly_rates": {k: round(v, 2) for k, v in self.get_real_hourly_rates().items()},
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize tracker state."""
        return self.get_dashboard()


# Singleton
_performance_tracker: PerformanceTracker | None = None


def get_performance_tracker() -> PerformanceTracker:
    """Get or create the global performance tracker."""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    return _performance_tracker
