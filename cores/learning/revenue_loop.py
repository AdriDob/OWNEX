"""Revenue Learning Loop — The heart of OWNEX.

Closes the circuit:
  DISCOVER → RANK → TELL USER WHAT TO DO → HELP DO IT → RECORD PAID → LEARN → IMPROVE

Metrics:
  - HUMAN_MINUTES / DAY
  - $PAID_REVENUE / HUMAN_HOUR
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.learning.revenue_loop")


@dataclass
class ActionRecord:
    """A record of a human action and its economic result."""

    id: str
    opportunity_id: str
    action_type: str  # investigate, submit, approve, review
    title: str
    description: str
    human_minutes: float  # How many minutes the human spent
    expected_value: float  # What we thought it was worth
    actual_revenue: float = 0.0  # What we actually got
    status: str = "pending"  # pending, completed, paid, rejected
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    paid_at: datetime | None = None
    learning_tags: list[str] = field(default_factory=list)

    @property
    def ev_per_hour(self) -> float:
        """Expected value per human hour."""
        if self.human_minutes <= 0:
            return 0.0
        return (self.expected_value / self.human_minutes) * 60

    @property
    def actual_per_hour(self) -> float:
        """Actual revenue per human hour."""
        if self.human_minutes <= 0:
            return 0.0
        return (self.actual_revenue / self.human_minutes) * 60

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "action_type": self.action_type,
            "title": self.title,
            "human_minutes": self.human_minutes,
            "expected_value": self.expected_value,
            "actual_revenue": self.actual_revenue,
            "ev_per_hour": round(self.ev_per_hour, 2),
            "actual_per_hour": round(self.actual_per_hour, 2),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DailyMetrics:
    """Daily metrics for the revenue learning loop."""

    date: str
    human_minutes: float = 0.0
    actions_taken: int = 0
    expected_value: float = 0.0
    actual_revenue: float = 0.0
    opportunities_discovered: int = 0
    opportunities_pursued: int = 0
    submissions: int = 0
    accepted: int = 0
    rejected: int = 0
    pending: int = 0

    @property
    def human_hours(self) -> float:
        return self.human_minutes / 60

    @property
    def ev_per_hour(self) -> float:
        if self.human_minutes <= 0:
            return 0.0
        return (self.expected_value / self.human_minutes) * 60

    @property
    def revenue_per_hour(self) -> float:
        if self.human_minutes <= 0:
            return 0.0
        return (self.actual_revenue / self.human_minutes) * 60

    @property
    def acceptance_rate(self) -> float:
        total = self.accepted + self.rejected
        if total == 0:
            return 0.0
        return self.accepted / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "human_minutes": round(self.human_minutes, 1),
            "human_hours": round(self.human_hours, 2),
            "actions_taken": self.actions_taken,
            "expected_value": round(self.expected_value, 2),
            "actual_revenue": round(self.actual_revenue, 2),
            "ev_per_hour": round(self.ev_per_hour, 2),
            "revenue_per_hour": round(self.revenue_per_hour, 2),
            "opportunities_discovered": self.opportunities_discovered,
            "opportunities_pursued": self.opportunities_pursued,
            "submissions": self.submissions,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "pending": self.pending,
            "acceptance_rate": round(self.acceptance_rate * 100, 1),
        }


class RevenueLearningLoop:
    """The heart of OWNEX — closes the circuit between discovery and revenue."""

    def __init__(self) -> None:
        self.actions: list[ActionRecord] = []
        self.daily: dict[str, DailyMetrics] = {}
        self.learnings: list[dict[str, Any]] = []
        self._action_counter = 0

    def record_action(
        self,
        opportunity_id: str,
        action_type: str,
        title: str,
        description: str,
        human_minutes: float,
        expected_value: float,
    ) -> ActionRecord:
        """Record a human action."""
        self._action_counter += 1
        record = ActionRecord(
            id=f"action_{self._action_counter}",
            opportunity_id=opportunity_id,
            action_type=action_type,
            title=title,
            description=description,
            human_minutes=human_minutes,
            expected_value=expected_value,
        )
        self.actions.append(record)

        # Update daily metrics
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if today not in self.daily:
            self.daily[today] = DailyMetrics(date=today)
        daily = self.daily[today]
        daily.human_minutes += human_minutes
        daily.actions_taken += 1
        daily.expected_value += expected_value

        logger.info(
            "[LEARN] Recorded action: %s (%.0f min, EV=$%.0f)",
            title,
            human_minutes,
            expected_value,
        )
        self._persist_action(record)
        return record

    def _persist_action(self, action: ActionRecord) -> None:
        """Persist action to DB."""
        try:
            from database.persistence import get_learning_persistence

            persist = get_learning_persistence()
            persist.save_action(action)
        except Exception:
            pass

    def _persist_insight(self, insight: dict[str, Any]) -> None:
        """Persist insight to DB."""
        try:
            from database.persistence import get_learning_persistence

            persist = get_learning_persistence()
            persist.save_insight(insight)
        except Exception:
            pass

    def _load_from_db(self) -> None:
        """Load actions and insights from DB."""
        try:
            from database.persistence import get_learning_persistence

            persist = get_learning_persistence()
            actions_data = persist.load_actions(limit=200)
            for a in actions_data:
                self._action_counter += 1
                record = ActionRecord(
                    id=a["id"],
                    opportunity_id=a["opportunity_id"],
                    action_type=a["action_type"],
                    title=a["title"],
                    description="",
                    human_minutes=a["human_minutes"],
                    expected_value=a["expected_value"],
                    actual_revenue=a["actual_revenue"],
                    status=a["status"],
                )
                self.actions.append(record)
                # Update daily
                date_str = a.get("created_at", "")[:10]
                if date_str:
                    if date_str not in self.daily:
                        self.daily[date_str] = DailyMetrics(date=date_str)
                    daily = self.daily[date_str]
                    daily.human_minutes += a["human_minutes"]
                    daily.actions_taken += 1
                    daily.expected_value += a["expected_value"]
                    daily.actual_revenue += a["actual_revenue"]
        except Exception:
            pass

    def record_result(
        self,
        action_id: str,
        actual_revenue: float,
        status: str,
        learning_tags: list[str] | None = None,
    ) -> bool:
        """Record the result of an action."""
        for action in self.actions:
            if action.id == action_id:
                action.actual_revenue = actual_revenue
                action.status = status
                action.completed_at = datetime.now(UTC)
                if learning_tags:
                    action.learning_tags = learning_tags

                # Update daily metrics
                today = action.created_at.strftime("%Y-%m-%d")
                if today in self.daily:
                    daily = self.daily[today]
                    daily.actual_revenue += actual_revenue
                    if status == "paid":
                        daily.accepted += 1
                    elif status == "rejected":
                        daily.rejected += 1
                    elif status == "submitted":
                        daily.submissions += 1

                # Generate learning
                self._learn(action)
                return True
        return False

    def _learn(self, action: ActionRecord) -> None:
        """Learn from an action result."""
        learning = {
            "action_id": action.id,
            "action_type": action.action_type,
            "expected_value": action.expected_value,
            "actual_revenue": action.actual_revenue,
            "human_minutes": action.human_minutes,
            "ev_per_hour": action.ev_per_hour,
            "actual_per_hour": action.actual_per_hour,
            "status": action.status,
            "tags": action.learning_tags,
            "learned_at": datetime.now(UTC).isoformat(),
        }

        # Key insight: was our EV estimate accurate?
        if action.actual_revenue > 0:
            accuracy = action.actual_revenue / max(action.expected_value, 1)
            learning["ev_accuracy"] = accuracy
            if accuracy > 1.5:
                learning["insight"] = "Underestimated value — boost similar opportunities"
            elif accuracy < 0.5:
                learning["insight"] = "Overestimated value — reduce similar opportunities"
            else:
                learning["insight"] = "EV estimate was reasonable"

        self.learnings.append(learning)
        self._persist_insight(learning)

    def get_daily_metrics(self, days: int = 30) -> list[DailyMetrics]:
        """Get daily metrics for the last N days."""
        sorted_dates = sorted(self.daily.keys(), reverse=True)
        return [self.daily[d] for d in sorted_dates[:days]]

    def get_totals(self) -> dict[str, Any]:
        """Get total metrics across all time."""
        total_minutes = sum(a.human_minutes for a in self.actions)
        total_ev = sum(a.expected_value for a in self.actions)
        total_revenue = sum(a.actual_revenue for a in self.actions)
        total_actions = len(self.actions)

        return {
            "total_human_minutes": round(total_minutes, 1),
            "total_human_hours": round(total_minutes / 60, 2),
            "total_actions": total_actions,
            "total_expected_value": round(total_ev, 2),
            "total_actual_revenue": round(total_revenue, 2),
            "avg_ev_per_hour": round((total_ev / max(total_minutes, 1)) * 60, 2),
            "avg_revenue_per_hour": round((total_revenue / max(total_minutes, 1)) * 60, 2),
            "ev_accuracy": round(total_revenue / max(total_ev, 1), 2),
        }

    def get_dashboard(self) -> dict[str, Any]:
        """Get complete learning loop dashboard."""
        totals = self.get_totals()
        recent = self.get_daily_metrics(days=7)

        # Today's metrics
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        today_metrics = self.daily.get(today, DailyMetrics(date=today))

        # Pending actions
        pending = [a for a in self.actions if a.status == "pending"]

        # Key learnings
        recent_learnings = self.learnings[-10:] if self.learnings else []

        return {
            "today": today_metrics.to_dict(),
            "totals": totals,
            "recent_days": [d.to_dict() for d in recent],
            "pending_actions": len(pending),
            "recent_learnings": recent_learnings,
            "metrics": {
                "human_minutes_per_day": round(totals["total_human_minutes"] / max(len(self.daily), 1), 1),
                "revenue_per_human_hour": totals["avg_revenue_per_hour"],
            },
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize learning loop state."""
        return self.get_dashboard()


# Singleton
_revenue_loop: RevenueLearningLoop | None = None


def get_revenue_loop() -> RevenueLearningLoop:
    """Get or create the global revenue learning loop."""
    global _revenue_loop
    if _revenue_loop is None:
        _revenue_loop = RevenueLearningLoop()
    return _revenue_loop
