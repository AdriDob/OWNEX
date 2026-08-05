"""Finance Engine — Intelligence layer for personal finance command center."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from cores.finance.models import (
    FinancialSummary,
    FreedomProgress,
    Opportunity,
    OpportunityStatus,
    TransactionType,
)
from cores.finance.store import FinanceStore, get_finance_store

logger = logging.getLogger("ownex.finance.engine")


class FinanceEngine:
    """Core intelligence engine for personal finance."""

    def __init__(self, store: FinanceStore | None = None):
        self.store = store or get_finance_store()

    # ── Transaction Analysis ──
    def analyze_spending(self, days: int = 30) -> dict[str, Any]:
        """Analyze spending patterns over the last N days."""
        end_date = datetime.now(UTC).isoformat()
        start_date = (datetime.now(UTC).replace(day=1)).isoformat()  # Simple month start

        expenses = self.store.get_transactions(
            type_=TransactionType.EXPENSE,
            start_date=start_date,
            end_date=end_date,
        )

        by_category: dict[str, Decimal] = defaultdict(Decimal)
        by_source: dict[str, Decimal] = defaultdict(Decimal)
        total = Decimal("0")

        for txn in expenses:
            by_category[txn.category] += txn.amount
            by_source[txn.source] += txn.amount
            total += txn.amount

        return {
            "period_days": days,
            "total_expenses": str(total),
            "by_category": {k: str(v) for k, v in sorted(by_category.items(), key=lambda x: x[1], reverse=True)},
            "by_source": {k: str(v) for k, v in sorted(by_source.items(), key=lambda x: x[1], reverse=True)},
            "transaction_count": len(expenses),
        }

    def analyze_income(self, days: int = 30) -> dict[str, Any]:
        """Analyze income patterns over the last N days."""
        end_date = datetime.now(UTC).isoformat()
        start_date = (datetime.now(UTC).replace(day=1)).isoformat()

        income = self.store.get_transactions(
            type_=TransactionType.INCOME,
            start_date=start_date,
            end_date=end_date,
        )

        by_category: dict[str, Decimal] = defaultdict(Decimal)
        by_source: dict[str, Decimal] = defaultdict(Decimal)
        total = Decimal("0")

        for txn in income:
            by_category[txn.category] += txn.amount
            by_source[txn.source] += txn.amount
            total += txn.amount

        return {
            "period_days": days,
            "total_income": str(total),
            "by_category": {k: str(v) for k, v in sorted(by_category.items(), key=lambda x: x[1], reverse=True)},
            by_source: {k: str(v) for k, v in sorted(by_source.items(), key=lambda x: x[1], reverse=True)},
            "transaction_count": len(income),
        }

    # ── Opportunity Intelligence ──
    def calculate_opportunity_ev(self, opportunity: Opportunity) -> float:
        """Calculate Expected Value per hour for an opportunity."""
        if opportunity.human_time_hours <= 0:
            return 0.0
        expected = float(opportunity.expected_reward) * opportunity.success_probability
        return expected / opportunity.human_time_hours

    def rank_opportunities_by_ev(self, opportunities: list[Opportunity] | None = None) -> list[Opportunity]:
        """Rank opportunities by Expected Value per hour."""
        opps = opportunities or self.store.get_opportunities()
        for opp in opps:
            opp.ev_score = self.calculate_opportunity_ev(opp)
        return sorted(opps, key=lambda o: o.ev_score, reverse=True)

    def get_top_opportunities(self, limit: int = 10) -> list[Opportunity]:
        """Get top opportunities by EV."""
        ranked = self.rank_opportunities_by_ev()
        return ranked[:limit]

    def get_opportunities_by_status(self, status: OpportunityStatus) -> list[Opportunity]:
        return self.store.get_opportunities(status=status)

    def get_pipeline_summary(self) -> dict[str, int]:
        """Get count of opportunities by status."""
        counts = {}
        for status in OpportunityStatus:
            counts[status.value] = len(self.store.get_opportunities(status=status))
        return counts

    # ── Work Income Analysis ──
    def analyze_work_income(self, days: int = 30) -> dict[str, Any]:
        """Analyze completed work income."""
        records = self.store.get_work_income()

        # Filter by date if needed
        cutoff = datetime.now(UTC).replace(day=1).isoformat()
        recent = [r for r in records if r.completed_at >= cutoff]

        total_reward = sum(r.reward for r in recent)
        total_hours = sum(r.time_invested_hours for r in recent)
        avg_profit_per_hour = float(total_reward) / total_hours if total_hours > 0 else 0.0

        by_platform: dict[str, dict] = defaultdict(lambda: {"reward": Decimal("0"), "hours": 0.0, "count": 0})
        by_category: dict[str, dict] = defaultdict(lambda: {"reward": Decimal("0"), "hours": 0.0, "count": 0})

        for r in recent:
            p = by_platform[r.platform]
            p["reward"] += r.reward
            p["hours"] += r.time_invested_hours
            p["count"] += 1

            c = by_category[r.category.value if hasattr(r.category, "value") else r.category]
            c["reward"] += r.reward
            c["hours"] += r.time_invested_hours
            c["count"] += 1

        platform_stats = {
            k: {
                "total_reward": str(v["reward"]),
                "total_hours": v["hours"],
                "count": v["count"],
                "avg_per_hour": float(v["reward"]) / v["hours"] if v["hours"] > 0 else 0.0,
            }
            for k, v in by_platform.items()
        }

        category_stats = {
            k: {
                "total_reward": str(v["reward"]),
                "total_hours": v["hours"],
                "count": v["count"],
                "avg_per_hour": float(v["reward"]) / v["hours"] if v["hours"] > 0 else 0.0,
            }
            for k, v in by_category.items()
        }

        return {
            "period_days": 30,
            "total_records": len(recent),
            "total_reward": str(sum(r.reward for r in recent)),
            "total_hours": total_hours,
            "avg_profit_per_hour": round(avg_profit_per_hour, 2),
            "by_platform": platform_stats,
            "by_category": category_stats,
        }

    def get_work_income_by_platform(self, platform: str) -> dict[str, Any]:
        records = self.store.get_work_income_by_platform(platform)
        total_reward = sum(r.reward for r in records)
        total_hours = sum(r.time_invested_hours for r in records)
        return {
            "platform": platform,
            "total_records": len(records),
            "total_reward": str(sum(r.reward for r in records)),
            "total_hours": total_hours,
            "avg_profit_per_hour": float(total_reward) / total_hours if total_hours > 0 else 0.0,
        }

    # ── Budget Analysis ──
    def get_budget_status(self) -> list[dict]:
        """Get all budget categories with utilization."""
        budgets = self.store.get_all_budgets()
        return [b.to_dict() for b in budgets]

    def check_budget_alerts(self, threshold: float = 80.0) -> list[dict]:
        """Check for budgets exceeding threshold."""
        alerts = []
        for budget in self.store.get_all_budgets():
            if budget.utilization_pct >= threshold:
                alerts.append(
                    {
                        "category": budget.category,
                        "utilization_pct": round(budget.utilization_pct, 1),
                        "allocated": str(budget.allocated),
                        "spent": str(budget.spent),
                        "remaining": str(budget.remaining),
                    }
                )
        return alerts

    # ── Financial Summary Generation ──
    def generate_monthly_summary(self) -> FinancialSummary:
        """Generate a monthly financial summary."""
        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        period_end = now.isoformat()

        income_data = self.analyze_income(30)
        expense_data = self.analyze_spending(30)
        work_data = self.analyze_work_income(30)

        total_income = Decimal(income_data["total_income"])
        total_expenses = Decimal(expense_data["total_expenses"])
        net_income = total_income - total_expenses

        # Get opportunity pipeline
        pipeline = self.get_pipeline_summary()
        total_opps = sum(pipeline.values())
        completed = pipeline.get("completed", 0) + pipeline.get("paid", 0)
        pending = sum(v for k, v in pipeline.items() if k not in ("completed", "paid"))

        # Top platforms by reward
        work_data_platforms = work_data.get("by_platform", {})
        top_platforms = sorted(
            [(k, float(v["total_reward"])) for k, v in work_data_platforms.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        # Savings rate
        savings_rate = float(net_income / total_income * 100) if total_income > 0 else 0.0

        summary = FinancialSummary(
            period_start=period_start,
            period_end=period_end,
            total_income=total_income,
            total_expenses=total_expenses,
            net_income=net_income,
            total_opportunities=sum(pipeline.values()),
            completed_opportunities=completed,
            pending_opportunities=pending,
            total_work_hours=work_data["total_hours"],
            avg_profit_per_hour=work_data["avg_profit_per_hour"],
            top_platforms=[{"platform": p[0], "reward": p[1]} for p in top_platforms],
            top_categories=[],  # Could be expanded
            savings_rate=round(savings_rate, 1),
        )

        self.store.add_summary(summary)
        return summary

    def get_latest_summary(self) -> FinancialSummary | None:
        summaries = self.store.get_summaries(limit=1)
        return summaries[0] if summaries else None

    # ── Freedom Progress ──
    def calculate_freedom_progress(self) -> FreedomProgress:
        """Calculate financial freedom progress."""
        # Get recent income (last 6 months)
        income_data = self.analyze_income(180)
        work_data = self.analyze_work_income(180)

        monthly_avg = Decimal(income_data["total_income"]) / 6
        work_monthly = Decimal(work_data["total_reward"]) / 6

        # Recurring income = platforms with consistent monthly income
        recurring = monthly_avg * Decimal("0.5")  # Conservative estimate

        fp = self.store.get_freedom_progress()
        fp.current_monthly_avg = monthly_avg
        fp.recurring_income = recurring
        fp.active_income_systems = len(self.store.get_work_income())

        # Progress towards target
        if fp.monthly_target > 0:
            fp.progress_pct = float(monthly_avg / fp.monthly_target * 100)
            if monthly_avg > 0:
                fp.months_to_target = float(fp.monthly_target / monthly_avg)
            else:
                fp.months_to_target = 999.0

        # Emergency fund (simplified)
        assets = self.store.get_total_assets_value()
        if monthly_avg > 0:
            fp.emergency_fund_months = float(assets / monthly_avg)

        fp.last_calculated = datetime.now(UTC).isoformat()
        self.store.update_freedom_progress(
            current_monthly_avg=monthly_avg,
            recurring_income=recurring,
            active_income_systems=fp.active_income_systems,
            emergency_fund_months=fp.emergency_fund_months,
            progress_pct=fp.progress_pct,
            months_to_target=fp.months_to_target,
        )

        return fp

    def get_freedom_progress(self) -> FreedomProgress:
        return self.store.get_freedom_progress()

    # ── Daily Financial Briefing ──
    def generate_daily_briefing(self) -> dict[str, Any]:
        """Generate the daily financial briefing report."""
        now = datetime.now(UTC)
        today = now.date().isoformat()

        # Today's transactions
        today_txns = self.store.get_transactions(start_date=today, end_date=today)

        today_income = sum(t.amount for t in today_txns if t.type == TransactionType.INCOME)
        today_expenses = sum(t.amount for t in today_txns if t.type == TransactionType.EXPENSE)

        # Pending opportunities
        pending_opps = self.store.get_opportunities(status=OpportunityStatus.IN_PROGRESS)
        evaluating_opps = self.store.get_opportunities(status=OpportunityStatus.EVALUATING)

        # Top opportunity for today
        top_opps = self.get_top_opportunities(limit=3)

        # Budget alerts
        budget_alerts = self.check_budget_alerts(80.0)

        # Freedom progress
        freedom = self.get_freedom_progress()

        # Work bank status
        from cores.direct_work_engine.workbank import get_workbank

        workbank = get_workbank()
        wb_summary = workbank._summary()

        return {
            "date": today,
            "generated_at": datetime.now(UTC).isoformat(),
            "balance": {
                "today_income": str(today_income),
                "today_expenses": str(today_expenses),
                "today_net": str(today_income - today_expenses),
            },
            "opportunities": {
                "in_progress": len(pending_opps),
                "evaluating": len(evaluating_opps),
                "top_picks": [o.to_dict() for o in top_opps],
            },
            "workbank": {
                "ready_to_deliver": wb_summary.get("ready_to_deliver", 0),
                "weekly_best": len(wb_summary.get("weekly_best", [])),
                "monthly_best": len(wb_summary.get("monthly_best", [])),
            },
            "budget_alerts": budget_alerts,
            "freedom_progress": freedom.to_dict(),
            "recommended_actions": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> list[dict]:
        """Generate actionable recommendations."""
        recommendations = []

        # Check for high-EV opportunities
        top_opps = self.get_top_opportunities(3)
        for opp in top_opps:
            if opp.ev_score > 50:
                recommendations.append(
                    {
                        "type": "opportunity",
                        "priority": "high",
                        "title": f"Start: {opp.title}",
                        "description": f"EV: ${opp.ev_score:.2f}/hr | Platform: {opp.platform}",
                        "action_url": f"/direct-work/opportunities/{opp.id}",
                    }
                )

        # Check budget alerts
        budget_alerts = self.check_budget_alerts(90.0)
        for alert in budget_alerts:
            recommendations.append(
                {
                    "type": "budget",
                    "priority": "high",
                    "title": f"Budget Alert: {alert['category']}",
                    "description": f"Utilization at {alert['utilization_pct']:.0f}%",
                    "action_url": "/finance/budgets",
                }
            )

        # Check for stagnant opportunities
        stale = self.store.get_opportunities(status=OpportunityStatus.DISCOVERED)
        if len(stale) > 10:
            recommendations.append(
                {
                    "type": "pipeline",
                    "priority": "medium",
                    "title": f"{len(stale)} opportunities need evaluation",
                    "description": "Review and move to evaluating or abandon",
                    "action_url": "/finance/opportunities?status=discovered",
                }
            )

        return recommendations


_engine: FinanceEngine | None = None


def get_finance_engine(store: FinanceStore | None = None) -> FinanceEngine:
    """Get the process-wide FinanceEngine singleton."""
    global _engine
    if _engine is None:
        _engine = FinanceEngine(store)
    return _engine
