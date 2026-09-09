"""Executive Dashboard — CEO view: '¿Esta semana ganamos plata?'

Aggregates revenue, pipeline health, and cycle performance into a single view.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.revenue.metrics import RevenueMetrics

logger = logging.getLogger("ownex.cycles.executive")


class ExecutiveDashboard:
    """Executive Dashboard — answers the one question: 'Did we make money this week?'"""

    def __init__(self, metrics: RevenueMetrics | None = None) -> None:
        self._metrics = metrics or RevenueMetrics()

    def get_ceo_view(self) -> dict[str, Any]:
        """Main CEO view — single screen summary."""
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Revenue this week
        weekly_payouts = self._get_weekly_payouts(week_ago)
        weekly_total = sum(p["amount"] for p in weekly_payouts)
        weekly_count = len(weekly_payouts)

        # Revenue this month
        monthly_payouts = self._get_monthly_payouts(month_ago)
        monthly_total = sum(p["amount"] for p in monthly_payouts)

        # Pipeline status
        pipeline = self._metrics.finding_pipeline()

        # USD/hour
        usd_per_hour = self._metrics.usd_per_hour()

        # Top platform
        platform_data = self._metrics.payout_summary().get("by_platform", {})
        top_platform = max(platform_data.items(), key=lambda x: x[1], default=("—", 0))[0]

        # Acceptance rate
        acceptance = self._metrics.acceptance_rate()
        total_accepted = sum(d.get("accepted", 0) for d in acceptance.values())
        total_resolved = sum(d.get("accepted", 0) + d.get("rejected", 0) for d in acceptance.values())
        overall_acceptance = total_accepted / max(total_resolved, 1)

        # Active cycles
        cycle_status = self._get_cycle_status()

        # Answer the question
        made_money = weekly_total > 0
        verdict = "🟢 GANAMOS PLATA" if made_money else "🔴 SIN INGRESOS ESTA SEMANA"

        return {
            "verdict": verdict,
            "made_money_this_week": made_money,
            "weekly": {
                "total_usd": round(weekly_total, 2),
                "count": weekly_count,
                "avg_per_payout": round(weekly_total / max(weekly_count, 1), 2),
            },
            "monthly": {
                "total_usd": round(monthly_total, 2),
                "runway_months": self._calc_runway(monthly_total),
            },
            "efficiency": {
                "usd_per_hour": round(usd_per_hour, 2),
                "acceptance_rate": round(overall_acceptance * 100, 1),
                "time_to_payout_avg_days": self._metrics.time_metrics().get("avg_days_to_payout", 0),
            },
            "pipeline": {
                "findings_total": pipeline.get("total", 0),
                "confirmed": pipeline.get("confirmed", 0),
                "submitted": pipeline.get("submitted", 0),
                "accepted": pipeline.get("accepted", 0),
            },
            "top_platform": top_platform,
            "cycles": cycle_status,
            "generated_at": now.isoformat(),
        }

    def _get_weekly_payouts(self, since: datetime) -> list[dict[str, Any]]:
        from database.db import SessionLocal
        from database.models_economic import PayoutRecord

        session = SessionLocal()
        try:
            payouts = (
                session.query(PayoutRecord)
                .filter(
                    PayoutRecord.status == "confirmed",
                    PayoutRecord.paid_at >= since,
                )
                .all()
            )
            return [
                {
                    "id": p.id,
                    "amount": p.amount,
                    "platform": p.platform,
                    "program": p.program,
                    "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                }
                for p in payouts
            ]
        finally:
            session.close()

    def _get_monthly_payouts(self, since: datetime) -> list[dict[str, Any]]:
        from database.db import SessionLocal
        from database.models_economic import PayoutRecord

        session = SessionLocal()
        try:
            payouts = (
                session.query(PayoutRecord)
                .filter(
                    PayoutRecord.status == "confirmed",
                    PayoutRecord.paid_at >= since,
                )
                .all()
            )
            return [{"amount": p.amount, "platform": p.platform} for p in payouts]
        finally:
            session.close()

    def _calc_runway(self, monthly: float) -> float:
        """Calculate months of runway at current monthly revenue (assuming 30k target)."""
        target = 30000.0
        if monthly <= 0:
            return 0.0
        return round(target / monthly, 1)

    def _get_cycle_status(self) -> dict[str, Any]:
        """Get status of all work cycles."""
        try:
            from core.cycles import get_cycle_service

            svc = get_cycle_service()
            cycles = svc.list(enabled_only=True)
            return {
                c.slug: {
                    "name": c.name,
                    "status": c.status,
                    "metrics": svc.get_metrics(c.id),
                }
                for c in cycles
            }
        except Exception as e:
            logger.warning("Failed to get cycle status: %s", e)
            return {}

    def get_weekly_trend(self, weeks: int = 12) -> list[dict[str, Any]]:
        """Weekly revenue trend for charting."""
        from sqlalchemy import func

        from database.db import SessionLocal
        from database.models_economic import PayoutRecord

        session = SessionLocal()
        try:
            cutoff = datetime.now(UTC) - timedelta(weeks=weeks)
            results = (
                session.query(
                    func.date_trunc("week", PayoutRecord.paid_at).label("week"),
                    func.sum(PayoutRecord.amount).label("total"),
                    func.count(PayoutRecord.id).label("count"),
                )
                .filter(
                    PayoutRecord.status == "confirmed",
                    PayoutRecord.paid_at >= cutoff,
                )
                .group_by("week")
                .order_by("week")
                .all()
            )
            return [
                {"week": r.week.isoformat() if r.week else "", "total": float(r.total), "count": r.count}
                for r in results
            ]
        finally:
            session.close()

    def get_platform_breakdown(self) -> dict[str, Any]:
        """Revenue by platform with trend."""
        platform_data = self._metrics.payout_summary().get("by_platform", {})
        return {
            "by_platform": platform_data,
            "total": sum(platform_data.values()),
            "platforms_count": len(platform_data),
        }


_EXECUTIVE_DASHBOARD: ExecutiveDashboard | None = None


def get_executive_dashboard() -> ExecutiveDashboard:
    """Get the global ExecutiveDashboard instance."""
    global _EXECUTIVE_DASHBOARD
    if _EXECUTIVE_DASHBOARD is None:
        _EXECUTIVE_DASHBOARD = ExecutiveDashboard()
    return _EXECUTIVE_DASHBOARD
