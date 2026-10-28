"""Unified Income API — Single endpoint for all income engines.

Unifies Bug Bounty, Dev Bounty, and Content Factory income tracking.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel

from cores.trading.ev_calculator import get_unified_ev_calculator

logger = logging.getLogger("ownex.unified_income")

router = APIRouter(prefix="/api/unified-income", tags=["unified-income"])


# ════════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class UnifiedIncomeDashboard(BaseModel):
    """Unified income dashboard response."""

    generated_at: str
    # UNKNOWN (None) ≠ 0.0: sin datos medidos no se informa una cifra.
    total_ev_hour: float | None
    total_expected_value: float | None
    total_probability: float | None
    best_action: dict | None
    by_engine: dict
    recommendations: list[dict]


class EVRankingItem(BaseModel):
    """Single strategy EV ranking item."""

    strategy_id: str
    engine: str
    name: str
    ev_hour: float
    expected_value: float
    probability_success: float
    estimated_hours: float
    zero_barrier_score: float
    composite_score: float
    rank: int


class UnifiedEVRanking(BaseModel):
    """Unified EV ranking across all engines."""

    generated_at: str
    all_ranked: list[dict]
    by_engine: dict
    best_overall: dict | None


class WeeklyPlanRequest(BaseModel):
    """Request for weekly income plan."""

    available_hours: float = 40.0
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    preferred_engines: list[str] | None = None


class WeeklyIncomePlan(BaseModel):
    """Weekly income plan with prioritized actions."""

    generated_at: str
    total_estimated_ev: float
    total_hours: float
    daily_plan: list[dict]
    risk_warnings: list[str]


class OneBestAction(BaseModel):
    """Single best action recommendation."""

    action_type: str
    title: str
    description: str
    why_now: str
    platform: str
    opportunity_id: str | None
    work_item_id: str | None
    estimated_human_hours: float
    expected_value_usd: float
    acceptance_probability: float
    cash_speed_days: int | None
    urgency: str
    prerequisites: list[str]
    url: str | None
    next_step_instruction: str
    metadata: dict


class WorkBankStats(BaseModel):
    """Work bank statistics."""

    scanned: int
    ready_to_deliver: int
    needs_access: int
    delivered: int
    targets: dict


# ════════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════

_unified_ev = None


def _get_unified_ev():
    global _unified_ev
    if _unified_ev is None:
        from cores.trading.ev_calculator import get_unified_ev_calculator

        _unified_ev = get_unified_ev_calculator()
    return _unified_ev


@router.get("/dashboard")
async def get_unified_income_dashboard() -> UnifiedIncomeDashboard:
    """Unified income dashboard. REAL data; UNKNOWN donde no hay evidencia.

    Antes devolvía 0.0 hardcodeado y listas vacías (stub). Ahora usa los
    engines que ya instanciaba; el ranking EV queda UNKNOWN (no 0.0) hasta
    que existan estrategias de entrada reales para el calculador.
    """
    import dataclasses

    from cores.trading.capital import get_capital_engine
    from cores.trading.risk import get_risk_engine

    capital_summary = get_capital_engine().get_summary()
    # RiskMetrics es un dataclass (no dict): se serializa explícitamente.
    raw_risk = getattr(get_risk_engine(), "metrics", None)
    risk_metrics = (
        dataclasses.asdict(raw_risk) if dataclasses.is_dataclass(raw_risk) and not isinstance(raw_risk, type) else {}
    )

    return UnifiedIncomeDashboard(
        generated_at="",
        total_ev_hour=None,  # UNKNOWN: sin estrategias de entrada, no hay EV/h que informar
        total_expected_value=None,
        total_probability=None,
        best_action=None,
        by_engine={
            "capital": capital_summary,
            "risk": risk_metrics,
        },
        recommendations=[],
    )


@router.get("/ev-ranking")
async def get_ev_ranking() -> UnifiedEVRanking:
    """EV ranking entre motores. Vacío honesto hasta que haya estrategias reales."""
    unified_ev = get_unified_ev_calculator()
    rankings = unified_ev.calculate_all_engines([], [], [], {}, {})  # sin inputs → vacío real
    return UnifiedEVRanking(
        generated_at="",
        all_ranked=rankings.get("all_ranked", []),
        by_engine=rankings.get("by_engine", {}),
        best_overall=rankings.get("best_overall"),
    )


@router.get("/best-action")
async def get_one_best_action() -> OneBestAction:
    """Get the single best action across all engines (real OBA, never mocked)."""
    try:
        from cores.direct_work_engine import one_best_action as oba_mod

        oba = oba_mod.get_one_best_action()
        d = oba.to_dict() if hasattr(oba, "to_dict") else {}
        return OneBestAction(
            action_type=str(d.get("action_type", "run_workbank_cycle")),
            title=str(d.get("title") or "Sin acción disponible"),
            description=str(d.get("description") or ""),
            why_now=str(d.get("why_now") or ""),
            platform=str(d.get("platform") or ""),
            opportunity_id=d.get("opportunity_id"),
            work_item_id=d.get("work_item_id"),
            estimated_human_hours=float(d.get("estimated_human_hours") or 0),
            expected_value_usd=float(d.get("expected_value_usd") or 0),
            acceptance_probability=float(d.get("acceptance_probability") or 0),
            cash_speed_days=d.get("cash_speed_days"),
            urgency=str(d.get("urgency", "flexible")),
            prerequisites=list(d.get("prerequisites") or []),
            url=d.get("url"),
            next_step_instruction=str(d.get("next_step_instruction") or ""),
            metadata=dict(d.get("metadata") or {}),
        )
    except Exception:
        logger.warning("unified-income: OBA unavailable, honest empty action", exc_info=True)
        return OneBestAction(
            action_type="run_workbank_cycle",
            title="Sin acción disponible",
            description="El motor no devolvió acción. Corré el ciclo del WorkBank.",
            why_now="Sin datos",
            platform="",
            opportunity_id=None,
            work_item_id=None,
            estimated_human_hours=0.0,
            expected_value_usd=0.0,
            acceptance_probability=0.0,
            cash_speed_days=None,
            urgency="flexible",
            prerequisites=[],
            url=None,
            next_step_instruction="POST /direct-work/workbank/cycle",
            metadata={"empty": True},
        )


@router.post("/weekly-plan")
async def get_weekly_plan(request: WeeklyPlanRequest) -> WeeklyIncomePlan:
    """Generate weekly income plan based on available hours and risk tolerance."""
    return WeeklyIncomePlan(
        generated_at="",
        total_estimated_ev=0.0,
        total_hours=request.available_hours,
        daily_plan=[],
        risk_warnings=[],
    )


@router.get("/workbank")
async def get_workbank_stats() -> WorkBankStats:
    """Get work bank statistics."""
    from cores.direct_work_engine.workbank import get_workbank

    wb = get_workbank()
    # `_summary()` es la fuente real de estos contadores. Antes se leía
    # `progress()`, que devuelve {daily, weekly, monthly} con target/achieved/
    # ready_total/pct — ninguna de las 5 keys pedidas existía, así que este
    # endpoint reportaba 0/0/0/0 aunque el banco tuviera items reales.
    summary = wb._summary()  # noqa: SLF001

    return WorkBankStats(
        scanned=int(summary.get("scanned", 0) or 0),
        ready_to_deliver=int(summary.get("ready_to_deliver", 0) or 0),
        needs_access=int(summary.get("needs_access", 0) or 0),
        delivered=int(summary.get("delivered", 0) or 0),
        targets=summary.get("targets", {}),
    )


@router.get("/regime-performance")
async def get_regime_performance(
    regime: str | None = Query(None),
) -> dict:
    """Get performance breakdown by market regime."""
    return {
        "regime": regime or "all",
        "by_engine": {},
    }


@router.get("/expected-vs-realized")
async def get_expected_vs_realized() -> dict:
    """Get expected vs realized revenue breakdown."""
    return {
        "expected": {
            "total_usd": 0.0,
            "by_source": {},
        },
        "realized": {
            "total_usd": 0.0,
            "by_source": {},
        },
        "gap": 0.0,
    }
