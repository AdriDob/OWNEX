from __future__ import annotations

import enum
import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_base

from database.db import SessionLocal, engine

Base = declarative_base()
logger = logging.getLogger("ownex.manage.ledger")


class PaymentStatus(enum.Enum):
    PENDING = "pending"  # Work submitted, payment expected
    RECEIVED = "received"  # Money is in the account
    FAILED = "failed"  # Rejected/Cancelled
    DISPUTED = "disputed"  # Payment under review


class RevenueSource(enum.Enum):
    BUG_BOUNTY = "bug_bounty"
    DIRECT_WORK = "direct_work"
    INVESTMENT_YIELD = "investment_yield"
    SaaS = "saas"
    OTHER = "other"


class RevenueRecord(Base):
    __tablename__ = "revenue_records"

    id = Column(String, primary_key=True)
    source_id = Column(String, index=True)  # Link to WorkBank item or Strategy
    source_type = Column(SQLEnum(RevenueSource), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC))
    evidence_url = Column(String, nullable=True)  # Screenshot or transaction ID


# Create the table immediately
Base.metadata.create_all(bind=engine)


class RevenueLedger:
    """
    The Single Source of Truth for all money entering OWNEX.
    """

    def __init__(self):
        self.session_factory = SessionLocal

    def record_payment(
        self,
        source_id: str,
        source_type: RevenueSource,
        amount: float,
        currency: str = "USD",
        status: PaymentStatus = PaymentStatus.PENDING,
        evidence: str | None = None,
    ) -> str:
        """Register a new revenue event."""
        session = self.session_factory()
        try:
            record_id = str(uuid4())
            record = RevenueRecord(
                id=record_id, source_id=source_id, source_type=source_type, amount=amount, currency=currency, status=status, evidence_url=evidence
            )
            session.add(record)
            session.commit()
            return record_id
        finally:
            session.close()

    def mark_as_received(self, record_id: str) -> bool:
        """Confirm the money has actually hit the account."""
        session = self.session_factory()
        try:
            record = session.query(RevenueRecord).filter(RevenueRecord.id == record_id).first()
            if record:
                record.status = PaymentStatus.RECEIVED
                record.updated_at = datetime.now(UTC)
                session.commit()
                return True
            return False
        finally:
            session.close()

    def get_total_balance(self) -> float:
        """Sum of all RECEIVED payments."""
        session = self.session_factory()
        try:
            from sqlalchemy import func

            result = session.query(func.sum(RevenueRecord.amount)).filter(RevenueRecord.status == PaymentStatus.RECEIVED).scalar()
            return result or 0.0
        finally:
            session.close()


_LEDGER_INSTANCE = RevenueLedger()


def get_revenue_ledger() -> RevenueLedger:
    return _LEDGER_INSTANCE
