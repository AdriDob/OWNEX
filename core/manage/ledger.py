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


class ContractStatus(enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class RecurringContract(Base):
    """A recurring revenue agreement. MRR is computed from ACTIVE contracts,
    never from accumulated payment events — payments are evidence of collection,
    the contract is the revenue stream."""

    __tablename__ = "recurring_contracts"

    id = Column(String, primary_key=True)
    client_ref = Column(String, index=True)  # external client/contract identifier
    source_type = Column(SQLEnum(RevenueSource), nullable=False)
    amount = Column(Float, nullable=False)  # amount per recurrence_period
    currency = Column(String, default="USD")
    recurrence_period = Column(String, nullable=False)  # weekly|biweekly|monthly|quarterly|semiannual|yearly
    status = Column(SQLEnum(ContractStatus, native_enum=False), default=ContractStatus.ACTIVE)
    started_at = Column(DateTime, default=lambda: datetime.now(UTC))
    ends_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    evidence_url = Column(String, nullable=True)  # contract signature / first payment proof
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC))


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
    contract_id = Column(String, nullable=True, index=True)  # link to recurring_contracts.id
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
        ("contract_id", "VARCHAR(36)"),
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
        contract_id: str | None = None,
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
                contract_id=contract_id,
            )
            session.add(record)
            session.commit()
            return record_id
        finally:
            session.close()

    def mark_as_received(self, record_id: str, evidence: str | None = None) -> bool:
        """Confirm the money has actually hit the account.

        Requires evidence: a payment cannot become RECEIVED (verified income)
        without a transaction reference, receipt, or explicit confirmation.
        """
        session = self.session_factory()
        try:
            record = session.query(RevenueRecord).filter(RevenueRecord.id == record_id).first()
            if not record:
                return False
            proof = evidence or record.evidence_url
            if not proof:
                logger.warning("Refusing RECEIVED without evidence for record %s", record_id)
                return False
            record.status = PaymentStatus.RECEIVED
            if evidence:
                record.evidence_url = evidence
            record.updated_at = datetime.now(UTC)
            session.commit()
            return True
        finally:
            session.close()

    # ── Recurring contracts (MRR source of truth) ──────────────────

    def create_contract(
        self,
        client_ref: str,
        source_type: RevenueSource,
        amount: float,
        recurrence_period: str,
        currency: str = "USD",
        evidence: str | None = None,
        ends_at: datetime | None = None,
    ) -> str:
        """Register a recurring revenue contract. Does NOT create revenue —
        only ACTIVE contracts feed MRR, and only RECEIVED payments are income."""
        session = self.session_factory()
        try:
            contract_id = str(uuid4())
            contract = RecurringContract(
                id=contract_id,
                client_ref=client_ref,
                source_type=source_type,
                amount=amount,
                currency=currency,
                recurrence_period=recurrence_period.lower(),
                evidence_url=evidence,
                ends_at=ends_at,
            )
            session.add(contract)
            session.commit()
            return contract_id
        finally:
            session.close()

    def cancel_contract(self, contract_id: str) -> bool:
        """Mark a contract cancelled — it stops contributing to MRR immediately."""
        session = self.session_factory()
        try:
            contract = session.query(RecurringContract).filter(RecurringContract.id == contract_id).first()
            if not contract or contract.status != ContractStatus.ACTIVE:
                return False
            contract.status = ContractStatus.CANCELLED
            contract.cancelled_at = datetime.now(UTC)
            contract.updated_at = datetime.now(UTC)
            session.commit()
            return True
        finally:
            session.close()

    def record_contract_payment(
        self,
        contract_id: str,
        evidence: str,
        amount: float | None = None,
    ) -> str | None:
        """Record a collected payment against an ACTIVE contract.

        Returns the RevenueRecord id, or None if the contract is not active.
        Multiple payments on the same contract never duplicate MRR — MRR comes
        from the contract, not from payment events.
        """
        session = self.session_factory()
        try:
            contract = session.query(RecurringContract).filter(RecurringContract.id == contract_id).first()
            if not contract or contract.status != ContractStatus.ACTIVE:
                return None
            record_id = str(uuid4())
            session.add(
                RevenueRecord(
                    id=record_id,
                    source_id=contract.client_ref,
                    source_type=contract.source_type,
                    amount=amount if amount is not None else contract.amount,
                    currency=contract.currency,
                    status=PaymentStatus.RECEIVED,
                    evidence_url=evidence,
                    income_type=IncomeType.RECURRING,
                    recurrence_period=contract.recurrence_period,
                    contract_ref=contract.client_ref,
                    contract_id=contract.id,
                )
            )
            session.commit()
            return record_id
        finally:
            session.close()

    def get_active_contracts(self) -> list[RecurringContract]:
        session = self.session_factory()
        try:
            return session.query(RecurringContract).filter(RecurringContract.status == ContractStatus.ACTIVE).all()
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
        """Monthly Recurring Revenue from ACTIVE contracts, normalized to USD/month.

        MRR measures the recurring revenue *stream* (active contracts), not
        accumulated payment events — three monthly payments on one contract
        still count once. Cancelled/expired contracts contribute zero.
        Only USD contracts are included (no FX conversion).
        """
        total = 0.0
        for contract in self.get_active_contracts():
            if contract.currency != "USD":
                continue
            factor = _PERIOD_TO_MONTHLY.get((contract.recurrence_period or "").lower())
            if factor is not None:
                total += contract.amount * factor
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
