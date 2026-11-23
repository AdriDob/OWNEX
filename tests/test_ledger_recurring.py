"""Ledger V2 integrity tests — evidence-gated RECEIVED and contract-based MRR.

Uses an isolated in-memory SQLite DB so the real ledger is never touched.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.manage.ledger import (
    Base,
    IncomeType,
    PaymentStatus,
    RevenueLedger,
    RevenueRecord,
    RevenueSource,
)


@pytest.fixture()
def ledger():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    instance = RevenueLedger()
    instance.session_factory = factory
    yield instance


def test_received_requires_evidence(ledger: RevenueLedger):
    rid = ledger.record_payment("src-1", RevenueSource.DIRECT_WORK, 100.0, evidence=None)
    assert ledger.mark_as_received(rid) is False  # no evidence → refused
    # still PENDING
    session = ledger.session_factory()
    rec = session.query(RevenueRecord).filter(RevenueRecord.id == rid).one()
    assert rec.status == PaymentStatus.PENDING
    session.close()

    # evidence at confirm time works
    assert ledger.mark_as_received(rid, evidence="tx-12345") is True
    session = ledger.session_factory()
    rec = session.query(RevenueRecord).filter(RevenueRecord.id == rid).one()
    assert rec.status == PaymentStatus.RECEIVED
    assert rec.evidence_url == "tx-12345"
    session.close()


def test_evidence_on_record_allows_confirm(ledger: RevenueLedger):
    rid = ledger.record_payment("src-2", RevenueSource.DIRECT_WORK, 50.0, evidence="receipt-url")
    assert ledger.mark_as_received(rid) is True


def test_contract_creates_no_revenue_by_itself(ledger: RevenueLedger):
    ledger.create_contract("client-a", RevenueSource.SERVICE, 500.0, "monthly")
    assert ledger.get_mrr() == 500.0  # active contract counts toward MRR stream
    assert ledger.get_total_balance() == 0.0  # but ZERO verified revenue without payments


def test_mrr_not_duplicated_by_multiple_payments(ledger: RevenueLedger):
    cid = ledger.create_contract("client-b", RevenueSource.SERVICE, 300.0, "monthly")
    for month in range(3):
        assert ledger.record_contract_payment(cid, evidence=f"inv-{month}-paid") is not None
    assert ledger.get_mrr() == 300.0  # one contract → counted once, not 3×
    assert ledger.get_total_balance() == 900.0  # but all 3 payments are real received income


def test_cancelled_contract_drops_from_mrr(ledger: RevenueLedger):
    cid = ledger.create_contract("client-c", RevenueSource.SERVICE, 200.0, "monthly")
    assert ledger.get_mrr() == 200.0
    assert ledger.cancel_contract(cid) is True
    assert ledger.get_mrr() == 0.0
    # payments on cancelled contract refused
    assert ledger.record_contract_payment(cid, evidence="late-payment") is None


def test_payment_on_unknown_contract_refused(ledger: RevenueLedger):
    assert ledger.record_contract_payment("nonexistent", evidence="x") is None


def test_period_normalization(ledger: RevenueLedger):
    ledger.create_contract("y", RevenueSource.SERVICE, 1200.0, "yearly")
    ledger.create_contract("w", RevenueSource.SERVICE, 50.0, "weekly")
    ledger.create_contract("q", RevenueSource.SERVICE, 300.0, "quarterly")
    # 1200/12 + 50*52/12 + 300/3 = 100 + 216.67 + 100 = 416.67
    assert ledger.get_mrr() == pytest.approx(416.67, abs=0.01)


def test_non_usd_and_unknown_period_excluded(ledger: RevenueLedger):
    ledger.create_contract("ars", RevenueSource.SERVICE, 1000.0, "monthly", currency="ARS")
    ledger.create_contract("odd", RevenueSource.SERVICE, 999.0, "per-deliverable")
    assert ledger.get_mrr() == 0.0


def test_contract_payment_links_record(ledger: RevenueLedger):
    cid = ledger.create_contract("client-d", RevenueSource.SERVICE, 100.0, "monthly")
    rid = ledger.record_contract_payment(cid, evidence="wire-1")
    session = ledger.session_factory()
    rec = session.query(RevenueRecord).filter(RevenueRecord.id == rid).one()
    assert rec.contract_id == cid
    assert rec.income_type == IncomeType.RECURRING
    assert rec.status == PaymentStatus.RECEIVED
    session.close()


def test_income_breakdown_splits_types(ledger: RevenueLedger):
    ledger.record_payment("one", RevenueSource.DIRECT_WORK, 40.0, evidence="e", status=PaymentStatus.RECEIVED)
    cid = ledger.create_contract("rec", RevenueSource.SERVICE, 60.0, "monthly")
    ledger.record_contract_payment(cid, evidence="e2")
    breakdown = ledger.get_income_breakdown()
    assert breakdown["one_time"] == 40.0
    assert breakdown["recurring"] == 60.0
