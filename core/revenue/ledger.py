"""Revenue Ledger — Single Source of Truth for OWNEX economic state.

States: DISCOVERED → COMMITTED → IN_PROGRESS → DELIVERED → SUBMITTED → ACCEPTED → AWARDED → PENDING_PAYOUT → PAID → NET
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func

from database.db import Base, SessionLocal

logger = logging.getLogger("ownex.revenue.ledger")


class RevenueState(StrEnum):
    """Economic states in the revenue pipeline."""

    DISCOVERED = "discovered"  # Opportunity found
    COMMITTED = "committed"  # Decided to pursue
    IN_PROGRESS = "in_progress"  # Active work
    DELIVERED = "delivered"  # Work submitted to platform
    SUBMITTED = "submitted"  # Acknowledged by platform
    ACCEPTED = "accepted"  # Platform accepted
    REJECTED = "rejected"  # Platform rejected
    AWARDED = "awarded"  # Bounty/award granted
    PENDING_PAYOUT = "pending_payout"  # Waiting for payment
    PAID = "paid"  # Money received
    NET = "net"  # After fees/taxes


class RevenueLedgerEntry(Base):
    """SQLAlchemy model for revenue ledger entries."""

    __tablename__ = "revenue_ledger"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(String(64), unique=True, nullable=False, index=True)
    mission_id = Column(String(64), nullable=True, index=True)
    opportunity_id = Column(String(64), nullable=True, index=True)
    platform = Column(String(64), nullable=True, index=True)

    state = Column(String(32), nullable=False, default=RevenueState.DISCOVERED.value, index=True)
    previous_state = Column(String(32), nullable=True)

    gross_usd = Column(Float, default=0.0)
    fees_usd = Column(Float, default=0.0)
    fx_usd = Column(Float, default=0.0)
    tax_estimate_usd = Column(Float, default=0.0)
    net_usd = Column(Float, default=0.0)

    payment_method = Column(String(64), nullable=True)
    external_id = Column(String(128), nullable=True)

    metadata_json = Column(Text, default="{}")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    state_changed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entry_id": self.entry_id,
            "mission_id": self.mission_id,
            "opportunity_id": self.opportunity_id,
            "platform": self.platform,
            "state": self.state,
            "previous_state": self.previous_state,
            "gross_usd": self.gross_usd,
            "fees_usd": self.fees_usd,
            "fx_usd": self.fx_usd,
            "tax_estimate_usd": self.tax_estimate_usd,
            "net_usd": self.net_usd,
            "payment_method": self.payment_method,
            "external_id": self.external_id,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "state_changed_at": self.state_changed_at.isoformat() if self.state_changed_at else None,
        }


class RevenueTransition:
    """Valid state transitions in the revenue pipeline."""

    VALID_TRANSITIONS: dict[RevenueState, set[RevenueState]] = {
        RevenueState.DISCOVERED: {RevenueState.COMMITTED, RevenueState.DISCOVERED},
        RevenueState.COMMITTED: {RevenueState.IN_PROGRESS, RevenueState.DISCOVERED},
        RevenueState.IN_PROGRESS: {RevenueState.DELIVERED, RevenueState.COMMITTED},
        RevenueState.DELIVERED: {RevenueState.SUBMITTED, RevenueState.IN_PROGRESS},
        RevenueState.SUBMITTED: {
            RevenueState.ACCEPTED,
            RevenueState.REJECTED,
            RevenueState.IN_PROGRESS,
            RevenueState.DELIVERED,
        },
        RevenueState.ACCEPTED: {RevenueState.AWARDED, RevenueState.SUBMITTED},
        RevenueState.REJECTED: {RevenueState.SUBMITTED},
        RevenueState.AWARDED: {RevenueState.PENDING_PAYOUT, RevenueState.ACCEPTED},
        RevenueState.PENDING_PAYOUT: {RevenueState.PAID, RevenueState.AWARDED},
        RevenueState.PAID: {RevenueState.NET, RevenueState.PENDING_PAYOUT},
        RevenueState.NET: {RevenueState.PAID},
    }

    @classmethod
    def is_valid(cls, from_state: RevenueState, to_state: RevenueState) -> bool:
        return to_state in cls.VALID_TRANSITIONS.get(from_state, set())


@dataclass
class RevenueEntry:
    """Revenue ledger entry data class."""

    entry_id: str
    mission_id: str | None
    opportunity_id: str | None
    platform: str | None
    state: RevenueState
    gross_usd: float
    fees_usd: float
    fx_usd: float
    tax_estimate_usd: float
    net_usd: float
    payment_method: str | None
    external_id: str | None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "mission_id": self.mission_id,
            "opportunity_id": self.opportunity_id,
            "platform": self.platform,
            "state": self.state.value,
            "gross_usd": self.gross_usd,
            "fees_usd": self.fees_usd,
            "fx_usd": self.fx_usd,
            "tax_estimate_usd": self.tax_estimate_usd,
            "net_usd": self.net_usd,
            "payment_method": self.payment_method,
            "external_id": self.external_id,
            "metadata": self.metadata,
        }


class RevenueLedger:
    """Single Source of Truth for OWNEX revenue tracking."""

    VALID_TRANSITIONS = RevenueTransition.VALID_TRANSITIONS

    def __init__(self, session_factory: Any = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def _get_session(self):
        return self._session_factory()

    # ── CRUD ────────────────────────────────────────────────────────

    def create(
        self,
        entry_id: str,
        mission_id: str | None = None,
        opportunity_id: str | None = None,
        platform: str | None = None,
        gross_usd: float = 0.0,
        fees_usd: float = 0.0,
        fx_usd: float = 0.0,
        tax_estimate_usd: float = 0.0,
        payment_method: str | None = None,
        external_id: str | None = None,
        metadata: dict | None = None,
    ) -> RevenueLedgerEntry:
        """Create a new revenue entry."""
        session = self._get_session()
        try:
            net_usd = max(0.0, gross_usd - fees_usd - fx_usd - tax_estimate_usd)
            entry = RevenueLedgerEntry(
                entry_id=entry_id,
                mission_id=mission_id,
                opportunity_id=opportunity_id,
                platform=platform,
                state=RevenueState.DISCOVERED.value,
                gross_usd=gross_usd,
                fees_usd=fees_usd,
                fx_usd=fx_usd,
                tax_estimate_usd=tax_estimate_usd,
                net_usd=net_usd,
                payment_method=payment_method,
                external_id=external_id,
                metadata_json=json.dumps(metadata or {}),
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            logger.info(f"[REVENUE] Created entry {entry_id} for mission {mission_id}")
            return entry
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, entry_id: str) -> RevenueLedgerEntry | None:
        session = self._get_session()
        try:
            return session.query(RevenueLedgerEntry).filter(RevenueLedgerEntry.entry_id == entry_id).first()
        finally:
            session.close()

    def update(self, entry_id: str, **kwargs) -> RevenueLedgerEntry | None:
        session = self._get_session()
        try:
            entry = session.query(RevenueLedgerEntry).filter(RevenueLedgerEntry.entry_id == entry_id).first()
            if not entry:
                return None
            for key, value in kwargs.items():
                if hasattr(entry, key):
                    if key in ("metadata",) and isinstance(value, dict):
                        entry.metadata_json = json.dumps(value)
                    else:
                        setattr(entry, key, value)
            entry.updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(entry)
            return entry
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ── State Transitions ────────────────────────────────────────

    def transition(
        self,
        entry_id: str,
        new_state: RevenueState | str,
        metadata: dict | None = None,
        fees_usd: float = 0.0,
        fx_usd: float = 0.0,
        tax_estimate_usd: float = 0.0,
    ) -> RevenueLedgerEntry | None:
        """Transition entry to new state with validation."""
        if isinstance(new_state, str):
            new_state = RevenueState(new_state)

        session = self._get_session()
        try:
            entry = session.query(RevenueLedgerEntry).filter(RevenueLedgerEntry.entry_id == entry_id).first()
            if not entry:
                return None

            current_state = RevenueState(entry.state)
            if not RevenueTransition.is_valid(current_state, new_state):
                logger.warning(f"[REVENUE] Invalid transition: {current_state} → {new_state}")
                return None

            previous_state = entry.state
            entry.previous_state = previous_state
            entry.state = new_state.value
            entry.state_changed_at = datetime.now(UTC)

            # Update financials if provided
            if fees_usd:
                entry.fees_usd = fees_usd
            if fx_usd:
                entry.fx_usd = fx_usd
            if tax_estimate_usd:
                entry.tax_estimate_usd = tax_estimate_usd

            # Recalculate net
            entry.net_usd = max(0.0, entry.gross_usd - entry.fees_usd - entry.fx_usd - entry.tax_estimate_usd)

            if metadata:
                meta = json.loads(entry.metadata_json) if entry.metadata_json else {}
                meta.update(metadata)
                entry.metadata_json = json.dumps(meta)

            session.commit()
            session.refresh(entry)

            logger.info(f"[REVENUE] Transition {entry_id}: {previous_state} → {new_state.value}")
            return entry
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def record_payout(
        self,
        entry_id: str,
        amount_usd: float,
        payment_method: str,
        external_id: str,
        fees_usd: float = 0.0,
        fx_usd: float = 0.0,
        tax_estimate_usd: float = 0.0,
    ) -> RevenueLedgerEntry | None:
        """Record a payout and transition to PAID."""
        return self.transition(
            entry_id,
            RevenueState.PAID,
            metadata={"payout_amount_usd": amount_usd, "payout_method": payment_method},
            fees_usd=fees_usd,
            fx_usd=fx_usd,
            tax_estimate_usd=tax_estimate_usd,
        )

    # ── Queries ────────────────────────────────────────────────────

    def get_by_mission(self, mission_id: str) -> list[RevenueLedgerEntry]:
        session = self._get_session()
        try:
            return session.query(RevenueLedgerEntry).filter(RevenueLedgerEntry.mission_id == mission_id).all()
        finally:
            session.close()

    def get_by_opportunity(self, opportunity_id: str) -> list[RevenueLedgerEntry]:
        session = self._get_session()
        try:
            return session.query(RevenueLedgerEntry).filter(RevenueLedgerEntry.opportunity_id == opportunity_id).all()
        finally:
            session.close()

    def get_by_platform(self, platform: str) -> list[RevenueLedgerEntry]:
        session = self._get_session()
        try:
            return session.query(RevenueLedgerEntry).filter(RevenueLedgerEntry.platform == platform).all()
        finally:
            session.close()

    def get_by_state(self, state: RevenueState | str) -> list[RevenueLedgerEntry]:
        if isinstance(state, RevenueState):
            state = state.value
        session = self._get_session()
        try:
            return session.query(RevenueLedgerEntry).filter(RevenueLedgerEntry.state == state).all()
        finally:
            session.close()

    def get_pending_payouts(self) -> list[RevenueLedgerEntry]:
        return self.get_by_state(RevenueState.PENDING_PAYOUT)

    def get_paid_entries(self) -> list[RevenueLedgerEntry]:
        return self.get_by_state(RevenueState.PAID)

    def get_summary(self) -> dict[str, Any]:
        """Revenue summary for dashboard."""
        session = self._get_session()
        try:
            from sqlalchemy import func

            total_gross = session.query(func.sum(RevenueLedgerEntry.gross_usd)).scalar() or 0.0
            total_fees = session.query(func.sum(RevenueLedgerEntry.fees_usd)).scalar() or 0.0
            total_fx = session.query(func.sum(RevenueLedgerEntry.fx_usd)).scalar() or 0.0
            total_tax = session.query(func.sum(RevenueLedgerEntry.tax_estimate_usd)).scalar() or 0.0
            total_net = session.query(func.sum(RevenueLedgerEntry.net_usd)).scalar() or 0.0

            by_state = {}
            for state in RevenueState:
                entries = session.query(RevenueLedgerEntry).filter(RevenueLedgerEntry.state == state.value).all()
                by_state[state.value] = {
                    "count": len(entries),
                    "gross_usd": sum(e.gross_usd for e in entries),
                    "net_usd": sum(e.net_usd for e in entries),
                }

            return {
                "total_gross_usd": round(total_gross, 2),
                "total_fees_usd": round(total_fees, 2),
                "total_fx_usd": round(total_fx, 2),
                "total_tax_estimate_usd": round(total_tax, 2),
                "total_net_usd": round(total_net, 2),
                "by_state": by_state,
            }
        finally:
            session.close()


# ── Singleton ──────────────────────────────────────────────────────

_revenue_ledger: Any | None = None


def get_revenue_ledger() -> RevenueLedger:
    global _revenue_ledger
    if _revenue_ledger is None:
        _revenue_ledger = RevenueLedger()
    return _revenue_ledger
