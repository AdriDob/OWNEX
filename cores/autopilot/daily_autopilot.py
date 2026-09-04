"""Daily Autopilot — The daily cycle that produces the ONE action.

Runs once per day (or on demand) to:
1. Refresh all data sources
2. Reconcile state
3. Generate candidate actions from all sources
4. Score and rank them
5. Output exactly ONE action (or NO ACTION REQUIRED)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from cores.autopilot.config.autopilot_config import AutopilotConfig
from cores.autopilot.one_action import (
    OneAction,
    create_deliver_action,
)

logger = logging.getLogger(__name__)


class DailyAutopilot:
    """
    Daily Autopilot — runs the daily decision cycle.

    The daily cycle:
    1. Refresh all data sources (WorkBank, Income Plan, Capital, Platforms)
    2. Reconcile pending work, payments, submissions
    3. Generate candidate actions from all sources
    5. Score and rank by EV/human_hour * success_probability * urgency
    6. Output exactly ONE action (or NO ACTION REQUIRED)

    Runs automatically at 06:00 daily, or on demand via API.
    """

    def __init__(self, config: AutopilotConfig | None = None):
        self.config = config
        self._factory = None
        self._last_run: datetime | None = None
        self._last_action: OneAction | None = None
        self._run_count = 0

    @property
    def factory(self):
        if self._factory is None:
            from cores.autopilot.one_action import get_one_action_factory

            self._factory = get_one_action_factory()
        return self._factory

    def register_default_sources(self) -> None:
        """Register the default action sources."""
        self.factory.register_source(self._source_workbank_deliveries)
        self.factory.register_source(self._source_bounty_submissions)
        self.factory.register_source(self._source_platform_applications)
        self.factory.register_source(self._source_workbank_approvals)

    # --- Source Functions ---

    def _source_workbank_deliveries(self, context: dict[str, Any] | None) -> list:
        """Source: WorkBank items ready to deliver."""
        try:
            from cores.direct_work_engine.workbank import get_workbank

            wb = get_workbank()
            ready = [i for i in wb._items.values() if i.status == "ready_to_deliver"]
            return [create_deliver_action(i.to_dict()) for i in ready]
        except Exception as e:
            logger.debug(f"WorkBank deliveries source failed: {e}")
            return []

    def _source_bounty_submissions(self, context: dict[str, Any] | None) -> list:
        """Source: Bug bounty findings ready to submit."""
        try:
            from database import db, models

            session = db.SessionLocal()
            try:
                confirmed = (
                    session.query(models.Finding)
                    .filter(models.Finding.status == "confirmed")
                    .filter(models.Finding.submitted_at.is_(None))
                    .order_by(models.Finding.id.desc())
                    .limit(10)
                    .all()
                )
                actions = []
                for f in confirmed:
                    item = {
                        "id": f.id,
                        "title": getattr(f, "title", "") or f"Finding #{f.id}",
                        "vulnerability_type": getattr(f, "vulnerability_type", "unknown"),
                        "platform": getattr(f, "program", ""),
                        "reward": getattr(f, "reward", 0),
                        "ev_per_human_hour_usd": getattr(f, "ev_per_human_hour_usd", 0),
                        "payout_cadence_days": getattr(f, "payout_cadence_days", 30),
                        "acceptance_probability": 0.5,
                        "submission_url": f"/intelligence/findings/{f.id}",
                        "program": getattr(f, "program", ""),
                    }
                    actions.append(item)
                return actions
            finally:
                session.close()
        except Exception as e:
            logger.debug(f"Bounty submissions source failed: {e}")
            return []

    def _source_platform_applications(self, context: dict[str, Any] | None) -> list:
        """Source: Platform applications needing action."""
        try:
            from core.application_assistant import get_application_assistant

            assistant = get_application_assistant()
            assistant.overview()
            apps_plan = assistant.get_plan()

            actions = []
            for platform in apps_plan.get("platforms", []):
                if platform["status"] in {"accepted", "rejected", "paused"}:
                    continue
                pending = [s for s in platform["steps"] if not s["done"]]
                if not pending:
                    continue
                pending[0]
                platform_data = {
                    "key": platform["key"],
                    "name": platform["name"],
                    "url": platform["url"],
                    "hourly_rate_usd": platform.get("pay_range", {}).get("hourly_rate_usd"),
                    "time_to_first_work_hours": platform.get("time_to_first_work_hours", 5),
                    "payout_cadence_days": platform.get("payout_cadence_days"),
                    "zero_experience": platform.get("zero_experience", True),
                    "zero_barrier": platform.get("zero_barrier", False),
                    "readiness_pct": platform.get("readiness_pct", 50),
                }
                actions.append(platform_data)
            return actions
        except Exception as e:
            logger.debug(f"Platform applications source failed: {e}")
            return []

    def _source_workbank_approvals(self, context: dict[str, Any] | None) -> list:
        """Source: WorkBank items needing human approval (access setup)."""
        try:
            from cores.direct_work_engine.workbank import get_workbank

            wb = get_workbank()
            [i for i in wb._items.values() if i.status == "needs_access"]
            # These become setup actions
            return []
        except Exception as e:
            logger.debug(f"WorkBank approvals source failed: {e}")
            return []

    # --- Public API ---

    def run_daily_cycle(self, force: bool = False) -> dict[str, Any]:
        """Run the daily autopilot cycle.

        Args:
            force: If True, run even if already ran today.

        Returns:
            Dict with the one action and cycle metadata.
        """
        now = datetime.now(UTC)
        today = now.date()

        # Check if already ran today (unless forced)
        if not force and self._last_run and self._last_run.date() == today:
            return {
                "status": "skipped",
                "reason": "already_ran_today",
                "last_run": self._last_run.isoformat(),
                "action": self._last_action.to_dict() if self._last_action else None,
            }

        cycle_start = datetime.now(UTC)
        self._run_count += 1

        logger.info(f"Starting daily autopilot cycle #{self._run_count}")

        # Register sources if not already done
        if not self.factory._sources:
            self.register_default_sources()

        # Get the best action
        best_action = self.factory.get_best_action()

        # If no action, create "no action required"
        if best_action is None:
            from cores.autopilot.one_action import ActionType, ActionUrgency, ConfidenceBand, OneAction

            action = OneAction(
                action_type=ActionType.STRATEGIC_REVIEW,
                urgency=ActionUrgency.FLEXIBLE,
            )
            action.title = "NO ACTION REQUIRED"
            action.description = "OWNEX no ha encontrado acciones que valgan tu tiempo ahora mismo."
            action.why = "Ninguna acción supera el umbral mínimo de valor esperado por hora humana."
            action.instruction = "Relajate. OWNEX seguirá monitoreando y te avisará cuando haya algo valioso."
            action.expected_value_usd = 0.0
            action.ev_per_human_hour_usd = 0.0
            action.confidence_band = ConfidenceBand.HIGH
            action.success_probability = 1.0
            action.risk_level = "none"
            best_action = action

        # Set expiration based on urgency
        now = datetime.now(UTC)
        if best_action.urgency == "immediate":
            best_action.expires_at = datetime.now(UTC) + timedelta(hours=24)
        elif best_action.urgency == "today":
            best_action.expires_at = datetime.now(UTC) + timedelta(days=1)
        elif best_action.urgency == "this_week":
            best_action.expires_at = datetime.now(UTC) + timedelta(days=7)

        # Update tracking
        self._last_run = datetime.now(UTC)
        self._last_action = best_action

        cycle_duration = (datetime.now(UTC) - cycle_start).total_seconds()

        result = {
            "status": "completed",
            "cycle": self._run_count,
            "duration_seconds": cycle_duration,
            "action": best_action.to_dict(),
            "generated_at": best_action.generated_at.isoformat(),
            "expires_at": best_action.expires_at.isoformat() if best_action.expires_at else None,
        }

        logger.info(
            f"Daily autopilot cycle completed: {best_action.title} "
            f"(priority: {best_action.priority_score:.2f}, urgency: {best_action.urgency})"
        )

        return result

    def get_current_action(self) -> dict[str, Any] | None:
        """Get the current best action (from last cycle or generate new)."""
        if self._last_action and not self._last_action.is_expired:
            return self._last_action.to_dict()
        return None

    def force_refresh(self) -> dict[str, Any]:
        """Force a refresh of the daily cycle."""
        return self.run_daily_cycle(force=True)

    def get_status(self) -> dict[str, Any]:
        """Get the daily autopilot status."""
        return {
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count,
            "has_action": self._last_action is not None and not (self._last_action and self._last_action.is_expired),
            "current_action": self._last_action.to_dict()
            if self._last_action and not self._last_action.is_expired
            else None,
        }


# Singleton instance
_daily_autopilot: DailyAutopilot | None = None


def get_daily_autopilot(config: AutopilotConfig | None = None) -> DailyAutopilot:
    global _daily_autopilot
    if _daily_autopilot is None:
        _daily_autopilot = DailyAutopilot(config)
    return _daily_autopilot


async def run_daily_cycle(config: AutopilotConfig | None = None) -> dict[str, Any]:
    """Run the daily autopilot cycle (async wrapper)."""
    autopilot = get_daily_autopilot(config)
    return autopilot.run_daily_cycle()


def get_daily_autopilot_status() -> dict[str, Any]:
    """Get daily autopilot status."""
    autopilot = get_daily_autopilot()
    return autopilot.get_status()
