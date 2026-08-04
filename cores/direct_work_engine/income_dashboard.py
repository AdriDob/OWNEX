"""Income Dashboard — the single pane of glass for OWNEX financial throughput.

Answers the owner's only real question: "is this system improving my money?"

Combines the Work Bank (jobs found/prepared/delivered), the Revenue pipeline
(payouts collected, USD/hour) and the Income Projector (time-to-target) into one
panel. Everything is read from existing engines — this module adds no data of its
own, it just consolidates (Golden Rule: no duplicated logic).

Output shape (one call):
  work : found | prepared (ready_to_deliver) | delivered | needs_access
         + targets (daily/weekly/monthly) with % achieved
  income : total_earned | pending_usd (cobros pendientes) | platforms_tracked
  roi : list of { platform, earned, accepted, pending, acceptance }
  projection : { crossing_months, months_to_target, target_monthly_usd,
                 monthly_curve } from the Income Projector
  generated_at : ISO timestamp
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from cores.direct_work_engine.income_projection import project_income

logger = logging.getLogger("ownex.direct_work_engine.income_dashboard")


class IncomeDashboard:
    """Consolidates WorkBank + Revenue + Projector into one financial panel."""

    def snapshot(
        self,
        work_income_usd_per_month: float = 0.0,
        savings_usd_per_month: float = 0.0,
        start_capital_usd: float = 0.0,
        annual_return_rate: float = 0.10,
        target_monthly_usd: float = 100_000.0,
    ) -> dict[str, Any]:
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "work": self._work_block(),
            "income": self._income_block(),
            "roi": self._roi_block(),
            "projection": self._projection_block(
                work_income_usd_per_month=work_income_usd_per_month,
                savings_usd_per_month=savings_usd_per_month,
                start_capital_usd=start_capital_usd,
                annual_return_rate=annual_return_rate,
                target_monthly_usd=target_monthly_usd,
            ),
        }

    # -- blocks -----------------------------------------------------------

    def _work_block(self) -> dict[str, Any]:
        from cores.direct_work_engine.workbank import get_workbank

        bank = None
        try:
            bank = get_workbank()
            items = list(bank._items.values()) if hasattr(bank, "_items") else []
        except Exception as exc:
            logger.debug("Work block degraded: %s", exc)
            items = []
        found = len(items)
        prepared = len([i for i in items if getattr(i, "ready_to_deliver", False)])
        delivered = len([i for i in items if getattr(i, "status", "") == "delivered"])
        needs_access = len([i for i in items if getattr(i, "status", "") == "needs_access"])
        targets = {}
        try:
            if bank is not None and hasattr(bank, "progress"):
                targets = bank.progress()
        except Exception:
            targets = {}
        return {
            "found": found,
            "prepared": prepared,
            "delivered": delivered,
            "needs_access": needs_access,
            "available_for_delivery": max(0, prepared - delivered),
            "targets": targets,
        }

    def _income_block(self) -> dict[str, Any]:
        """Payouts collected, pending cobros, USD/hour from the revenue layer."""
        from cores.revenue_tracker.revenue_tracker import get_revenue_tracker

        try:
            tracker = get_revenue_tracker()
            metrics = getattr(tracker, "metrics", {}) or {}
            total_earned = 0.0
            pending_usd = 0.0
            for metric in metrics.values():
                total_earned += float(getattr(metric, "completed_amount", 0.0) or 0.0)
                pending_usd += float(getattr(metric, "pending_amount", 0.0) or 0.0)
            return {
                "total_earned_usd": round(total_earned, 2),
                "pending_usd": round(pending_usd, 2),
                "platforms_tracked": len(metrics),
            }
        except Exception as exc:
            logger.debug("Income block degraded: %s", exc)
            return {
                "total_earned_usd": 0.0,
                "pending_usd": 0.0,
                "usd_per_hour": 0.0,
                "platforms_tracked": 0,
            }

    def _roi_block(self) -> list[dict[str, Any]]:
        """Per-platform earned/pending/accepted (from real outcomes, never invented)."""
        from cores.revenue_tracker.revenue_tracker import get_revenue_tracker

        try:
            tracker = get_revenue_tracker()
            metrics = getattr(tracker, "metrics", {}) or {}
            return [
                {
                    "platform": str(platform),
                    "earned_usd": round(float(getattr(m, "completed_amount", 0.0) or 0.0), 2),
                    "pending_usd": round(float(getattr(m, "pending_amount", 0.0) or 0.0), 2),
                    "accepted": int(getattr(m, "accepted", 0) or 0),
                    "total_amount_usd": round(float(getattr(m, "total_amount", 0.0) or 0.0), 2),
                }
                for platform, m in metrics.items()
            ]
        except Exception as exc:
            logger.debug("ROI block degraded: %s", exc)
            return []

    def _projection_block(
        self,
        work_income_usd_per_month: float,
        savings_usd_per_month: float,
        start_capital_usd: float,
        annual_return_rate: float,
        target_monthly_usd: float,
    ) -> dict[str, Any]:
        if work_income_usd_per_month <= 0 and savings_usd_per_month <= 0:
            return {
                "crossing_months": None,
                "months_to_target": None,
                "target_monthly_usd": target_monthly_usd,
                "note": "Configurá ingreso/ahorro por mes para ver tiempos.",
            }
        try:
            projection = project_income(
                work_income_usd_per_month=work_income_usd_per_month,
                savings_usd_per_month=savings_usd_per_month,
                start_capital_usd=start_capital_usd,
                annual_return_rate=annual_return_rate,
                target_monthly_usd=target_monthly_usd,
            )
            return {
                "crossing_months": projection.crossing_months,
                "months_to_target": projection.months_to_target,
                "capital_at_target_usd": round(projection.capital_at_target_usd, 2),
                "portfolio_monthly_income_usd": round(projection.portfolio_monthly_income_usd, 2),
                "target_monthly_usd": target_monthly_usd,
                "annual_return_rate": annual_return_rate,
                "monthly_curve": projection.monthly_curve,
            }
        except Exception as exc:
            logger.debug("Projection block degraded: %s", exc)
            return {"crossing_months": None, "months_to_target": None, "note": str(exc)}


def get_income_dashboard() -> IncomeDashboard:
    return IncomeDashboard()
