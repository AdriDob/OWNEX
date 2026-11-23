from __future__ import annotations

import enum
import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, String, func, text
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
    SERVICE = "service"  # productized service / contract work
    PRODUCT = "product"  # own product sales / subscriptions
    OTHER = "other"


class IncomeType(enum.Enum):
    """Whether revenue is a one-off payment or part of a recurring stream."""

    ONE_TIME = "one_time"
    RECURRING = "recurring"


# Normalization factors to monthly equivalents for recurring revenue.
_PERIOD_TO_MONTHLY = {
    "weekly": 52 / 12,
    "biweekly": 26 / 12,
    "monthly": 1.0,
    "quarterly": 1 / 3,
    "semiannual": 1 / 6,
    "yearly": 1 / 12,
}


class RevenueRecord(Base):
    __tablename__ = "revenue_records"

    id = Column(String, primary_key=True)
    source_id = Column(String, index=True)  # Link to WorkBank item or Strategy
    source_type = Column(SQLEnum(RevenueSource), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    income_type = Column(SQLEnum(IncomeType, native_enum=False), default=IncomeType.ONE_TIME)
    recurrence_period = Column(String, nullable=True)  # "monthly", "yearly", ... (RECURRING only)
    contract_ref = Column(String, nullable=True)  # client/contract identifier for recurring streams
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC))
    evidence_url = Column(String, nullable=True)  # Screenshot or transaction ID


# Create the table immediately
Base.metadata.create_all(bind=engine)


def _ensure_columns() -> None:
    """Add V2 columns to revenue_records on existing databases (SQLite/Postgres)."""
    new_cols = [
        ("income_type", "VARCHAR(20)"),
        ("recurrence_period", "VARCHAR(20)"),
        ("contract_ref", "VARCHAR(255)"),
    ]
    session = SessionLocal()
    try:
        if engine.dialect.name == "sqlite":
            rows = session.execute(text("PRAGMA table_info(revenue_records)")).fetchall()
            existing = {row[1] for row in rows}
            if not existing:
                return
            for col_name, col_type in new_cols:
                if col_name not in existing:
                    session.execute(text(f"ALTER TABLE revenue_records ADD COLUMN {col_name} {col_type}"))
        else:
            for col_name, col_type in new_cols:
                session.execute(text(f"ALTER TABLE revenue_records ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
        session.execute(text("UPDATE revenue_records SET income_type = 'ONE_TIME' WHERE income_type IS NULL"))
        session.commit()
    except Exception as exc:  # noqa: BLE001 — migration must not break ledger init
        logger.warning("revenue_records column migration skipped: %s", exc)
        session.rollback()
    finally:
        session.close()


_ensure_columns()


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
        income_type: IncomeType = IncomeType.ONE_TIME,
        recurrence_period: str | None = None,
        contract_ref: str | None = None,
    ) -> str:
        """Register a new revenue event."""
        session = self.session_factory()
        try:
            record_id = str(uuid4())
            record = RevenueRecord(
                id=record_id,
                source_id=source_id,
                source_type=source_type,
                amount=amount,
                currency=currency,
                status=status,
                evidence_url=evidence,
                income_type=income_type,
                recurrence_period=recurrence_period if income_type == IncomeType.RECURRING else None,
                contract_ref=contract_ref,
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
            result = session.query(func.sum(RevenueRecord.amount)).filter(RevenueRecord.status == PaymentStatus.RECEIVED).scalar()
            return result or 0.0
        finally:
            session.close()

    def get_mrr(self) -> float:
        """Monthly Recurring Revenue: RECEIVED recurring records normalized to monthly USD.

        Only RECEIVED records count — signed contracts or billed invoices do not.
        Records with an unknown recurrence period are excluded from MRR.
        """
        session = self.session_factory()
        try:
            records = (
                session.query(RevenueRecord.amount, RevenueRecord.recurrence_period, RevenueRecord.currency)
                .filter(RevenueRecord.status == PaymentStatus.RECEIVED, RevenueRecord.income_type == IncomeType.RECURRING)
                .all()
            )
        finally:
            session.close()
        total = 0.0
        for amount, period, currency in records:
            if currency != "USD":
                continue  # MRR reported in USD only; FX conversion out of scope
            factor = _PERIOD_TO_MONTHLY.get((period or "").lower())
            if factor is not None:
                total += amount * factor
        return round(total, 2)

    def get_income_breakdown(self) -> dict[str, float]:
        """Received totals split by income type (USD only)."""
        session = self.session_factory()
        try:
            rows = (
                session.query(RevenueRecord.income_type, func.sum(RevenueRecord.amount))
                .filter(RevenueRecord.status == PaymentStatus.RECEIVED, RevenueRecord.currency == "USD")
                .group_by(RevenueRecord.income_type)
                .all()
            )
        finally:
            session.close()
        breakdown = {IncomeType.ONE_TIME.value: 0.0, IncomeType.RECURRING.value: 0.0}
        for income_type, total in rows:
            key = income_type.value if isinstance(income_type, IncomeType) else str(income_type)
            breakdown[key] = breakdown.get(key, 0.0) + round(total or 0.0, 2)
        return breakdown


_LEDGER_INSTANCE = RevenueLedger()


def get_revenue_ledger() -> RevenueLedger:
    return _LEDGER_INSTANCE
