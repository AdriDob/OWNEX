from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.revenue.converter import usd_to_ars
from core.revenue.discovery import discover_daily_opportunities
from core.revenue.models import (
    ARGENTINA_METHODS,
    Payment,
    RevenueRecord,
    RevenueStats,
)
from core.revenue.tracker import PaymentTracker

logger = logging.getLogger("ownex.revenue")


class RevenueEngine:
    """Ownex Revenue Engine — discovers, scores, tracks, and reports on opportunities."""

    name = "revenue_engine"

    def __init__(self) -> None:
        self._tracker = PaymentTracker()
        self._exchange_rate = 1000.0

    def set_exchange_rate(self, rate: float) -> None:
        self._exchange_rate = rate

    def discover(self, scored_opps: list[Any], top_n: int = 10) -> list[dict[str, Any]]:
        """Run daily discovery on scored opportunities."""
        results = discover_daily_opportunities(scored_opps, top_n=top_n)
        for r in results:
            record = RevenueRecord(
                id=r["id"],
                date=r["date"],
                source_type=r["source_type"],
                platform=r["platform"],
                opportunity=r["name"],
                reward_usd=r["reward_usd"],
                status="discovered",
            )
            self._tracker.add_record(record)
        logger.info("Discovered %d daily opportunities", len(results))
        return results

    def score(self, record_id: str, score_overall: float) -> None:
        """Score a discovered opportunity."""
        for rec in self._tracker._records:
            if rec.id == record_id:
                rec.status = "scored"
                rec.notes = f"score={score_overall:.2f}"
                break

    def prepare(self, record_id: str, task_package: dict[str, Any]) -> None:
        """Prepare a task package for execution."""
        for rec in self._tracker._records:
            if rec.id == record_id:
                rec.status = "prepared"
                rec.notes = f"package={task_package.get('id', '?')}"
                break

    def execute(self, record_id: str) -> None:
        """Mark opportunity as in execution."""
        for rec in self._tracker._records:
            if rec.id == record_id:
                rec.status = "executing"
                break

    def deliver(self, record_id: str) -> None:
        """Mark opportunity as delivered (PR submitted / report sent)."""
        for rec in self._tracker._records:
            if rec.id == record_id:
                rec.status = "delivered"
                break

    def validate(self, record_id: str) -> None:
        """Mark opportunity as accepted / validated."""
        for rec in self._tracker._records:
            if rec.id == record_id:
                rec.status = "accepted"
                break

    def process_payment(
        self,
        record_id: str,
        amount_usd: float,
        method: str = "wise",
        platform: str = "unknown",
    ) -> Payment:
        """Process a payment for a completed opportunity."""
        payment_id = f"pay_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        payment = Payment(
            id=payment_id,
            platform=platform,
            opportunity_id=record_id,
            amount_usd=amount_usd,
            amount_ars=usd_to_ars(amount_usd, self._exchange_rate),
            exchange_rate=self._exchange_rate,
            status="pending",
            method=method,
        )

        self._tracker.add_payment(payment)

        for rec in self._tracker._records:
            if rec.id == record_id:
                rec.status = "paid"
                rec.payment_id = payment_id
                rec.reward_usd = amount_usd
                break

        logger.info("Payment processed: %s $%.2f via %s", payment_id, amount_usd, method)
        return payment

    def get_stats(self, period_days: int = 30) -> RevenueStats:
        return self._tracker.get_stats(period_days)

    def summary(self) -> str:
        return self._tracker.summary()

    def health(self) -> dict[str, Any]:
        stats = self.get_stats()
        d = stats.to_dict()
        return {
            "status": "ok",
            "name": self.name,
            "period_days": d["period_days"],
            "total_usd": d["total_usd"],
            "pending_usd": d["pending_usd"],
            "paid_usd": d["paid_usd"],
            "opportunities_completed": d["opportunities_completed"],
            "win_rate_pct": d["win_rate_pct"],
            "avg_payout_usd": d["avg_payout_usd"],
            "exchange_rate": self._exchange_rate,
            "payment_methods_supported": list(ARGENTINA_METHODS.keys()),
        }

    def available_methods(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in ARGENTINA_METHODS.values()]
