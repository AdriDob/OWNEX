from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any


class EscrowStatus(str, Enum):
    CREATED = "created"
    FUNDED = "funded"
    LOCKED = "locked"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    PARTIALLY_RELEASED = "partially_released"


class DisputeResolution(str, Enum):
    PENDING = "pending"
    PROVIDER_WIN = "provider_win"
    REQUESTER_WIN = "requester_win"
    SPLIT = "split"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class EscrowAccount:
    id: str
    requester_id: str
    provider_id: str
    amount: float
    currency: str = "USDC"
    status: EscrowStatus = EscrowStatus.CREATED
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    funded_at: datetime | None = None
    expires_at: datetime | None = None
    released_at: datetime | None = None
    released_amount: float = 0.0
    dispute_id: str | None = None
    auto_release_after: timedelta | None = None
    release_conditions: list[Callable[..., bool]] = field(default_factory=list)


@dataclass(slots=True)
class Dispute:
    id: str
    escrow_id: str
    initiator_id: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)
    status: DisputeResolution = DisputeResolution.PENDING
    resolver_id: str | None = None
    resolution: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None
    split_ratio: float | None = None


class EscrowManager:
    def __init__(self, default_expiry_hours: int = 24):
        self._escrows: dict[str, EscrowAccount] = {}
        self._disputes: dict[str, Dispute] = {}
        self._lock = Lock()
        self._default_expiry = timedelta(hours=default_expiry_hours)
        self._balance_hooks: dict[str, Callable[[str, float], bool]] = {}

    def register_balance_hook(self, currency: str, hook: Callable[[str, float], bool]) -> None:
        self._balance_hooks[currency] = hook

    def create_escrow(
        self,
        requester_id: str,
        provider_id: str,
        amount: float,
        currency: str = "USDC",
        description: str = "",
        expires_in: timedelta | None = None,
        auto_release_after: timedelta | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        escrow_id = f"esc_{uuid.uuid4().hex[:12]}"
        expires_at = datetime.utcnow() + (expires_in or self._default_expiry)
        escrow = EscrowAccount(
            id=escrow_id,
            requester_id=requester_id,
            provider_id=provider_id,
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata or {},
            expires_at=expires_at,
            auto_release_after=auto_release_after,
        )
        with self._lock:
            self._escrows[escrow_id] = escrow
        return escrow_id

    def fund_escrow(self, escrow_id: str, payer_id: str) -> bool:
        with self._lock:
            escrow = self._escrows.get(escrow_id)
            if not escrow or escrow.status != EscrowStatus.CREATED:
                return False
            if payer_id != escrow.requester_id:
                return False
            hook = self._balance_hooks.get(escrow.currency)
            if hook and not hook(payer_id, escrow.amount):
                return False
            escrow.status = EscrowStatus.FUNDED
            escrow.funded_at = datetime.utcnow()
            return True

    def lock_escrow(self, escrow_id: str) -> bool:
        with self._lock:
            escrow = self._escrows.get(escrow_id)
            if not escrow or escrow.status != EscrowStatus.FUNDED:
                return False
            escrow.status = EscrowStatus.LOCKED
            return True

    def release_escrow(self, escrow_id: str, releaser_id: str, amount: float | None = None) -> bool:
        with self._lock:
            escrow = self._escrows.get(escrow_id)
            if not escrow or escrow.status not in (EscrowStatus.FUNDED, EscrowStatus.LOCKED):
                return False
            if releaser_id not in (escrow.requester_id, escrow.provider_id):
                return False
            release_amount = amount or (escrow.amount - escrow.released_amount)
            if release_amount <= 0 or release_amount > escrow.amount - escrow.released_amount:
                return False
            escrow.released_amount += release_amount
            escrow.released_at = datetime.utcnow()
            if escrow.released_amount >= escrow.amount:
                escrow.status = EscrowStatus.RELEASED
            else:
                escrow.status = EscrowStatus.PARTIALLY_RELEASED
            return True

    def refund_escrow(self, escrow_id: str, requester_id: str) -> bool:
        with self._lock:
            escrow = self._escrows.get(escrow_id)
            if not escrow or escrow.requester_id != requester_id:
                return False
            if escrow.status not in (EscrowStatus.FUNDED, EscrowStatus.LOCKED):
                return False
            if escrow.released_amount > 0:
                return False
            escrow.status = EscrowStatus.REFUNDED
            return True

    def open_dispute(
        self,
        escrow_id: str,
        initiator_id: str,
        reason: str,
        evidence: dict[str, Any] | None = None,
    ) -> str | None:
        with self._lock:
            escrow = self._escrows.get(escrow_id)
            if not escrow or escrow.status not in (EscrowStatus.FUNDED, EscrowStatus.LOCKED):
                return None
            if initiator_id not in (escrow.requester_id, escrow.provider_id):
                return None
            dispute_id = f"disp_{uuid.uuid4().hex[:12]}"
            dispute = Dispute(
                id=dispute_id,
                escrow_id=escrow_id,
                initiator_id=initiator_id,
                reason=reason,
                evidence=evidence or {},
            )
            self._disputes[dispute_id] = dispute
            escrow.status = EscrowStatus.DISPUTED
            escrow.dispute_id = dispute_id
            return dispute_id

    def resolve_dispute(
        self,
        dispute_id: str,
        resolver_id: str,
        resolution: DisputeResolution,
        split_ratio: float | None = None,
        resolution_note: str = "",
    ) -> bool:
        with self._lock:
            dispute = self._disputes.get(dispute_id)
            if not dispute or dispute.status != DisputeResolution.PENDING:
                return False
            escrow = self._escrows.get(dispute.escrow_id)
            if not escrow:
                return False
            dispute.status = resolution
            dispute.resolver_id = resolver_id
            dispute.resolution = resolution_note
            dispute.resolved_at = datetime.utcnow()
            if resolution == DisputeResolution.SPLIT:
                dispute.split_ratio = split_ratio or 0.5
                provider_amount = escrow.amount * dispute.split_ratio
                requester_amount = escrow.amount - provider_amount
                escrow.released_amount = provider_amount
                escrow.status = EscrowStatus.PARTIALLY_RELEASED
            elif resolution == DisputeResolution.PROVIDER_WIN:
                escrow.released_amount = escrow.amount
                escrow.status = EscrowStatus.RELEASED
            elif resolution == DisputeResolution.REQUESTER_WIN:
                escrow.status = EscrowStatus.REFUNDED
            return True

    def get_escrow(self, escrow_id: str) -> EscrowAccount | None:
        with self._lock:
            return self._escrows.get(escrow_id)

    def get_dispute(self, dispute_id: str) -> Dispute | None:
        with self._lock:
            return self._disputes.get(dispute_id)

    def list_escrows(
        self,
        requester_id: str | None = None,
        provider_id: str | None = None,
        status: EscrowStatus | None = None,
    ) -> list[EscrowAccount]:
        with self._lock:
            result = list(self._escrows.values())
            if requester_id:
                result = [e for e in result if e.requester_id == requester_id]
            if provider_id:
                result = [e for e in result if e.provider_id == provider_id]
            if status:
                result = [e for e in result if e.status == status]
            return result

    def check_expired(self) -> list[str]:
        now = datetime.utcnow()
        expired = []
        with self._lock:
            for escrow in self._escrows.values():
                if escrow.status in (EscrowStatus.FUNDED, EscrowStatus.LOCKED) and escrow.expires_at <= now:
                    escrow.status = EscrowStatus.EXPIRED
                    expired.append(escrow.id)
        return expired

    def auto_release_ready(self) -> list[str]:
        now = datetime.utcnow()
        released = []
        with self._lock:
            for escrow in self._escrows.values():
                if (
                    escrow.status == EscrowStatus.LOCKED
                    and escrow.auto_release_after
                    and escrow.funded_at
                    and (now - escrow.funded_at) >= escrow.auto_release_after
                ):
                    escrow.released_amount = escrow.amount
                    escrow.released_at = now
                    escrow.status = EscrowStatus.RELEASED
                    released.append(escrow.id)
        return released


escrow_manager = EscrowManager()
