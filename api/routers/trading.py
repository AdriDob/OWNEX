"""Trading API — copy trading, trader intelligence and OWNEX reasoning.

Thin adapter over core.trading engines (SSOT). One router, dashboard summary
in a single call for the simple UX mandate.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException

from core.trading.config import TradingConfig
from core.trading.copy_trading import CopyTradingEngine, FollowedTrader, MasterTrade, ReplicationResult
from core.trading.executor import create_executor
from core.trading.models import OrderSide
from core.trading.reasoning import AutoParamOptimizer, DecisionCorrelator
from core.trading.store import TradingStore
from core.trading.trader_intelligence import (
    BacktestValidator,
    LiveTraderMonitor,
    TraderDiscovery,
    TraderMetrics,
    TraderScorer,
)

router = APIRouter(prefix="/api/trading", tags=["trading"])

_engine: CopyTradingEngine | None = None


def _get_engine() -> CopyTradingEngine:
    global _engine
    if _engine is None:
        _engine = CopyTradingEngine(
            store=TradingStore(), config=TradingConfig(), executor=create_executor(TradingConfig())
        )
    return _engine


def _safe(fn: Any, default: Any) -> Any:
    try:
        return fn()
    except Exception:
        return default


@router.get("/dashboard/summary")
def dashboard_summary() -> dict[str, Any]:
    """One call: copy status + intelligence + reasoning for the dashboard."""
    engine = _get_engine()
    store = engine._store  # noqa: SLF001 — state access only
    return {
        "copy": _safe(engine.status, {}),
        "masters": _safe(lambda: [m.to_dict() for m in engine.list_masters()], []),
        "intelligence": {
            "discovery": _safe(lambda: (store.get("discovery_cache") or {}).get("candidates", []), []),
            "alerts": _safe(lambda: store.get("alerts", []), []),
        },
        "reasoning": {
            "dna": _safe(lambda: store.get("dna", []), []),
            "proposals": _safe(lambda: store.get("proposals", []), []),
        },
        "generated_at": store.now_iso(),
    }


@router.post("/copy/masters")
def add_master(trader: FollowedTrader) -> dict[str, Any]:
    try:
        added = _get_engine().add_master(trader)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "master": added.to_dict()}


@router.get("/copy/masters")
def list_masters() -> dict[str, Any]:
    masters = [m.to_dict() for m in _get_engine().list_masters()]
    return {"success": True, "masters": masters, "count": len(masters)}


@router.delete("/copy/masters/{master_id}")
def remove_master(master_id: str) -> dict[str, Any]:
    if not _get_engine().remove_master(master_id):
        raise HTTPException(status_code=404, detail="master not found")
    return {"success": True}


@router.post("/copy/masters/{master_id}/toggle")
def toggle_master(master_id: str) -> dict[str, Any]:
    master = _get_engine().get_master(master_id)
    if master is None:
        raise HTTPException(status_code=404, detail="master not found")
    _get_engine().set_master_enabled(master_id, not master.enabled)
    updated = _get_engine().get_master(master_id)
    return {"success": True, "master": updated.to_dict() if updated else None}


@router.post("/copy/ingest")
def ingest_master_trade(payload: dict[str, Any]) -> dict[str, Any]:
    """Simulate a master trade and replicate it under risk controls."""
    try:
        side = str(payload.get("side", "BUY")).upper()
        if side not in ("BUY", "SELL"):
            raise HTTPException(status_code=400, detail="side must be BUY or SELL")
        trade = MasterTrade(
            master_id=str(payload["master_id"]),
            pair=str(payload["pair"]).upper(),
            side=OrderSide.BUY if side == "BUY" else OrderSide.SELL,
            quantity=Decimal(str(payload.get("quantity", 0))),
            price=Decimal(str(payload["price"])) if payload.get("price") else None,
            master_dd_pct=payload.get("master_dd_pct"),
            source=str(payload.get("source", "cex")),
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing field: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid numeric values") from exc
    result: ReplicationResult = _get_engine().replicate(trade.master_id, trade)
    return {
        "success": result.success,
        "reason": result.reason,
        "master_trade": result.master_trade,
        "order": result.order,
        "size_usd": str(result.size_usd),
        "simulated": result.simulated,
    }


@router.post("/copy/emergency-stop")
def emergency_stop(payload: dict[str, Any]) -> dict[str, Any]:
    reason = str(payload.get("reason", "user requested"))
    return {"success": True, "result": _get_engine().emergency_stop(reason)}


@router.post("/copy/release")
def release_emergency_stop() -> dict[str, Any]:
    _get_engine().release_emergency_stop()
    return {"success": True}


@router.get("/copy/status")
def copy_status() -> dict[str, Any]:
    return _get_engine().status()


@router.get("/intelligence/discover")
async def discover_traders(limit: int = 10) -> dict[str, Any]:
    discovery = TraderDiscovery()
    scored = await discovery.discover_scored(limit=limit)
    return {"success": True, "candidates": scored, "count": len(scored)}


@router.post("/intelligence/score")
def score_trader(metrics: TraderMetrics) -> dict[str, Any]:
    score = TraderScorer().score(metrics)
    validation = BacktestValidator().validate(metrics)
    return {
        "success": True,
        "score": score.score,
        "tier": score.tier,
        "factors": score.factors,
        "reasoning": score.reasoning,
        "validation": validation,
    }


@router.post("/intelligence/validate")
def validate_trader(metrics: TraderMetrics) -> dict[str, Any]:
    return {"success": True, "validation": BacktestValidator().validate(metrics)}


@router.post("/intelligence/alerts")
def check_alerts(
    metrics: TraderMetrics, current_dd_pct: float | None = None, rolling_win_rate: float | None = None
) -> dict[str, Any]:
    alerts = LiveTraderMonitor().check(metrics, current_dd_pct=current_dd_pct, rolling_win_rate=rolling_win_rate)
    return {"success": True, "alerts": alerts, "count": len(alerts)}


@router.get("/reasoning/dna")
def get_dna() -> dict[str, Any]:
    dna = _safe(lambda: _get_engine()._store.get("dna", []), [])  # noqa: SLF001
    return {"success": True, "dna": dna, "count": len(dna)}


@router.get("/reasoning/proposals")
def get_proposals() -> dict[str, Any]:
    proposals = _safe(lambda: _get_engine()._store.get("proposals", []), [])  # noqa: SLF001
    return {"success": True, "proposals": proposals, "count": len(proposals)}


@router.post("/reasoning/correlate")
def correlate_dna(limit: int = 500) -> dict[str, Any]:
    store = _get_engine()._store  # noqa: SLF001
    correlator = DecisionCorrelator(store)
    dna = correlator.correlate(limit=limit)
    correlator.persist_dna(dna)
    return {"success": True, "dna": [d.__dict__ for d in dna], "count": len(dna)}


@router.post("/reasoning/approve/{proposal_id}")
def approve_proposal(proposal_id: str) -> dict[str, Any]:
    return AutoParamOptimizer(_get_engine()._store).approve(proposal_id)  # noqa: SLF001


@router.post("/reasoning/reject/{proposal_id}")
def reject_proposal(proposal_id: str) -> dict[str, Any]:
    return AutoParamOptimizer(_get_engine()._store).reject(proposal_id)  # noqa: SLF001
