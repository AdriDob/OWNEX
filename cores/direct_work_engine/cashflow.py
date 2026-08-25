"""Cashflow projection — ExpectedCashDate (Income Multiplier Fase A slice).

ExpectedIncome != AvailableCash: every opportunity pays through a rail,
and the rail carries real setup+transfer+arrival days. This module turns
the curated Argentina payout database into an explicit cash date so
dashboards can separate earned / pending / available (spec §11) without
ever inventing a timeline.

Honesty contract: unknown or missing payment method yields
confidence="unknown" and date=None — never a fabricated date.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class CashProjection:
    expected_date: str | None  # ISO date, None when unknown
    days_to_cash: int | None
    method_id: str | None
    reliability: float  # 0-100 source score; 0.0 when unknown
    confidence: str  # high | medium | low | unknown
    warnings: tuple[str, ...] = ()


_UNKNOWN = CashProjection(
    expected_date=None,
    days_to_cash=None,
    method_id=None,
    reliability=0.0,
    confidence="unknown",
)


def _confidence(reliability: float) -> str:
    if reliability >= 90:
        return "high"
    if reliability >= 75:
        return "medium"
    return "low"


def expected_cash_date(
    method_id: str | None,
    *,
    accepted_at: datetime | None = None,
) -> CashProjection:
    """Project when money from an ACCEPTED payout becomes available ARS-side.

    ``accepted_at`` defaults to now; pass the acceptance timestamp to make
    projections deterministic/testable.
    """
    if not method_id:
        return CashProjection(None, None, None, 0.0, "unknown", ("payment_method missing",))

    from cores.financial_intelligence.argentina_payout_methods import (
        ARGENTINA_PAYOUT_METHODS,
    )

    method = next((m for m in ARGENTINA_PAYOUT_METHODS if m.id == method_id), None)
    if method is None:
        return CashProjection(
            None,
            None,
            method_id,
            0.0,
            "unknown",
            (f"payout method '{method_id}' not in curated catalog",),
        )

    timing = getattr(method, "timing", {}) or {}
    days = int(timing.get("setup", 0)) + int(timing.get("transfer", 0)) + int(timing.get("arrival", 0))
    base = accepted_at or datetime.now(UTC)
    expected = (base + timedelta(days=days)).date().isoformat()

    return CashProjection(
        expected_date=expected,
        days_to_cash=days,
        method_id=method.id,
        reliability=float(getattr(method, "reliability_score", 0.0)),
        confidence=_confidence(float(getattr(method, "reliability_score", 0.0))),
    )
