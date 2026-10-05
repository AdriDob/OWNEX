"""Trading API — copy trading, trader intelligence and OWNEX reasoning.

Thin adapter over cores.trading engines (SSOT). One router, dashboard summary
in a single call for the simple UX mandate.
"""

from __future__ import annotations

import dataclasses
import os
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException

from cores.automation.safety import consume_approval, issue_approval
from cores.trading.config import TradingConfig
from cores.trading.copy_trading import CopyTradingEngine, FollowedTrader, MasterTrade, ReplicationResult
from cores.trading.executor import create_executor
from cores.trading.models import OrderSide
from cores.trading.reasoning import AutoParamOptimizer, DecisionCorrelator
from cores.trading.store import TradingStore
from cores.trading.trader_intelligence import (
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


@router.get("/overview")
def overview() -> dict[str, Any]:
    """One honest call for the front: mode + jobs + paper metrics + copy + pending config.

    Nothing here invents data: DRY_RUN/PAPER metrics come from TradingStore,
    config-mode from TradingConfig, jobs from the scheduler registry, and the
    pending trading config from the Setup Checklist (trading_live manual item).
    """
    from cores.scheduler.jobs import get_trading_jobs
    from cores.setup.checklist import get_setup_checklist
    from cores.trading.paper.memecoin_paper import MemecoinPaperLoop, paper_metrics

    engine = _get_engine()
    store = engine._store  # noqa: SLF001
    config = TradingConfig()
    ask = TradingConfig.from_env()

    trades = store.get(MemecoinPaperLoop.LEDGER_KEY) or []
    pnls = [t["pnl_sol"] for t in trades if isinstance(t, dict)] if trades else []
    metrics = paper_metrics([type("T", (), {"pnl_sol": p})() for p in pnls])
    metrics["trade_count"] = len(trades)

    jobs = get_trading_jobs()
    running = [j for j in jobs if (j.metadata or {}).get("enabled", True) is True]

    # Pending config: paper mode is the safe default and needs nothing; live asks
    # for exchange keys (vault/env). trading_live (manual) gates the decision.
    checklist = _safe(lambda: get_setup_checklist().status(), {})
    pending: list[dict[str, str]] = []
    live_enabled = False
    for item in checklist.get("pending") or []:
        if item.get("id") == "trading_live":
            live_enabled = False
            pending.append(
                {
                    "id": "trading_live",
                    "title": item.get("title", "Habilitar trading LIVE"),
                    "why": item.get("why", ""),
                    "how_to": item.get("how_to", ""),
                }
            )
    if not pending and not live_enabled:
        for env_key in ("EXCHANGE_API_KEY", "HELIUS_API_KEY"):
            if not os.environ.get(env_key) and not getattr(ask, env_key.lower(), ""):
                pending.append(
                    {
                        "id": env_key.lower(),
                        "title": f"Configurar {env_key}",
                        "why": "Necesario para trading LIVE.",
                        "how_to": "IdentityVault / env.",
                    }
                )

    return {
        "mode": config.mode.value,
        "mode_label": config.mode_label,
        "is_simulation": config.is_simulation,
        "is_live": config.is_live,
        "emergency_stop": bool(engine.status().get("emergency_stop", False)),
        "copy": _safe(engine.status, {}),
        "masters": _safe(lambda: [m.to_dict() for m in engine.list_masters()], []),
        "metrics": metrics,
        "jobs": {"total": len(jobs), "enabled": len(running)},
        "reasoning": {
            "dna": _safe(lambda: store.get("dna", []), []),
            "proposals": _safe(lambda: store.get("proposals", []), []),
        },
        "pending_config": pending,
        "generated_at": store.now_iso(),
    }


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


# ── Backtest (offline replay of accumulated paper snapshots) ──


def _backtest_config_from_payload(payload: dict[str, Any]) -> Any:
    """Build a BacktestConfig from request payload. Shallow, defensive."""
    from cores.trading.backtest import BacktestConfig

    cfg = payload.get("config") or {}
    try:
        return BacktestConfig(
            position_sol=float(cfg.get("position_sol", 0.1)),
            max_open_positions=int(cfg.get("max_open_positions", 3)),
            daily_loss_limit_sol=float(cfg.get("daily_loss_limit_sol", 0.5)),
            max_hold_minutes=float(cfg.get("max_hold_minutes", 120.0)),
            min_liquidity_usd=float(cfg.get("min_liquidity_usd", 10_000.0)),
            stop_loss_pct=float(cfg.get("stop_loss_pct", 0.25)),
            trailing_pct=float(cfg.get("trailing_pct", 0.20)),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid backtest config: {exc}") from exc


@router.post("/backtest/run")
def run_backtest_endpoint(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Replay accumulated paper snapshots through filters + exits (offline).

    Body optional: {"config": {...backtest knobs...}}. When no snapshots have
    been accumulated yet the paper loop is the producer (every 15m scheduler
    cycle records tracked prices), so this returns honest NO_DATA metrics.
    """
    from cores.trading.backtest import load_snapshots, result_to_dict, run_backtest

    store = _get_engine()._store  # noqa: SLF001
    snapshots = load_snapshots(store)
    cfg = _backtest_config_from_payload(payload or {})
    result = run_backtest(snapshots, cfg)
    return {"success": True, **result_to_dict(result)}


@router.post("/backtest/snapshot")
def record_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Record one price snapshot (from a live feed or manual entry)."""
    from cores.trading.backtest import save_snapshot

    store = _get_engine()._store  # noqa: SLF001
    mint = str(payload.get("mint", ""))
    try:
        price = float(payload.get("price_usd", 0))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="price_usd must be numeric") from exc
    if not mint or price <= 0:
        raise HTTPException(status_code=400, detail="mint + positive price_usd required")
    save_snapshot(
        store,
        mint,
        str(payload.get("symbol", "?")),
        price,
        pair=payload.get("pair") or {},
        rug=payload.get("rug"),
    )
    return {"success": True}


@router.get("/metrics/history")
def trading_metrics() -> dict[str, Any]:
    """Paper metrics, open positions and accumulated snapshot count."""
    from cores.trading.backtest import load_snapshots
    from cores.trading.paper.memecoin_paper import MemecoinPaperLoop, paper_metrics

    store = _get_engine()._store  # noqa: SLF001
    snapshots = load_snapshots(store)
    trades = store.get(MemecoinPaperLoop.LEDGER_KEY) or []
    pnls = [t["pnl_sol"] for t in trades if isinstance(t, dict)] if trades else []
    metrics = paper_metrics([])
    if pnls:
        try:
            fake = [type("T", (), {"pnl_sol": p})() for p in pnls]
            metrics = paper_metrics(fake)
        except Exception:
            metrics = paper_metrics([])
    metrics["trade_count"] = len(trades)
    metrics["snapshots"] = len(snapshots)
    metrics["hash"] = (
        f"{metrics.get('trades', 0)}/{metrics.get('win_rate') or '-'}/{metrics.get('profit_factor') or '-'}"
    )
    return {"success": True, "metrics": metrics}


@router.post("/advisor/propose")
async def advisor_propose(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """OAR proposes parameter tweaks from paper metrics (Human Gate to apply).

    Returns proposals already persisted as ParamAdjustment under the standard
    `proposals` store key — the existing /reasoning/approve|reject endpoints
    handle the actual apply/reject decision.
    """
    from cores.trading.advisor import TradingAdvisor
    from cores.trading.paper.memecoin_paper import MemecoinPaperLoop, paper_metrics
    from cores.trading.reasoning import ParamAdjustment

    store = _get_engine()._store  # noqa: SLF001
    trades = store.get(MemecoinPaperLoop.LEDGER_KEY) or []
    metrics = paper_metrics([type("T", (), {"pnl_sol": t["pnl_sol"]})() for t in trades])
    if metrics.get("trades", 0) < 20:
        return {"success": True, "proposals": [], "count": 0, "reason": "insufficient sample (<20 trades)"}

    cfg = _backtest_config_from_payload(payload or {})
    advisor = TradingAdvisor(store)
    proposals = await advisor.propose(metrics, cfg.to_dict())
    if not proposals:
        return {"success": True, "proposals": [], "count": 0, "reason": "no proposals (no edge or OAR unavailable)"}

    persisted: list[dict[str, Any]] = []
    for p in proposals:
        adjustment = ParamAdjustment(
            proposal_id=p.proposal_id,
            strategy_id="memecoin_v1",
            param=p.param,
            current_value=p.current_value,
            proposed_value=p.proposed_value,
            reason=p.reason,
            confidence=p.confidence,
        )
        store.upsert_item("proposals", adjustment.__dict__, id_key="proposal_id")
        persisted.append(adjustment.__dict__)

    return {"success": True, "proposals": persisted, "count": len(persisted)}


# ── Pump Radar — radar real de pumps, lectura + ejecución gated ────────


@router.get("/pump/radar")
async def pump_radar(
    min_liquidity_usd: float = 10000,
    min_volume_h24: float = 20000,
    min_price_change_h24: float = 20.0,
    max_candidates: int = 20,
) -> dict[str, Any]:
    from cores.trading.pump_radar import PumpRadarConfig, scan_pump_candidates

    cfg = PumpRadarConfig(
        min_liquidity_usd=min_liquidity_usd,
        min_volume_h24_usd=min_volume_h24,
        min_price_change_h24_pct=min_price_change_h24,
        max_candidates=max_candidates,
    )
    candidates = await scan_pump_candidates(cfg)
    return {
        "success": True,
        "scanned_at": __import__("time").time(),
        "config": dataclasses.asdict(cfg),
        "count": len(candidates),
        "candidates": [dataclasses.asdict(c) for c in candidates],
    }


@router.get("/pump/last")
def pump_last() -> dict[str, Any]:
    snap = _get_engine()._store.get("pump_radar_last")  # noqa: SLF001
    if not snap:
        return {"success": True, "snapshot": None, "reason": "no snapshot yet (radar runs every 5m)"}
    return {"success": True, "snapshot": snap}


@router.post("/pump/simulate")
async def pump_simulate(payload: dict[str, Any]) -> dict[str, Any]:
    mint = str(payload.get("mint") or "").strip()
    amount_sol = float(payload.get("amount_sol") or 0.1)
    if not mint:
        raise HTTPException(status_code=422, detail="mint required")
    if amount_sol <= 0 or amount_sol > 5:
        raise HTTPException(status_code=422, detail="amount_sol 0-5")
    from cores.investment.adapters.memecoin_adapter import MemecoinAdapter

    adapter = MemecoinAdapter()
    try:
        quote = await adapter.quote_buy(mint, amount_sol)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"quote failed: {exc}") from exc
    if not quote:
        raise HTTPException(status_code=404, detail="no quote for mint (illiquid or unknown)")
    return {"success": True, "dry_run": True, "mint": mint, "amount_sol": amount_sol, "quote": quote}


@router.post("/pump/approve")
def pump_approve(payload: dict[str, Any]) -> dict[str, Any]:
    mint = str(payload.get("mint") or "").strip()
    if not mint:
        raise HTTPException(status_code=422, detail="mint required")
    token = issue_approval(action="pump_live_trade", target=mint, workspace="trading")
    return {"success": True, "approval_token": token, "mint": mint, "ttl_seconds": 600}


@router.post("/pump/execute")
async def pump_execute(payload: dict[str, Any]) -> dict[str, Any]:
    mint = str(payload.get("mint") or "").strip()
    token = str(payload.get("approval_token") or "").strip()
    amount_sol = float(payload.get("amount_sol") or 0.1)
    if not mint:
        raise HTTPException(status_code=422, detail="mint required")
    if not token:
        raise HTTPException(status_code=403, detail="approval_token required (POST /pump/approve first)")
    if not consume_approval(token, action="pump_live_trade", target=mint, workspace="trading"):
        raise HTTPException(status_code=403, detail="invalid or expired approval_token")
    if amount_sol <= 0 or amount_sol > 1.0:
        raise HTTPException(status_code=422, detail="amount_sol 0-1.0 for live (risk cap)")
    from cores.trading.config import TradingConfig

    cfg = TradingConfig.from_env()
    if not cfg.is_live:
        raise HTTPException(status_code=412, detail="TradingConfig not in REAL mode (set TRADING_MODE=real)")
    # Kill switch: se consulta por el NOMBRE REAL del método (`is_active`).
    # Antes llamaba `is_triggered()`, que no existe → AttributeError tragado
    # por `except Exception: pass` → el path de compra real nunca chekeaba el
    # switch. Un control que se puede saltear por un typo no es un control.
    from cores.trading.risk import KillSwitchLevel, KillSwitchManager
    from cores.trading.store import TradingStore

    kill = KillSwitchManager(store=TradingStore())
    if kill.is_active(KillSwitchLevel.GLOBAL) or kill.is_active(KillSwitchLevel.STRATEGY):
        raise HTTPException(status_code=423, detail="kill switch active — resolve before live trade")
    if amount_sol * 150 > cfg.max_position_size_usd:
        raise HTTPException(
            status_code=422, detail=f"position exceeds max_position_size_usd {cfg.max_position_size_usd}"
        )
    from cores.investment.adapters.memecoin_adapter import MemecoinAdapter

    adapter = MemecoinAdapter(config={"allow_live": True, "private_key": cfg.exchange_api_key or cfg.helius_api_key})
    if not adapter._private_key:  # noqa: SLF001
        raise HTTPException(status_code=412, detail="no private key configured (IdentityVault / env)")
    try:
        await adapter.connect()
        result = await adapter.execute_buy(mint, amount_sol)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"execute failed: {exc}") from exc
    if not result:
        raise HTTPException(status_code=502, detail="execute returned no result")
    return {"success": True, "mint": mint, "amount_sol": amount_sol, "result": result}


@router.get("/dip/radar")
async def dip_radar() -> dict[str, Any]:
    from cores.trading.extra_radars import DipRadarConfig, scan_dip_candidates

    cands = await scan_dip_candidates(DipRadarConfig())
    return {"success": True, "count": len(cands), "candidates": [dataclasses.asdict(c) for c in cands]}


@router.get("/dip/last")
def dip_last() -> dict[str, Any]:
    snap = _get_engine()._store.get("dip_radar_last")  # noqa: SLF001
    if not snap:
        return {"success": True, "snapshot": None, "reason": "no snapshot yet (dip every 7m)"}
    return {"success": True, "snapshot": snap}


@router.get("/spread/radar")
async def spread_radar() -> dict[str, Any]:
    from cores.trading.extra_radars import scan_spread

    return await scan_spread()


@router.get("/spread/last")
def spread_last() -> dict[str, Any]:
    snap = _get_engine()._store.get("spread_radar_last")  # noqa: SLF001
    if not snap:
        return {"success": True, "snapshot": None, "reason": "no snapshot yet (spread every 3m)"}
    return {"success": True, "snapshot": snap}
