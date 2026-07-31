"""Withdrawal Tracker — lifecycle management for every withdrawal.

States:
  initiated → pending → completed
                         → failed

Every state transition is recorded in the ledger as an immutable event.
The system NEVER assumes withdrawal success — it must be confirmed via:
  a) API sync (platform supports it)
  b) Manual user confirmation (with proof)
  c) On-chain reorg-safe confirmation (crypto)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from cores.ledger import LedgerEvent, record_event

logger = logging.getLogger("ownex.financial.withdrawal")


# ── Chain confirmation defaults ──────────────────────────────────────

DEFAULT_CONFIRMATIONS_REQUIRED: dict[str, int] = {
    "ethereum": 12,
    "bitcoin": 6,
    "solana": 30,
    "tron": 19,
    "polygon": 64,
    "arbitrum": 64,
    "optimism": 64,
    "base": 64,
    "bsc": 15,
    "avalanche": 12,
    "cosmos": 7,
    "polkadot": 12,
}


# ── Enums ────────────────────────────────────────────────────────────


class WithdrawalStatus(StrEnum):
    INITIATED = "initiated"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfirmationMethod(StrEnum):
    API_VERIFIED = "api_verified"
    MANUAL_PROOF = "manual_proof"
    RECONCILIATION = "reconciliation"
    UNCONFIRMED = "unconfirmed"
    REORG_SAFE = "reorg_safe"


# ── Data classes ─────────────────────────────────────────────────────


@dataclass
class ProofAttachment:
    type: str  # "screenshot", "tx_hash", "bank_statement", "note"
    value: str
    timestamp: str = ""


@dataclass
class WithdrawalEntry:
    id: str
    amount: float
    currency: str
    platform: str  # "hackerone", "ethereum", "binance", etc.
    target_account: str
    method: str  # "bank_transfer", "crypto", "paypal", etc.
    status: WithdrawalStatus
    confirmation: ConfirmationMethod
    confidence: float

    # Crypto-specific
    tx_hash: str = ""
    chain: str = ""  # "ethereum", "bitcoin", "solana", etc.
    destination_address: str = ""
    fee: float = 0.0
    net_amount: float = 0.0
    confirmations: int = 0
    confirmations_required: int = 12
    block_number: int = 0
    block_hash: str = ""

    # Reorg safety
    reorg_risk: float = 0.0
    reorg_depth: int = 0
    last_checked_block: int = 0
    fork_id: str = ""

    # Timestamps and metadata
    created_at: str = ""
    completed_at: str = ""
    updated_at: str = ""
    error: str = ""
    proof: list[ProofAttachment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_settled(self) -> bool:
        return self.status in (WithdrawalStatus.COMPLETED, WithdrawalStatus.FAILED)

    @property
    def is_reorg_safe(self) -> bool:
        return self.confirmations >= self.confirmations_required and self.reorg_risk == 0.0

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
            "tx_hash": self.tx_hash,
            "chain": self.chain,
            "destination_address": self.destination_address,
            "fee": self.fee,
            "net_amount": self.net_amount,
            "confirmations": self.confirmations,
            "confirmations_required": self.confirmations_required,
            "block_number": self.block_number,
            "block_hash": self.block_hash,
            "reorg_risk": self.reorg_risk,
            "reorg_depth": self.reorg_depth,
            "last_checked_block": self.last_checked_block,
            "fork_id": self.fork_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "proof": [{"type": p.type, "value": p.value[:40], "timestamp": p.timestamp} for p in self.proof],
        }


# ── Backward‑compatible alias ────────────────────────────────────────

Withdrawal = WithdrawalEntry


# ── Storage ──────────────────────────────────────────────────────────

_WITHDRAWALS: dict[str, WithdrawalEntry] = {}
_WITHDRAWAL_BY_TX_HASH: dict[str, str] = {}  # tx_hash → withdrawal_id


# ── Helpers ──────────────────────────────────────────────────────────


def _get_confirmations_required(chain: str) -> int:
    return DEFAULT_CONFIRMATIONS_REQUIRED.get(chain.lower(), 12)


def _compute_confidence(
    confirmation: ConfirmationMethod,
    confirmations: int = 0,
    confirmations_required: int = 12,
) -> float:
    if confirmation == ConfirmationMethod.API_VERIFIED:
        return 1.0
    if confirmation == ConfirmationMethod.REORG_SAFE:
        return min(1.0, confirmations / max(confirmations_required, 1))
    if confirmation == ConfirmationMethod.MANUAL_PROOF:
        return 0.8
    if confirmation == ConfirmationMethod.RECONCILIATION:
        return 0.9
    return 0.3


def _get_crypto_sync_manager():
    from cores.crypto.sync_manager import get_crypto_sync_manager

    return get_crypto_sync_manager()


# ── Core lifecycle ───────────────────────────────────────────────────


def create_withdrawal(
    amount: float,
    currency: str,
    platform: str,
    target_account: str,
    method: str,
    fee: float = 0.0,
    metadata: dict[str, Any] | None = None,
    tx_hash: str = "",
    chain: str = "",
    destination_address: str = "",
    block_number: int = 0,
    block_hash: str = "",
    confirmations: int = 0,
) -> WithdrawalEntry:
    now = datetime.now(UTC).isoformat()
    wid = str(uuid.uuid4())
    net = amount - fee
    is_crypto = bool(chain or tx_hash or method == "crypto")

    confirmations_required = _get_confirmations_required(chain) if chain else 12

    event = LedgerEvent.CRYPTO_WITHDRAWAL if is_crypto else LedgerEvent.WITHDRAWAL_REQUESTED
    event_metadata: dict[str, Any] = {
        "method": method,
        "target_account": target_account,
        "fee": fee,
    }
    if chain:
        event_metadata["chain"] = chain
    if tx_hash:
        event_metadata["tx_hash"] = tx_hash

    record_event(
        event=event,
        amount=amount,
        currency=currency,
        description=f"Retiro de {platform} a {target_account} via {method}",
        source="withdrawal_tracker",
        source_id=wid,
        platform=platform,
        metadata=event_metadata,
    )

    w = WithdrawalEntry(
        id=wid,
        amount=amount,
        currency=currency,
        platform=platform,
        target_account=target_account,
        method=method,
        status=WithdrawalStatus.INITIATED,
        confirmation=ConfirmationMethod.UNCONFIRMED,
        confidence=0.3,
        tx_hash=tx_hash,
        chain=chain,
        destination_address=destination_address,
        fee=fee,
        net_amount=net,
        confirmations=confirmations,
        confirmations_required=confirmations_required,
        block_number=block_number,
        block_hash=block_hash,
        created_at=now,
        updated_at=now,
        metadata=metadata or {},
    )
    _WITHDRAWALS[wid] = w
    if tx_hash:
        _WITHDRAWAL_BY_TX_HASH[tx_hash] = wid

    logger.info(
        "Withdrawal initiated: %s — %.2f %s from %s",
        wid[:8],
        amount,
        currency,
        platform,
    )
    return w


def mark_pending(withdrawal_id: str) -> WithdrawalEntry | None:
    w = _WITHDRAWALS.get(withdrawal_id)
    if not w:
        logger.warning("Withdrawal %s not found", withdrawal_id)
        return None
    if w.status != WithdrawalStatus.INITIATED:
        logger.warning("Cannot mark pending: %s is %s", withdrawal_id, w.status.value)
        return None

    w.status = WithdrawalStatus.PENDING
    w.updated_at = datetime.now(UTC).isoformat()
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
) -> WithdrawalEntry | None:
    w = _WITHDRAWALS.get(withdrawal_id)
    if not w:
        logger.warning("Withdrawal %s not found", withdrawal_id)
        return None
    if w.is_settled:
        logger.warning("Cannot complete: %s is already %s", withdrawal_id, w.status.value)
        return None

    if confirmation == ConfirmationMethod.REORG_SAFE and w.chain and w.tx_hash and not w.is_reorg_safe:
        logger.warning(
            "Cannot complete via reorg_safe: %s — only %d/%d confirmations, risk=%.2f",
            withdrawal_id[:8],
            w.confirmations,
            w.confirmations_required,
            w.reorg_risk,
        )
        return None

    now = datetime.now(UTC).isoformat()
    w.status = WithdrawalStatus.COMPLETED
    w.confirmation = confirmation
    w.confidence = _compute_confidence(confirmation, w.confirmations, w.confirmations_required)
    w.completed_at = now
    w.updated_at = now

    if tx_hash:
        old_hash = w.tx_hash
        w.tx_hash = tx_hash
        if old_hash and old_hash != tx_hash and old_hash in _WITHDRAWAL_BY_TX_HASH:
            del _WITHDRAWAL_BY_TX_HASH[old_hash]
        _WITHDRAWAL_BY_TX_HASH[tx_hash] = withdrawal_id

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
            "tx_hash": w.tx_hash,
            "net_amount": w.net_amount,
        },
    )
    logger.info("Withdrawal completed: %s — %.2f %s", withdrawal_id[:8], w.amount, w.currency)
    return w


def fail_withdrawal(
    withdrawal_id: str,
    error: str,
) -> WithdrawalEntry | None:
    w = _WITHDRAWALS.get(withdrawal_id)
    if not w:
        logger.warning("Withdrawal %s not found", withdrawal_id)
        return None
    if w.is_settled:
        logger.warning("Cannot fail: %s is already %s", withdrawal_id, w.status.value)
        return None

    w.status = WithdrawalStatus.FAILED
    w.error = error
    w.updated_at = datetime.now(UTC).isoformat()

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


# ── Queries ──────────────────────────────────────────────────────────


def get_withdrawal(withdrawal_id: str) -> WithdrawalEntry | None:
    return _WITHDRAWALS.get(withdrawal_id)


def get_withdrawal_by_tx_hash(tx_hash: str) -> WithdrawalEntry | None:
    wid = _WITHDRAWAL_BY_TX_HASH.get(tx_hash)
    if not wid:
        return None
    return _WITHDRAWALS.get(wid)


def list_withdrawals(
    status: WithdrawalStatus | None = None,
    platform: str | None = None,
    chain: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    result = list(_WITHDRAWALS.values())
    if status:
        result = [w for w in result if w.status == status]
    if platform:
        result = [w for w in result if w.platform == platform]
    if chain:
        result = [w for w in result if w.chain == chain]
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
        "completion_rate": round(completed_count / max(len(_WITHDRAWALS), 1) * 100, 1),
    }


# ── On‑chain / reorg‑safe operations ─────────────────────────────────


def track_onchain(withdrawal_id: str, wallet_id: str) -> WithdrawalEntry | None:
    """Start monitoring a withdrawal's on‑chain progress via CryptoSyncManager."""
    w = _WITHDRAWALS.get(withdrawal_id)
    if not w:
        logger.warning("Withdrawal %s not found", withdrawal_id)
        return None
    if not w.tx_hash:
        logger.warning("Withdrawal %s has no tx_hash — cannot track on‑chain", withdrawal_id)
        return None

    check_confirmations(wallet_id, w.tx_hash)
    w.updated_at = datetime.now(UTC).isoformat()
    logger.info("Tracking on‑chain: %s — tx %s", withdrawal_id[:8], w.tx_hash[:16])
    return w


def check_confirmations(wallet_id: str, tx_hash: str) -> tuple[int, int, int]:
    """Query CryptoSyncManager snapshot and update a withdrawal's confirmations.

    Returns (confirmations, confirmations_required, block_number).
    """
    withdrawal_id = _WITHDRAWAL_BY_TX_HASH.get(tx_hash)
    if not withdrawal_id:
        logger.warning("No withdrawal tracked for tx_hash %s", tx_hash[:16])
        return (0, 12, 0)

    w = _WITHDRAWALS.get(withdrawal_id)
    if not w:
        return (0, 12, 0)

    try:
        manager = _get_crypto_sync_manager()
        snapshot = manager.get_snapshot(wallet_id)
        if not snapshot:
            return (w.confirmations, w.confirmations_required, w.block_number)

        for wi in snapshot.withdrawals:
            if wi.tx_hash == tx_hash:
                w.confirmations = wi.confirmations
                w.confirmations_required = wi.confirmations_required
                w.last_checked_block = w.confirmations
                w.updated_at = datetime.now(UTC).isoformat()

                if w.confirmations < w.confirmations_required:
                    w.reorg_risk = max(
                        0.0,
                        1.0 - (w.confirmations / max(w.confirmations_required, 1)),
                    )
                else:
                    w.reorg_risk = 0.0
                    w.reorg_depth = w.confirmations - w.confirmations_required

                return (wi.confirmations, wi.confirmations_required, w.block_number)

        return (w.confirmations, w.confirmations_required, w.block_number)
    except Exception as exc:
        logger.error("check_confirmations failed for tx %s: %s", tx_hash[:16], exc)
        return (w.confirmations, w.confirmations_required, w.block_number)


def update_confirmations(wallet_id: str) -> int:
    """Update confirmations for every tracked crypto withdrawal in a wallet's snapshot.

    Returns the number of withdrawals updated.
    """
    updated = 0
    try:
        manager = _get_crypto_sync_manager()
        snapshot = manager.get_snapshot(wallet_id)
        if not snapshot:
            return 0

        for wi in snapshot.withdrawals:
            withdrawal_id = _WITHDRAWAL_BY_TX_HASH.get(wi.tx_hash)
            if not withdrawal_id:
                continue

            w = _WITHDRAWALS.get(withdrawal_id)
            if not w or w.is_settled:
                continue

            w.confirmations = wi.confirmations
            w.confirmations_required = wi.confirmations_required
            w.block_number = wi.block_number if hasattr(wi, "block_number") else w.block_number
            w.last_checked_block = w.confirmations
            w.updated_at = datetime.now(UTC).isoformat()

            if wi.is_finalized():
                w.reorg_risk = 0.0
                w.reorg_depth = w.confirmations - w.confirmations_required

            updated += 1
    except Exception as exc:
        logger.error("update_confirmations failed for %s: %s", wallet_id, exc)

    return updated


def detect_reorg(wallet_id: str) -> list[str]:
    """Detect chain reorganisations by comparing stored confirmations with current chain state.

    Returns list of tx_hashes affected by a detected reorg.
    """
    affected: list[str] = []
    try:
        manager = _get_crypto_sync_manager()
        snapshot = manager.get_snapshot(wallet_id)
        if not snapshot:
            return affected

        for wi in snapshot.withdrawals:
            withdrawal_id = _WITHDRAWAL_BY_TX_HASH.get(wi.tx_hash)
            if not withdrawal_id:
                continue

            w = _WITHDRAWALS.get(withdrawal_id)
            if not w or w.is_settled:
                continue

            prev_confirmations = w.confirmations

            if wi.confirmations < prev_confirmations:
                risk = min(
                    1.0,
                    (prev_confirmations - wi.confirmations) / max(prev_confirmations, 1),
                )
                w.reorg_risk = max(w.reorg_risk, risk)
                w.reorg_depth = 0
                w.confirmations = wi.confirmations
                w.block_hash = ""
                w.fork_id = f"reorg:{wallet_id}:{datetime.now(UTC).isoformat()}"
                affected.append(wi.tx_hash)
                logger.warning(
                    "Reorg detected for tx %s — confirmations dropped from %d to %d",
                    wi.tx_hash[:16],
                    prev_confirmations,
                    wi.confirmations,
                )
            else:
                pass
    except Exception as exc:
        logger.error("detect_reorg failed for %s: %s", wallet_id, exc)

    return affected


def is_reorg_safe(withdrawal_id: str) -> bool:
    """Return True when the withdrawal has enough confirmations and no reorg was detected."""
    w = _WITHDRAWALS.get(withdrawal_id)
    if not w:
        return False
    return w.is_reorg_safe


def auto_finalize(wallet_id: str) -> list[str]:
    """Complete every pending crypto withdrawal that is now reorg‑safe.

    Designed to be called after CryptoSyncManager.sync_wallet(wallet_id).
    Returns list of completed withdrawal IDs.
    """
    update_confirmations(wallet_id)
    detect_reorg(wallet_id)

    completed: list[str] = []
    for withdrawal_id, w in list(_WITHDRAWALS.items()):
        if w.is_settled:
            continue
        if w.status != WithdrawalStatus.PENDING:
            continue
        if not w.chain or not w.tx_hash:
            continue
        if not w.is_reorg_safe:
            continue

        result = complete_withdrawal(
            withdrawal_id,
            confirmation=ConfirmationMethod.REORG_SAFE,
        )
        if result:
            completed.append(withdrawal_id)

    return completed
