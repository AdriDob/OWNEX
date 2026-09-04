"""Patrimony API — Net worth, patrimonial ladder, and expected revenue endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.trading.contracts import (
    PatrimonialLevel,
)
from core.trading.ladder import get_ladder_engine

router = APIRouter(prefix="/api/patrimony", tags=["patrimony"])


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═════════════════════════════════════════════════════════════════════════════


class ExpectedRevenueCreate(BaseModel):
    source: str  # "bug_bounty", "dev_bounty", "content_factory", "invoice", "other"
    source_id: str
    platform: str
    expected_amount_usd: Decimal
    currency: str = "USD"
    expected_date: str | None = None
    probability_pct: Decimal = Decimal("50")
    notes: str = ""


class ExpectedRevenueRealize(BaseModel):
    realized_amount_usd: Decimal
    realized_at: str | None = None
    notes: str = ""


class AdvanceLevelRequest(BaseModel):
    human_approved: bool = True
    reason: str = ""


class LadderAdvanceResponse(BaseModel):
    success: bool
    new_level: str | None = None
    reasons: list[str] = []


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

_ladder_engine = None


def _get_ladder_engine():
    global _ladder_engine
    if _ladder_engine is None:
        from core.trading.ladder import get_ladder_engine

        _ladder_engine = get_ladder_engine()
    return _ladder_engine


# ── Net Worth Snapshot ───────────────────────────────────────────────────────


@router.get("/snapshot")
async def get_net_worth_snapshot() -> dict[str, Any]:
    """Get current net worth snapshot with full breakdown."""
    engine = _get_ladder_engine()

    # For now, compute from capital engine
    from core.trading.capital import get_capital_engine
    from core.trading.risk import get_risk_engine

    capital = get_capital_engine()
    risk = get_risk_engine()

    capital_state = capital.get_state()
    risk_metrics = risk.metrics

    # Build net worth breakdown
    breakdown = {
        "liquid_capital": float(capital_state.available_cash),
        "emergency_reserve": 0.0,
        "operating_capital": float(capital_state.invested_capital),
        "investments": float(capital_state.invested_capital),
        "crypto": 0.0,
        "business_assets": 0.0,
        "expected_revenue": 0.0,
        "pending_bounties": 0.0,
        "pending_invoices": 0.0,
        "unrealized_value": float(risk_metrics.unrealized_pnl or 0),
        "total_net_worth": float(capital_state.total_capital),
    }

    net_worth = Decimal(str(breakdown["total_net_worth"]))
    ladder = get_ladder_engine().get_ladder_snapshot(net_worth)

    return {
        "generated_at": ladder.snapshot.generated_at if hasattr(ladder, "snapshot") else None,
        "breakdown": breakdown,
        "ladder": {
            "current_level": ladder.current_level.value,
            "level_name": ladder.level_name,
            "progress_pct": float(ladder.progress_pct),
            "next_level": ladder.next_level.value if ladder.next_level else None,
            "next_level_name": ladder.next_level_name,
            "amount_to_next": float(ladder.amount_to_next) if ladder.amount_to_next else None,
            "can_advance": ladder.can_advance,
            "months_at_current_level": ladder.months_at_current_level,
            "capital_gates": {
                "can_advance": ladder.capital_gates.can_advance,
                "blocking_reasons": ladder.capital_gates.blocking_reasons,
                "warnings": ladder.capital_gates.warnings,
                "next_level": ladder.capital_gates.next_level.value if ladder.capital_gates.next_level else None,
            }
            if ladder.capital_gates
            else None,
        },
        "ladder_progress_pct": float(ladder.progress_pct),
        "ladder_level": ladder.current_level.value,
    }


@router.get("/breakdown")
async def get_net_worth_breakdown() -> dict[str, Any]:
    """Get detailed net worth breakdown by category."""
    from core.trading.capital import get_capital_engine
    from core.trading.risk import get_risk_engine

    capital = get_capital_engine()
    risk = get_risk_engine()

    capital_state = capital.get_state()
    risk_metrics = risk.metrics

    return {
        "liquid_capital": float(capital_state.available_cash),
        "emergency_reserve": 0.0,
        "operating_capital": float(capital_state.invested_capital),
        "investments": float(capital_state.invested_capital),
        "crypto": 0.0,
        "business_assets": 0.0,
        "expected_revenue": 0.0,
        "pending_bounties": 0.0,
        "pending_invoices": 0.0,
        "unrealized_value": float(risk_metrics.unrealized_pnl or 0),
        "total_net_worth": float(capital_state.total_capital),
    }


# ── Ladder Status ───────────────────────────────────────────────────────────


@router.get("/ladder")
async def get_ladder_status() -> dict[str, Any]:
    """Get current patrimonial ladder status."""
    from core.trading.capital import get_capital_engine
    from core.trading.risk import get_risk_engine

    capital = get_capital_engine()
    risk = get_risk_engine()

    capital_state = capital.get_state()
    risk_metrics = risk.metrics

    net_worth = Decimal(str(capital_state.total_capital))
    engine = get_ladder_engine()
    ladder = engine.get_ladder_snapshot(net_worth)

    # Get all levels summary
    levels = engine.get_all_levels()
    levels_summary = []
    for level in levels:
        info = engine.get_level_summary(level.level)
        levels_summary.append(info)

    return {
        "current_level": ladder.current_level.value,
        "level_name": ladder.level_name,
        "net_worth": float(net_worth),
        "progress_pct": float(ladder.progress_pct),
        "next_level": ladder.next_level.value if ladder.next_level else None,
        "next_level_name": ladder.next_level_name,
        "amount_to_next": float(ladder.amount_to_next) if ladder.amount_to_next else None,
        "months_at_level": ladder.months_at_current_level,
        "can_advance": ladder.can_advance,
        "capital_gates": {
            "can_advance": ladder.capital_gates.can_advance,
            "blocking_reasons": ladder.capital_gates.blocking_reasons,
            "warnings": ladder.capital_gates.warnings,
            "next_level": ladder.capital_gates.next_level.value if ladder.capital_gates.next_level else None,
        },
        "all_levels": levels_summary,
    }


@router.post("/ladder/advance")
async def advance_level(request: AdvanceLevelRequest) -> LadderAdvanceResponse:
    """Attempt to advance to next patrimonial level (requires human approval)."""
    from core.trading.capital import get_capital_engine
    from core.trading.risk import get_risk_engine

    capital = get_capital_engine()
    risk = get_risk_engine()

    capital_state = capital.get_state()
    risk_metrics = risk.metrics

    net_worth = Decimal(str(capital_state.total_capital))

    engine = get_ladder_engine()
    success, new_level, reasons = engine.advance_level(
        net_worth=Decimal(str(capital_state.total_capital)),
        months_at_level=0,  # Would need to track this
        drawdown_pct=Decimal(str(risk_metrics.current_drawdown or 0)),
        monthly_revenue_usd=Decimal(str(capital_state.realized_pnl / 4)),  # Rough monthly
        human_approved=request.human_approved,
    )

    if success:
        return LadderAdvanceResponse(success=True, new_level=new_level.value if new_level else None, reasons=reasons)
    else:
        raise HTTPException(status_code=400, detail={"reasons": reasons})


@router.get("/ladder/levels")
async def get_all_levels() -> list[dict]:
    """Get all patrimonial levels definition."""
    engine = get_ladder_engine()
    levels = []
    for level in get_ladder_engine().get_all_levels():
        levels.append(engine.get_level_summary(level.level))
    return levels


@router.get("/ladder/level/{level_id}")
async def get_level_detail(level_id: str) -> dict:
    """Get detailed info for a specific ladder level."""
    try:
        level = PatrimonialLevel(level_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown level: {level_id}")

    engine = get_ladder_engine()
    return engine.get_level_summary(level)


# ── Expected Revenue (not yet realized) ──────────────────────────────────────

# In-memory store for expected revenue (would be DB in production)
_expected_revenue_store: dict[str, dict] = {}


@router.post("/expected-revenue")
async def create_expected_revenue(payload: ExpectedRevenueCreate) -> dict:
    """Register expected revenue (bounty submitted, invoice sent, etc.)."""
    import uuid
    from datetime import UTC, datetime

    record_id = f"er_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    record = {
        "record_id": record_id,
        "source": payload.source,
        "source_id": payload.source_id,
        "platform": payload.platform,
        "expected_amount_usd": float(payload.expected_amount_usd),
        "currency": payload.currency,
        "expected_date": payload.expected_date,
        "probability_pct": float(payload.probability_pct),
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "realized_at": None,
        "realized_amount_usd": None,
        "notes": payload.notes,
    }

    _expected_revenue_store[record_id] = record
    return record


@router.get("/expected-revenue")
async def list_expected_revenue(status: str | None = Query(None)) -> list[dict]:
    """List all expected revenue records."""
    records = list(_expected_revenue_store.values())
    if status:
        records = [r for r in records if r["status"] == status]
    return records


@router.get("/expected-revenue/{record_id}")
async def get_expected_revenue(record_id: str) -> dict:
    """Get expected revenue record by ID."""
    if record_id not in _expected_revenue_store:
        raise HTTPException(status_code=404, detail="Record not found")
    return _expected_revenue_store[record_id]


@router.post("/expected-revenue/{record_id}/realize")
async def realize_expected_revenue(record_id: str, payload: ExpectedRevenueRealize) -> dict:
    """Mark expected revenue as realized (payment received)."""
    if record_id not in _expected_revenue_store:
        raise HTTPException(status_code=404, detail="Record not found")

    record = _expected_revenue_store[record_id]
    record["status"] = "paid"
    record["realized_at"] = payload.realized_at
    record["realized_amount_usd"] = float(payload.realized_amount_usd)
    record["notes"] = f"{record['notes']}\nRealized: {payload.notes}"
    record["updated_at"] = datetime.now(UTC).isoformat()

    return record


@router.post("/expected-revenue/{record_id}/cancel")
async def cancel_expected_revenue(record_id: str, reason: str = "cancelled") -> dict:
    """Cancel expected revenue (won't be received)."""
    if record_id not in _expected_revenue_store:
        raise HTTPException(status_code=404, detail="Record not found")

    record = _expected_revenue_store[record_id]
    record["status"] = "cancelled"
    record["notes"] = f"{record['notes']}\nCancelled: {reason}"
    record["updated_at"] = datetime.now(UTC).isoformat()

    return record


# ── Capital Gates ────────────────────────────────────────────────────────────


@router.get("/capital-gates")
async def get_capital_gates(
    drawdown_pct: float = Query(0.0),
    liquidity_usd: float = Query(0.0),
    monthly_revenue_usd: float = Query(0.0),
) -> dict:
    """Check current capital gates status."""
    from core.trading.capital import get_capital_engine
    from core.trading.risk import get_risk_engine

    capital = get_capital_engine()
    risk = get_risk_engine()

    capital_state = capital.get_state()
    risk_metrics = risk.metrics

    net_worth = Decimal(str(capital_state.total_capital))

    engine = get_ladder_engine()
    gates = engine.check_capital_gates(
        net_worth=net_worth,
        months_at_level=0,
        drawdown_pct=Decimal(str(risk_metrics.current_drawdown or 0)),
        liquidity_usd=Decimal(str(capital_state.available_cash)),
        monthly_revenue_usd=Decimal(str(capital_state.realized_pnl / 4)),
        current_leverage=Decimal(str(risk_metrics.leverage or 1)),
    )

    return {
        "can_advance": gates.can_advance,
        "blocking_reasons": gates.blocking_reasons,
        "warnings": gates.warnings,
        "next_level": gates.next_level.value if gates.next_level else None,
    }
