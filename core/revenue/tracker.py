from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.revenue.models import Payment, RevenueRecord, RevenueStats


class PaymentTracker:
    """Tracks all payments for discovered opportunities."""

    def __init__(self) -> None:
        self._records: list[RevenueRecord] = []
        self._payments: list[Payment] = []

    def add_record(self, record: RevenueRecord) -> None:
        self._records.append(record)

    def add_payment(self, payment: Payment) -> None:
        self._payments.append(payment)
        for rec in self._records:
            if rec.opportunity == payment.opportunity_id and rec.status == "pending":
                rec.status = payment.status
                rec.payment_id = payment.id

    def get_stats(self, period_days: int = 30) -> RevenueStats:
        cutoff = _cutoff_date(period_days)
        recent = [r for r in self._records if r.date >= cutoff]
        stats = RevenueStats(period_days=period_days)
        stats.update(recent, self._payments)
        return stats

    def get_pending(self) -> list[RevenueRecord]:
        return [r for r in self._records if r.status == "pending"]

    def get_by_platform(self, platform: str) -> list[RevenueRecord]:
        return [r for r in self._records if r.platform == platform]

    def get_payments_by_status(self, status: str) -> list[Payment]:
        return [p for p in self._payments if p.status == status]

    def mark_paid(self, payment_id: str, method: str = "unknown") -> None:
        for p in self._payments:
            if p.id == payment_id:
                p.status = "paid"
                p.paid_at = datetime.now(UTC).isoformat()
                p.method = method
                for rec in self._records:
                    if rec.payment_id == payment_id:
                        rec.status = "paid"
                return

    def to_dict(self) -> dict[str, Any]:
        stats = self.get_stats()
        return {
            "stats": stats.to_dict(),
            "recent_records": [r.to_dict() for r in self._records[-20:]],
            "recent_payments": [p.to_dict() for p in self._payments[-20:]],
            "pending_count": len(self.get_pending()),
            "total_records": len(self._records),
            "total_payments": len(self._payments),
        }

    def summary(self) -> str:
        stats = self.get_stats()
        d = stats.to_dict()
        lines = [
            "OWNEX Revenue Summary",
            f"Period: last {d['period_days']} days",
            f"Total USD: ${d['total_usd']:,.2f}",
            f"Pending: ${d['pending_usd']:,.2f}",
            f"Paid: ${d['paid_usd']:,.2f}",
            f"Opportunities: {d['opportunities_completed']} completed / {d['opportunities_accepted']} accepted",
            f"Win rate: {d['win_rate_pct']}%",
            f"Avg payout: ${d['avg_payout_usd']:,.2f}",
        ]
        return "\n".join(lines)


def _cutoff_date(period_days: int) -> str:
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(days=period_days)
    return cutoff.strftime("%Y-%m-%d")
