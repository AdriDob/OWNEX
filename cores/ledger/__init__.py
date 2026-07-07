"""Financial ledger — append-only, immutable transaction log, persisted to DB.

Every financial event is recorded as a LedgerEntry. No overwrites.
Balances are computed by replaying the ledger, never stored directly.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger("cateye.ledger")

LEDGER_EVENTS = [
    "bounty_created",
    "bounty_pending",
    "bounty_approved",
    "bounty_rejected",
    "payout_received",
    "withdrawal_requested",
    "withdrawal_processing",
    "withdrawal_completed",
    "withdrawal_failed",
    "adjustment_manual",
    "fee_deducted",
    "currency_converted",
    "crypto_deposit",
    "crypto_withdrawal",
    "crypto_staking_reward",
    "crypto_defi_yield",
    "crypto_swap",
    "crypto_gas_fee",
    "crypto_airdrop",
    "exchange_trade",
    "exchange_fee",
]


class LedgerEvent(str, Enum):
    BOUNTY_CREATED = "bounty_created"
    BOUNTY_PENDING = "bounty_pending"
    BOUNTY_APPROVED = "bounty_approved"
    BOUNTY_REJECTED = "bounty_rejected"
    PAYOUT_RECEIVED = "payout_received"
    WITHDRAWAL_REQUESTED = "withdrawal_requested"
    WITHDRAWAL_PROCESSING = "withdrawal_processing"
    WITHDRAWAL_COMPLETED = "withdrawal_completed"
    WITHDRAWAL_FAILED = "withdrawal_failed"
    ADJUSTMENT_MANUAL = "adjustment_manual"
    FEE_DEDUCTED = "fee_deducted"
    CURRENCY_CONVERTED = "currency_converted"
    CRYPTO_DEPOSIT = "crypto_deposit"
    CRYPTO_WITHDRAWAL = "crypto_withdrawal"
    CRYPTO_STAKING_REWARD = "crypto_staking_reward"
    CRYPTO_DEFI_YIELD = "crypto_defi_yield"
    CRYPTO_SWAP = "crypto_swap"
    CRYPTO_GAS_FEE = "crypto_gas_fee"
    CRYPTO_AIRDROP = "crypto_airdrop"
    EXCHANGE_TRADE = "exchange_trade"
    EXCHANGE_FEE = "exchange_fee"


@dataclass
class LedgerEntryData:
    event: LedgerEvent
    amount: float
    currency: str
    description: str
    source: str
    source_id: str
    platform: str
    timestamp: str
    entry_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    reconciled: bool = False


class DataSource(str, Enum):
    EXTERNAL_API = "external_api"
    SYNCED_CACHE = "synced_cache"
    MANUAL_INPUT = "manual_input"
    SEED_DATA = "seed_data"
    SYSTEM = "system"


@dataclass
class WalletState:
    available_balance: float = 0.0
    pending_balance: float = 0.0
    locked_balance: float = 0.0

    @property
    def total_balance(self) -> float:
        return self.available_balance + self.pending_balance + self.locked_balance

    def to_dict(self) -> dict[str, float]:
        return {
            "available": round(self.available_balance, 2),
            "pending": round(self.pending_balance, 2),
            "locked": round(self.locked_balance, 2),
            "total": round(self.total_balance, 2),
        }


def _get_session() -> Session:
    from database.db import SessionLocal
    return SessionLocal()


def _row_to_entry(row: Any) -> LedgerEntryData:
    return LedgerEntryData(
        event=LedgerEvent(row.event),
        amount=row.amount,
        currency=row.currency,
        description=row.description or "",
        source=row.source or "system",
        source_id=row.source_id or "",
        platform=row.platform or "internal",
        timestamp=row.timestamp,
        entry_id=row.entry_id,
        metadata=json.loads(row.metadata_json or "{}"),
        reconciled=bool(row.reconciled),
    )


def record_event(
    event: LedgerEvent,
    amount: float,
    currency: str = "USD",
    description: str = "",
    source: str = "system",
    source_id: str = "",
    platform: str = "internal",
    metadata: dict[str, Any] | None = None,
) -> LedgerEntryData:
    import uuid

    from database.models import LedgerEntry as LedgerEntryModel

    entry_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    metadata_json = json.dumps(metadata or {})

    session = _get_session()
    try:
        model = LedgerEntryModel(
            entry_id=entry_id,
            event=event.value,
            amount=amount,
            currency=currency,
            description=description,
            source=source,
            source_id=source_id,
            platform=platform,
            timestamp=timestamp,
            metadata_json=metadata_json,
        )
        session.add(model)
        session.commit()
    finally:
        session.close()

    entry = LedgerEntryData(
        event=event,
        amount=amount,
        currency=currency,
        description=description,
        source=source,
        source_id=source_id,
        platform=platform,
        timestamp=timestamp,
        entry_id=entry_id,
        metadata=metadata or {},
    )
    logger.info("Ledger: %s %s %.2f %s (%s)", event.value, source, amount, description, platform)
    return entry


def _all_entries() -> list[LedgerEntryData]:
    """Return all ledger entries sorted by timestamp descending."""
    from database.models import LedgerEntry as LedgerEntryModel

    session = _get_session()
    try:
        rows = session.query(LedgerEntryModel).order_by(LedgerEntryModel.id.desc()).all()
        return [_row_to_entry(r) for r in rows]
    finally:
        session.close()


def compute_wallet() -> WalletState:
    w = WalletState()
    for e in _all_entries():
        if e.event in (LedgerEvent.PAYOUT_RECEIVED, LedgerEvent.ADJUSTMENT_MANUAL,
                       LedgerEvent.CRYPTO_DEPOSIT, LedgerEvent.CRYPTO_STAKING_REWARD,
                       LedgerEvent.CRYPTO_DEFI_YIELD, LedgerEvent.CRYPTO_AIRDROP):
            w.available_balance += e.amount
        elif e.event in (LedgerEvent.BOUNTY_APPROVED, LedgerEvent.BOUNTY_PENDING):
            w.pending_balance += e.amount
        elif e.event == LedgerEvent.WITHDRAWAL_PROCESSING:
            w.locked_balance += e.amount
            w.available_balance -= e.amount
        elif e.event == LedgerEvent.WITHDRAWAL_COMPLETED:
            w.locked_balance -= e.amount
        elif e.event in (LedgerEvent.BOUNTY_REJECTED, LedgerEvent.WITHDRAWAL_FAILED):
            w.pending_balance -= e.amount if e.event == LedgerEvent.BOUNTY_REJECTED else 0
            w.locked_balance -= e.amount if e.event == LedgerEvent.WITHDRAWAL_FAILED else 0
        elif e.event in (LedgerEvent.FEE_DEDUCTED, LedgerEvent.CRYPTO_GAS_FEE,
                         LedgerEvent.EXCHANGE_FEE, LedgerEvent.CRYPTO_SWAP):
            w.available_balance -= e.amount
    return w


def get_history(limit: int = 100) -> list[dict[str, Any]]:
    from database.models import LedgerEntry as LedgerEntryModel

    session = _get_session()
    try:
        rows = session.query(LedgerEntryModel).order_by(LedgerEntryModel.id.desc()).limit(limit).all()
        return [
            {
                "id": r.entry_id,
                "event": r.event,
                "amount": r.amount,
                "currency": r.currency,
                "description": r.description,
                "source": r.source,
                "source_id": r.source_id,
                "platform": r.platform,
                "timestamp": r.timestamp,
                "reconciled": bool(r.reconciled),
                "metadata": json.loads(r.metadata_json or "{}"),
            }
            for r in rows
        ]
    finally:
        session.close()


def reconcile() -> dict[str, Any]:
    w = compute_wallet()
    issues = []
    if w.available_balance < 0:
        issues.append("Negative available balance")
    if w.pending_balance < 0:
        issues.append("Negative pending balance")
    if w.locked_balance < 0:
        issues.append("Negative locked balance")
    return {
        "wallet": w.to_dict(),
        "entry_count": len(_all_entries()),
        "issues": issues,
        "healthy": len(issues) == 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# Backward-compatible alias for modules that imported _entries directly.
# New code should call _all_entries() instead.
_entries: list[LedgerEntryData] = []
