"""Cashflow projection tests — ExpectedCashDate (Fase A slice)."""

from __future__ import annotations

from datetime import UTC, datetime

from cores.direct_work_engine.cashflow import expected_cash_date


def _days_for(method_id: str) -> int:
    from cores.financial_intelligence.argentina_payout_methods import (
        ARGENTINA_PAYOUT_METHODS,
    )

    m = next(m for m in ARGENTINA_PAYOUT_METHODS if m.id == method_id)
    t = m.timing
    return int(t.get("setup", 0)) + int(t.get("transfer", 0)) + int(t.get("arrival", 0))


def test_known_method_projects_date() -> None:
    accepted = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    days = _days_for("binance_ar")
    res = expected_cash_date("binance_ar", accepted_at=accepted)
    assert res.days_to_cash == days
    assert res.expected_date is not None
    year, month, day = map(int, res.expected_date.split("-"))
    assert (year, month, day) == (2026, 8, 25 + days)


def test_high_reliability_maps_to_high_confidence() -> None:
    res = expected_cash_date("binance_ar")  # reliability 95 per catalog
    assert res.confidence == "high"
    assert res.reliability >= 90


def test_unknown_method_never_invents_a_date() -> None:
    res = expected_cash_date("no_such_rail_xyz")
    assert res.expected_date is None
    assert res.days_to_cash is None
    assert res.confidence == "unknown"
    assert any("not in curated catalog" in w for w in res.warnings)


def test_missing_method_is_unknown() -> None:
    res = expected_cash_date(None)
    assert res.expected_date is None
    assert res.confidence == "unknown"
    assert any("missing" in w for w in res.warnings)
