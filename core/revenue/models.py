from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Payment:
    id: str
    platform: str
    opportunity_id: str
    amount_usd: float
    amount_ars: float | None = None
    exchange_rate: float | None = None
    status: str = "pending"
    method: str = "unknown"
    paid_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "opportunity_id": self.opportunity_id,
            "amount_usd": self.amount_usd,
            "amount_ars": self.amount_ars,
            "exchange_rate": self.exchange_rate,
            "status": self.status,
            "method": self.method,
            "paid_at": self.paid_at,
            "created_at": self.created_at,
        }


@dataclass
class RevenueRecord:
    id: str
    date: str
    source_type: str
    platform: str
    opportunity: str
    reward_usd: float
    status: str = "discovered"
    payment_id: str | None = None
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date,
            "source_type": self.source_type,
            "platform": self.platform,
            "opportunity": self.opportunity,
            "reward_usd": self.reward_usd,
            "status": self.status,
            "payment_id": self.payment_id,
            "notes": self.notes,
            "created_at": self.created_at,
        }


@dataclass
class ArgentinaPaymentMethod:
    name: str
    display_name: str
    platform_support: list[str]
    fee_percent: float = 0.0
    speed_days: float = 3.0
    min_amount_usd: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "platform_support": self.platform_support,
            "fee_percent": self.fee_percent,
            "speed_days": self.speed_days,
            "min_amount_usd": self.min_amount_usd,
            "notes": self.notes,
        }


ARGENTINA_METHODS: dict[str, ArgentinaPaymentMethod] = {
    "paypal": ArgentinaPaymentMethod(
        name="paypal",
        display_name="PayPal",
        platform_support=["hackerone", "bugcrowd", "fiverr", "upwork"],
        fee_percent=4.5,
        speed_days=5.0,
        min_amount_usd=10.0,
        notes="May have withdrawal restrictions for Argentina",
    ),
    "payoneer": ArgentinaPaymentMethod(
        name="payoneer",
        display_name="Payoneer",
        platform_support=["fiverr", "upwork", "freelancer"],
        fee_percent=2.0,
        speed_days=3.0,
        min_amount_usd=20.0,
        notes="Works well for Argentina, supports ARS withdrawal",
    ),
    "wise": ArgentinaPaymentMethod(
        name="wise",
        display_name="Wise (TransferWise)",
        platform_support=["bugcrowd", "hackerone", "upwork"],
        fee_percent=1.5,
        speed_days=1.0,
        min_amount_usd=5.0,
        notes="Best conversion rates USD → ARS",
    ),
    "cripto": ArgentinaPaymentMethod(
        name="cripto",
        display_name="Criptomonedas (USDT/USDC)",
        platform_support=["many"],
        fee_percent=0.5,
        speed_days=0.5,
        min_amount_usd=1.0,
        notes="Fastest, lowest fees, volatile to convert to ARS",
    ),
    "transferencia": ArgentinaPaymentMethod(
        name="transferencia",
        display_name="Transferencia Bancaria Internacional",
        platform_support=["manual"],
        fee_percent=3.0,
        speed_days=5.0,
        min_amount_usd=50.0,
        notes="Traditional international wire transfer",
    ),
}


@dataclass
class RevenueStats:
    period_days: int = 30
    total_usd: float = 0.0
    pending_usd: float = 0.0
    accepted_usd: float = 0.0
    paid_usd: float = 0.0
    by_platform: dict[str, float] = field(default_factory=dict)
    by_source_type: dict[str, float] = field(default_factory=dict)
    monthly_goal_usd: float = 1000.0
    daily_goal_usd: float = 50.0
    days_active: int = 0
    opportunities_discovered: int = 0
    opportunities_accepted: int = 0
    opportunities_completed: int = 0
    win_rate_pct: float = 0.0
    avg_payout_usd: float = 0.0

    def update(self, records: list[RevenueRecord], payments: list[Payment]) -> None:
        self.total_usd = sum(r.reward_usd for r in records)
        self.pending_usd = sum(r.reward_usd for r in records if r.status == "pending")
        self.accepted_usd = sum(r.reward_usd for r in records if r.status == "accepted")
        self.paid_usd = sum(p.amount_usd for p in payments if p.status == "paid")
        self.days_active = len({r.date for r in records}) if records else 0
        self.opportunities_discovered = len(records)
        self.opportunities_accepted = sum(1 for r in records if r.status in ("accepted", "paid", "completed"))
        self.opportunities_completed = sum(1 for r in records if r.status in ("paid", "completed"))
        if self.opportunities_accepted > 0:
            self.win_rate_pct = round(self.opportunities_completed / self.opportunities_accepted * 100, 1)
        if self.opportunities_completed > 0:
            total = sum(r.reward_usd for r in records if r.status in ("paid", "completed"))
            self.avg_payout_usd = round(total / self.opportunities_completed, 2)
        for r in records:
            self.by_platform[r.platform] = self.by_platform.get(r.platform, 0.0) + r.reward_usd
            self.by_source_type[r.source_type] = self.by_source_type.get(r.source_type, 0.0) + r.reward_usd

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_days": self.period_days,
            "total_usd": round(self.total_usd, 2),
            "pending_usd": round(self.pending_usd, 2),
            "accepted_usd": round(self.accepted_usd, 2),
            "paid_usd": round(self.paid_usd, 2),
            "by_platform": {k: round(v, 2) for k, v in self.by_platform.items()},
            "by_source_type": {k: round(v, 2) for k, v in self.by_source_type.items()},
            "monthly_goal_usd": self.monthly_goal_usd,
            "daily_goal_usd": self.daily_goal_usd,
            "days_active": self.days_active,
            "opportunities_discovered": self.opportunities_discovered,
            "opportunities_accepted": self.opportunities_accepted,
            "opportunities_completed": self.opportunities_completed,
            "win_rate_pct": self.win_rate_pct,
            "avg_payout_usd": self.avg_payout_usd,
        }


DAILY_CYCLE_ORDER = [
    "discovery",
    "scoring",
    "preparation",
    "execution",
    "delivery",
    "validation",
    "payment",
    "learning",
]
