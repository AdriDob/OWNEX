from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class SettlementStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class SplitType(StrEnum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    TIERED = "tiered"
    DYNAMIC = "dynamic"


@dataclass(slots=True)
class SettlementSplit:
    recipient_id: str
    split_type: SplitType
    value: float
    currency: str = "USDC"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Settlement:
    id: str
    escrow_id: str
    requester_id: str
    provider_id: str
    total_amount: float
    currency: str = "USDC"
    splits: list[SettlementSplit] = field(default_factory=list)
    status: SettlementStatus = SettlementStatus.PENDING
    fees: dict[str, float] = field(default_factory=dict)
    net_amounts: dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None
    failure_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_split(self, split: SettlementSplit) -> None:
        self.splits.append(split)

    def calculate_net(self, platform_fee_pct: float = 0.025) -> dict[str, float]:
        total = self.total_amount
        platform_fee = total * platform_fee_pct
        provider_share = total - platform_fee
        net = {"provider": provider_share, "platform": platform_fee}
        for split in self.splits:
            if split.split_type == SplitType.PERCENTAGE:
                net[split.recipient_id] = net.get(split.recipient_id, 0) + total * (split.value / 100)
            elif split.split_type == SplitType.FIXED:
                net[split.recipient_id] = net.get(split.recipient_id, 0) + split.value
        self.fees = {"platform": platform_fee}
        self.net_amounts = net
        return net


class SettlementEngine:
    PLATFORM_FEE_PCT = 0.025
    MIN_SETTLEMENT = 0.01

    def __init__(self):
        self._settlements: dict[str, Any] = {}

    def create_settlement(
        self,
        escrow_id: str,
        requester_id: str,
        provider_id: str,
        amount: float,
        currency: str = "USDC",
        splits: list[dict[str, Any]] | None = None,
    ) -> str:
        import uuid

        settlement_id = f"stl_{uuid.uuid4().hex[:12]}"
        settlement = Settlement(
            id=settlement_id,
            escrow_id=escrow_id,
            requester_id=requester_id,
            provider_id=provider_id,
            total_amount=amount,
            currency=currency,
        )
        if splits:
            for s in splits:
                settlement.add_split(
                    SettlementSplit(
                        recipient_id=s["recipient_id"],
                        split_type=SplitType(s["split_type"]),
                        value=s["value"],
                        currency=s.get("currency", "USDC"),
                        metadata=s.get("metadata", {}),
                    )
                )
        self._settlements[settlement_id] = settlement
        return settlement_id

    def process_settlement(self, settlement_id: str) -> bool:
        settlement = self._settlements.get(settlement_id)
        if not settlement or settlement.status != "pending":
            return False
        settlement.status = SettlementStatus.PROCESSING
        settlement.calculate_net(self.PLATFORM_FEE_PCT)
        settlement.status = SettlementStatus.COMPLETED
        settlement.processed_at = datetime.utcnow()
        return True

    def get_settlement(self, settlement_id: str):
        return self._settlements.get(settlement_id)

    def get_provider_earnings(self, provider_id: str) -> float:
        return sum(
            s.net_amounts.get(provider_id, 0)
            for s in self._settlements.values()
            if s.status == SettlementStatus.COMPLETED
        )


settlement_engine = SettlementEngine()
