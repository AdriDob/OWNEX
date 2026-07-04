"""Withdrawal Tracker — lifecycle management for every withdrawal.

States:
  initiated → pending → completed
                         → failed

Every state transition is recorded in the ledger as an immutable event.
The system NEVER assumes withdrawal success — it must be confirmed via:
  a) API sync (platform supports it)
  b) Manual user confirmation (with proof)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from cores.ledger import LedgerEvent, record_event

logger = logging.getLogger("catseye.financial.withdrawal")


class WithdrawalStatus(str, Enum):
    INITIATED = "initiated"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfirmationMethod(str, Enum):
    API_VERIFIED = "api_verified"
    MANUAL_PROOF = "manual_proof"
    RECONCILIATION = "reconciliation"
    UNCONFIRMED = "unconfirmed"


@dataclass
class ProofAttachment:
    type: str  # "screenshot", "tx_hash", "bank_statement", "note"
    value: str
    timestamp: str = ""


@dataclass
class Withdrawal:
    id: str
    amount: float
    currency: str
    platform: str
    target_account: str
    method: str  # "crypto", "bank", "p2p", "payoneer", etc.
    status: WithdrawalStatus
    confirmation: ConfirmationMethod
    created_at: str
    updated_at: str
    completed_at: str = ""
    fee: float = 0.0
    net_amount: float = 0.0
    tx_hash: str = ""
    proof: list[ProofAttachment] = field(default_factory=list)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    ledger_entry_id: str = ""

    @property
    def is_settled(self) -> bool:
        return self.status in (WithdrawalStatus.COMPLETED, WithdrawalStatus.FAILED)

    @property
    def confidence(self) -> float:
        if self.confirmation == ConfirmationMethod.API_VERIFIED:
            return 1.0
        if self.confirmation == ConfirmationMethod.MANUAL_PROOF:
            return 0.8
        if self.confirmation == ConfirmationMethod.RECONCILIATION:
            return 0.9
        return 0.3

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "amount": self.amount,
            "currency": self.currency,
            "platform": self.platform,
            "target_account": self.target_account,
            "method": self.method,
            "status": self.status.value,
            "confirmation": self.confirmation.value,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "fee": self.fee,
            "net_amount": self.net_amount,
            "tx_hash": self.tx_hash,
            "proof": [{"type": p.type, "value": p.value[:40], "timestamp": p.timestamp} for p in self.proof],
            "error": self.error,
            "ledger_entry_id": self.ledger_entry_id,
        }


_WITHDRAWALS: dict[str, Withdrawal] = {}


def create_withdrawal(
    amount: float,
    currency: str,
    platform: str,
    target_account: str,
    method: str,
    fee: float = 0.0,
    metadata: dict[str, Any] | None = None,
) -> Withdrawal:
    now = datetime.now(timezone.utc).isoformat()
    wid = str(uuid.uuid4())
    net = amount - fee

    entry = record_event(
        event=LedgerEvent.WITHDRAWAL_REQUESTED,
        amount=amount,
        currency=currency,
        description=f"Retiro de {platform} a {target_account} via {method}",
        source="withdrawal_tracker",
        source_id=wid,
        platform=platform,
        metadata={"method": method, "target_account": target_account, "fee": fee},
    )

    w = Withdrawal(
        id=wid,
        amount=amount,
        currency=currency,
        platform=platform,
        target_account=target_account,
        method=method,
        status=WithdrawalStatus.INITIATED,
        confirmation=ConfirmationMethod.UNCONFIRMED,
        created_at=now,
        updated_at=now,
        fee=fee,
        net_amount=net,
        metadata=metadata or {},
        ledger_entry_id=entry.entry_id,
    )
    _WITHDRAWALS[wid] = w
    logger.info("Withdrawal initiated: %s — %.2f %s from %s", wid[:8], amount, currency, platform)
    return w


def mark_pending(withdrawal_id: str) -> Withdrawal | None:
    w = _WITHDRAWALS.get(withdrawal_id)
    if not w:
        logger.warning("Withdrawal %s not found", withdrawal_id)
        return None
    if w.status != WithdrawalStatus.INITIATED:
        logger.warning("Cannot mark pending: %s is %s", withdrawal_id, w.status.value)
        return None

    w.status = WithdrawalStatus.PENDING
    w.updated_at = datetime.now(timezone.utc).isoformat()
    record_event(
        event=LedgerEvent.WITHDRAWAL_PROCESSING,
        amount=w.amount,
        currency=w.currency,
        description=f"Retiro en proceso: {withdrawal_id[:8]}",
        source="withdrawal_tracker",
        source_id=withdrawal_id,
        platform=w.platform,
    )
    return w


def complete_withdrawal(
    withdrawal_id: str,
    confirmation: ConfirmationMethod = ConfirmationMethod.MANUAL_PROOF,
    tx_hash: str = "",
    proof: list[ProofAttachment] | None = None,
) -> Withdrawal | None:
    w = _WITHDRAWALS.get(withdrawal_id)
    if not w:
        logger.warning("Withdrawal %s not found", withdrawal_id)
        return None
    if w.is_settled:
        logger.warning("Cannot complete: %s is already %s", withdrawal_id, w.status.value)
        return None

    now = datetime.now(timezone.utc).isoformat()
    w.status = WithdrawalStatus.COMPLETED
    w.confirmation = confirmation
    w.completed_at = now
    w.updated_at = now
    w.tx_hash = tx_hash or w.tx_hash
    if proof:
        w.proof.extend(proof)

    record_event(
        event=LedgerEvent.WITHDRAWAL_COMPLETED,
        amount=w.amount,
        currency=w.currency,
        description=f"Retiro completado: {withdrawal_id[:8]} a {w.target_account}",
        source="withdrawal_tracker",
        source_id=withdrawal_id,
        platform=w.platform,
        metadata={
            "confirmation": confirmation.value,
            "tx_hash": tx_hash,
            "net_amount": w.net_amount,
        },
    )
    logger.info("Withdrawal completed: %s — %.2f %s", withdrawal_id[:8], w.amount, w.currency)
    return w


def fail_withdrawal(
    withdrawal_id: str,
    error: str,
) -> Withdrawal | None:
    w = _WITHDRAWALS.get(withdrawal_id)
    if not w:
        logger.warning("Withdrawal %s not found", withdrawal_id)
        return None
    if w.is_settled:
        logger.warning("Cannot fail: %s is already %s", withdrawal_id, w.status.value)
        return None

    w.status = WithdrawalStatus.FAILED
    w.error = error
    w.updated_at = datetime.now(timezone.utc).isoformat()

    record_event(
        event=LedgerEvent.WITHDRAWAL_FAILED,
        amount=w.amount,
        currency=w.currency,
        description=f"Retiro fallido: {withdrawal_id[:8]} — {error[:100]}",
        source="withdrawal_tracker",
        source_id=withdrawal_id,
        platform=w.platform,
        metadata={"error": error},
    )
    logger.warning("Withdrawal failed: %s — %s", withdrawal_id[:8], error)
    return w


def get_withdrawal(withdrawal_id: str) -> Withdrawal | None:
    return _WITHDRAWALS.get(withdrawal_id)


def list_withdrawals(
    status: WithdrawalStatus | None = None,
    platform: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    result = list(_WITHDRAWALS.values())
    if status:
        result = [w for w in result if w.status == status]
    if platform:
        result = [w for w in result if w.platform == platform]
    result.sort(key=lambda w: w.created_at, reverse=True)
    return [w.to_dict() for w in result[:limit]]


def get_summary() -> dict[str, Any]:
    total_initiated = 0.0
    total_pending = 0.0
    total_completed = 0.0
    total_failed = 0.0
    completed_count = 0
    failed_count = 0

    for w in _WITHDRAWALS.values():
        if w.status == WithdrawalStatus.COMPLETED:
            total_completed += w.net_amount
            completed_count += 1
        elif w.status == WithdrawalStatus.FAILED:
            total_failed += w.amount
            failed_count += 1
        elif w.status == WithdrawalStatus.PENDING:
            total_pending += w.amount
        else:
            total_initiated += w.amount

    return {
        "total_initiated": round(total_initiated, 2),
        "total_pending": round(total_pending, 2),
        "total_completed": round(total_completed, 2),
        "total_failed": round(total_failed, 2),
        "completed_count": completed_count,
        "failed_count": failed_count,
        "total_withdrawals": len(_WITHDRAWALS),
        "completion_rate": round(
            completed_count / max(len(_WITHDRAWALS), 1) * 100, 1
        ),
    }
