"""Investment API Router for OWNEX.

Exposes investment management, strategies, and portfolio via REST API.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, RootModel

from core.investment.adapters import (
    AgentFactory,
    InvestmentAdapterRegistry,
    build_agent_factory,
    build_default_registry,
)
from core.investment.adapters import (
    build_aave_adapter as _build_aave,
)
from core.investment.adapters import (
    build_alpaca_adapter as _build_alpaca,
)
from core.investment.adapters import (
    build_ibkr_adapter as _build_ibkr,
)
from core.investment.adapters import (
    build_lido_adapter as _build_lido,
)
from core.investment.adapters import (
    build_morpho_adapter as _build_morpho,
)
from core.investment.adapters import (
    build_pendle_adapter as _build_pendle,
)
from core.investment.adapters import (
    build_polymarket_adapter as _build_polymarket,
)
from core.investment.adapters.ccxt_adapter import CCXTAdapter as _CCXTAdapter
from core.investment.manager import get_investment_manager
from core.investment.models import get_strategy

logger = logging.getLogger("orion.api.investment")

router = APIRouter(prefix="/api/investment", tags=["investment"])

# Global registry instance
_registry: InvestmentAdapterRegistry | None = None
_agent_factory: AgentFactory | None = None


def get_registry() -> InvestmentAdapterRegistry:
    global _registry
    if _registry is None:
        _registry = build_default_registry()
    return _registry


def get_agent_factory() -> AgentFactory:
    global _agent_factory
    if _agent_factory is None:
        _agent_factory = build_agent_factory()
    return _agent_factory


# ─── Request/Response Models ───


class UpdateCapitalRequest(BaseModel):
    total_usd: float


class AllocatePayoutRequest(BaseModel):
    amount: float
    source: str = ""


class DeployStrategyRequest(BaseModel):
    amount: float


class UpdateConfigFlatRequest(RootModel[dict[str, Any]]):
    pass


# ─── Snapshot ───


@router.get("/snapshot")
async def get_snapshot(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Get investment snapshot."""
    snap = manager.snapshot()
    return {"success": True, "snapshot": snap.to_dict()}


# ─── Strategies ───


@router.get("/strategies")
async def list_strategies(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """List all available strategies."""
    strategies = manager.list_strategies()
    return {"success": True, "strategies": strategies}


@router.get("/strategies/{strategy_id}")
async def get_strategy_detail(
    strategy_id: str,
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Get strategy detail by ID."""
    sdef = get_strategy(strategy_id)
    if not sdef:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    from core.investment.allocation import get_allocation_controller

    ctrl = get_allocation_controller()
    alloc = ctrl.get_strategy_allocation(strategy_id)
    active = strategy_id in manager._active_strategies
    paused = manager.is_strategy_paused(strategy_id)
    deploy_info = manager._active_strategies.get(strategy_id, {})
    return {
        "success": True,
        "strategy": {
            "profile": sdef.__dict__,
            "active": active,
            "paused": paused,
            "allocation": alloc.__dict__ if alloc else {},
            "total_deployed": deploy_info.get("total_deployed", 0.0),
        },
    }


# ─── Strategy Actions ───


@router.post("/strategies/{strategy_id}/deploy")
async def deploy_strategy(strategy_id: str, request: DeployStrategyRequest) -> dict[str, Any]:
    """Deploy capital to a strategy."""
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be greater than zero")
    if not get_strategy(strategy_id):
        raise HTTPException(status_code=400, detail=f"Strategy {strategy_id} not found")
    manager = get_investment_manager()
    result = manager.deploy_strategy(strategy_id, request.amount)
    return {"success": result.get("success", False), "result": result}


@router.post("/strategies/{strategy_id}/pause")
async def pause_strategy(strategy_id: str) -> dict[str, Any]:
    """Pause a strategy."""
    manager = get_investment_manager()
    success = manager.pause_strategy(strategy_id)
    return {"success": True, "paused": success}


@router.post("/strategies/{strategy_id}/resume")
async def resume_strategy(strategy_id: str) -> dict[str, Any]:
    """Resume a strategy."""
    manager = get_investment_manager()
    success = manager.resume_strategy(strategy_id)
    return {"success": True, "paused": not success}


# ─── Allocation ───


@router.get("/allocation")
async def get_allocation() -> dict[str, Any]:
    """Get current allocation and config."""
    manager = get_investment_manager()
    return {
        "success": True,
        "allocation": manager.get_allocation(),
        "config": manager.get_config(),
    }


@router.post("/allocation/update-capital")
async def update_capital(request: UpdateCapitalRequest) -> dict[str, Any]:
    """Update total investment capital."""
    manager = get_investment_manager()
    manager.update_total_capital(request.total_usd)
    return {"success": True, "total_capital_usd": request.total_usd}


@router.post("/allocation/allocate-payout")
async def allocate_payout(request: AllocatePayoutRequest) -> dict[str, Any]:
    """Allocate payout to investment capital."""
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be greater than zero")
    manager = get_investment_manager()
    allocation = manager.allocate_payout(request.amount, request.source)
    return {"success": True, "allocation": allocation}


# ─── Portfolio ───


@router.get("/portfolio")
async def get_portfolio(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Get portfolio snapshot."""
    snap = manager.snapshot()
    return snap.to_dict()


@router.get("/exposure")
async def get_exposure() -> dict[str, Any]:
    """Get exposure and risk limits."""
    manager = get_investment_manager()
    return {"success": True, "exposure": manager.get_exposure()}


# ─── System ───


@router.get("/status")
async def get_investment_status() -> dict[str, Any]:
    """Get investment system status."""
    manager = get_investment_manager()
    status = manager.get_status()
    return {"success": True, "status": status}


@router.get("/metrics")
async def get_investment_metrics() -> dict[str, Any]:
    """Get consolidated metrics including P&L chart."""
    manager = get_investment_manager()
    metrics = manager.get_metrics()
    pnl_chart = manager.get_pnl_chart()
    return {"success": True, "metrics": metrics, "pnl_chart": pnl_chart}


@router.get("/events")
async def get_investment_events(limit: int = 50) -> dict[str, Any]:
    """Get recent investment events."""
    manager = get_investment_manager()
    events = manager.get_events(limit)
    return {"success": True, "events": events}


@router.post("/pause")
async def pause_all(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Pause all investment strategies."""
    manager.pause_all()
    return {"success": True, "paused": True}


@router.post("/resume")
async def resume_all(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Resume all investment strategies."""
    manager.resume_all()
    return {"success": True, "paused": False}


@router.post("/max-revenue")
async def activate_max_revenue(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Activate maximum revenue mode."""
    return manager.activate_max_revenue_mode()


@router.post("/config")
async def update_config(request: UpdateConfigFlatRequest) -> dict[str, Any]:
    """Update investment configuration."""
    manager = get_investment_manager()
    manager.update_config(**request.model_dump())
    return {"success": True, "config": manager.get_config()}


# ─── CCXT ───


@router.get("/ccxt/info")
async def ccxt_info(exchange: str = "binance") -> dict[str, Any]:
    """Get exchange info via CCXT."""
    registry = get_registry()
    adapter = registry.get_adapter("ccxt")
    if not adapter:
        await registry.initialize_all()
        adapter = registry.get_adapter("ccxt")
    if not adapter:
        raise HTTPException(status_code=404, detail="CCXT adapter not available")
    try:
        info = await adapter.get_exchange_info()
        return {"success": True, "exchange": exchange, "info": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ─── Health ───


@router.get("/health")
async def health_check(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Health check for investment system."""
    adapters = registry.list_adapters()
    initialized = sum(1 for a in adapters if a["initialized"])
    return {
        "status": "healthy" if initialized > 0 else "degraded",
        "adapters_total": len(adapters),
        "adapters_initialized": initialized,
        "registry_ready": True,
    }


# Include in main
def get_investment_router() -> APIRouter:
    return router


def register_investment_capabilities() -> None:
    """Register investment capabilities with the system."""
    # Capabilities are auto-registered via the investment manager and adapters
    pass


# ─── Sub-adapter wiring (frontend contracts: Trading/InvestmentHub) ─────────
# Los adapters existen en core/investment/adapters/*; estas rutas finas los
# exponen con las shapes exactas que consume el frontend. Creds pasan por
# request y NUNCA se persisten ni loguean.


class CCXTConnectRequest(BaseModel):
    exchange: str = "binance"
    api_key: str = ""
    api_secret: str = ""
    password: str = ""
    testnet: bool = False


async def _fresh_adapter(name: str, config: dict[str, Any] | None = None) -> Any:
    """Instancia efímera del adapter (creds por-request, sin estado global)."""
    builders: dict[str, Any] = {
        "ccxt": lambda cfg: _CCXTAdapter(exchange_id=cfg.pop("exchange", "binance"), config=cfg),
        "alpaca": _build_alpaca,
        "ibkr": _build_ibkr,
        "aave": _build_aave,
        "morpho": _build_morpho,
        "pendle": _build_pendle,
        "lido": _build_lido,
        "polymarket": _build_polymarket,
    }
    factory = builders.get(name)
    if not factory:
        raise HTTPException(status_code=404, detail=f"Adapter '{name}' no disponible")
    return factory(dict(config or {}))


def _adapter_info(adapter: Any) -> dict[str, Any]:
    return {
        "success": True,
        "adapter": getattr(adapter, "name", "unknown"),
        "connected": bool(getattr(adapter, "is_connected", False)),
    }


# ── CCXT ──


@router.post("/ccxt/connect")
async def ccxt_connect(body: CCXTConnectRequest) -> dict[str, Any]:
    adapter = await _fresh_adapter("ccxt", body.model_dump())
    connected = await adapter.connect()
    return {"success": True, "connected": bool(connected)}


@router.get("/ccxt/balance")
async def ccxt_balance(exchange: str = "binance") -> dict[str, Any]:
    registry = get_registry()
    adapter = registry.get_adapter("ccxt")
    if not adapter:
        await registry.initialize_all()
        adapter = registry.get_adapter("ccxt")
    if not adapter:
        raise HTTPException(status_code=404, detail="CCXT adapter not available")
    try:
        balance = await adapter.get_balance()
        return {"success": True, "balance": balance}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


# ── Stocks (Alpaca / IBKR) ───


class AlpacaConnectRequest(BaseModel):
    api_key: str = ""
    secret_key: str = ""
    base_url: str | None = None


class AlpacaOrderRequest(BaseModel):
    symbol: str
    side: str
    qty: float
    order_type: str | None = None
    take_profit: float | None = None
    stop_loss: float | None = None


class IBKRConnectRequest(BaseModel):
    host: str | None = None
    port: int | None = None
    client_id: int | None = None


class IBKROrderRequest(BaseModel):
    symbol: str
    side: str
    qty: float
    order_type: str | None = None
    sec_type: str | None = None
    strike: float | None = None
    right: str | None = None


def _order_gate() -> None:
    """Órdenes reales bloqueadas si el manager está pausado globalmente."""
    manager = get_investment_manager()
    if manager.is_paused():
        raise HTTPException(status_code=409, detail="Investment system paused — orders blocked")


@router.get("/stocks/algopaca")
async def alpaca_info() -> dict[str, Any]:
    return _adapter_info(await _fresh_adapter("alpaca", {}))


@router.post("/stocks/algopaca/connect")
async def alpaca_connect(body: AlpacaConnectRequest) -> dict[str, Any]:
    cfg = {"api_key": body.api_key, "secret_key": body.secret_key}
    if body.base_url:
        cfg["base_url"] = body.base_url
    adapter = await _fresh_adapter("alpaca", cfg)
    connected = await adapter.connect()
    return {"success": True, "connected": bool(connected)}


@router.get("/stocks/algopaca/account")
async def alpaca_account() -> dict[str, Any]:
    return {"success": True, "account": await (await _fresh_adapter("alpaca", {})).get_account()}


@router.get("/stocks/algopaca/positions")
async def alpaca_positions() -> dict[str, Any]:
    return {"success": True, "positions": await (await _fresh_adapter("alpaca", {})).get_positions()}


@router.post("/stocks/algopaca/order")
async def alpaca_order(body: AlpacaOrderRequest) -> dict[str, Any]:
    _order_gate()
    result = await (await _fresh_adapter("alpaca", {})).place_order(
        symbol=body.symbol,
        side=body.side,
        qty=body.qty,
        order_type=(body.order_type or "market").lower(),
        take_profit=body.take_profit,
        stop_loss=body.stop_loss,
    )
    return {"success": "error" not in result, "result": result}


@router.get("/stocks/algopaca/market-data")
async def alpaca_market_data(symbol: str = "AAPL") -> dict[str, Any]:
    return {"success": True, "data": await (await _fresh_adapter("alpaca", {})).get_market_data(symbol)}


@router.get("/stocks/algopaca/options-chain")
async def alpaca_options_chain(underlying: str = "SPY") -> dict[str, Any]:
    return {"success": True, "options": await (await _fresh_adapter("alpaca", {})).get_option_chain(underlying)}


@router.get("/stocks/ibkr")
async def ibkr_info() -> dict[str, Any]:
    return _adapter_info(await _fresh_adapter("ibkr", {}))


@router.post("/stocks/ibkr/connect")
async def ibkr_connect(body: IBKRConnectRequest) -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    if body.host:
        cfg["host"] = body.host
    if body.port:
        cfg["port"] = body.port
    if body.client_id is not None:
        cfg["client_id"] = body.client_id
    adapter = await _fresh_adapter("ibkr", cfg)
    connected = await adapter.connect()
    return {"success": True, "connected": bool(connected)}


@router.get("/stocks/ibkr/account")
async def ibkr_account() -> dict[str, Any]:
    return {"success": True, "account": await (await _fresh_adapter("ibkr", {})).get_account()}


@router.get("/stocks/ibkr/positions")
async def ibkr_positions() -> dict[str, Any]:
    return {"success": True, "positions": await (await _fresh_adapter("ibkr", {})).get_positions()}


@router.post("/stocks/ibkr/order")
async def ibkr_order(body: IBKROrderRequest) -> dict[str, Any]:
    _order_gate()
    kwargs: dict[str, Any] = {"symbol": body.symbol, "side": body.side, "qty": body.qty}
    if body.order_type:
        kwargs["order_type"] = body.order_type
    if body.sec_type:
        kwargs["sec_type"] = body.sec_type
    if body.strike is not None:
        kwargs["strike"] = body.strike
    if body.right:
        kwargs["right"] = body.right
    result = await (await _fresh_adapter("ibkr", {})).place_order(**kwargs)
    return {"success": "error" not in result and result.get("status") != "not_connected", "result": result}


# ── DeFi (Aave / Morpho / Pendle / Lido) ─── read-only yields, sin keys.


async def _defi_call(provider: str, coro: Any) -> dict[str, Any]:
    try:
        return {"success": True, "data": await coro}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/defi/aave/info")
async def aave_info() -> dict[str, Any]:
    return _adapter_info(await _fresh_adapter("aave", {}))


@router.post("/defi/aave/connect")
async def aave_connect(chain: str | None = None) -> dict[str, Any]:
    adapter = await _fresh_adapter("aave", {"chain": chain} if chain else {})
    return {"success": True, "connected": bool(await adapter.connect())}


@router.get("/defi/aave/supply-apy")
async def aave_supply_apy(asset: str = "USDC") -> dict[str, Any]:
    return await _defi_call("aave", (await _fresh_adapter("aave", {})).get_supply_apy(asset))


@router.get("/defi/aave/top-assets")
async def aave_top_assets() -> dict[str, Any]:
    return {"success": True, "assets": await (await _fresh_adapter("aave", {})).get_top_assets()}


@router.get("/defi/morpho/info")
async def morpho_info() -> dict[str, Any]:
    return _adapter_info(await _fresh_adapter("morpho", {}))


@router.post("/defi/morpho/connect")
async def morpho_connect(chain: str | None = None) -> dict[str, Any]:
    adapter = await _fresh_adapter("morpho", {"chain": chain} if chain else {})
    return {"success": True, "connected": bool(await adapter.connect())}


@router.get("/defi/morpho/market-apy")
async def morpho_market_apy(market_id: str) -> dict[str, Any]:
    return await _defi_call("morpho", (await _fresh_adapter("morpho", {})).get_market_apy(market_id))


@router.get("/defi/morpho/top-markets")
async def morpho_top_markets() -> dict[str, Any]:
    return {"success": True, "markets": await (await _fresh_adapter("morpho", {})).get_top_markets()}


@router.get("/defi/pendle/info")
async def pendle_info() -> dict[str, Any]:
    return _adapter_info(await _fresh_adapter("pendle", {}))


@router.post("/defi/pendle/connect")
async def pendle_connect(chain: str | None = None) -> dict[str, Any]:
    adapter = await _fresh_adapter("pendle", {"chain": chain} if chain else {})
    return {"success": True, "connected": bool(await adapter.connect())}


@router.get("/defi/pendle/yield-opportunities")
async def pendle_yield_opportunities() -> dict[str, Any]:
    return {"success": True, "opportunities": await (await _fresh_adapter("pendle", {})).get_yield_opportunities()}


@router.get("/defi/pendle/pt-yield")
async def pendle_pt_yield(market_id: str) -> dict[str, Any]:
    return await _defi_call("pendle", (await _fresh_adapter("pendle", {})).get_pt_yield(market_id))


@router.get("/defi/lido/info")
async def lido_info() -> dict[str, Any]:
    return _adapter_info(await _fresh_adapter("lido", {}))


@router.post("/defi/lido/connect")
async def lido_connect() -> dict[str, Any]:
    return {"success": True, "connected": bool(await (await _fresh_adapter("lido", {})).connect())}


@router.get("/defi/lido/staking-apy")
async def lido_staking_apy() -> dict[str, Any]:
    return await _defi_call("lido", (await _fresh_adapter("lido", {})).get_staking_apy())


@router.get("/defi/lido/protocol-metrics")
async def lido_protocol_metrics() -> dict[str, Any]:
    return {"success": True, "metrics": await (await _fresh_adapter("lido", {})).get_protocol_metrics()}


# ── Polymarket strategies (core/polymarket/manager) ───


def _polymarket_manager() -> Any:
    from core.polymarket.manager import PolymarketManager

    return PolymarketManager()


@router.get("/polymarket/strategies")
async def polymarket_strategies() -> dict[str, Any]:
    from core.polymarket.manager import list_strategies

    return {"success": True, "strategies": list_strategies()}


@router.get("/polymarket/strategies/diagnostic")
async def polymarket_diagnostic() -> dict[str, Any]:
    return {"success": True, "diagnostic": await _polymarket_manager().full_diagnostic()}


@router.post("/polymarket/strategies/{name}/run")
async def polymarket_run_strategy(name: str) -> dict[str, Any]:
    try:
        result = await _polymarket_manager().run_scan(name)
        return {"success": True, "result": result}
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ── Backtest MA-crossover (pandas puro sobre OHLCV de ccxt) ───


class BacktestRequest(BaseModel):
    symbol: str = "BTC/USD"
    short_ma: int = 20
    long_ma: int = 50
    initial_capital: float = 10000.0


@router.post("/backtest")
async def run_backtest(body: BacktestRequest) -> dict[str, Any]:
    """MA crossover backtest determinista (sin dependencia vectorbt)."""
    if body.short_ma >= body.long_ma:
        raise HTTPException(status_code=400, detail="short_ma debe ser < long_ma")
    registry = get_registry()
    adapter = registry.get_adapter("ccxt")
    if not adapter:
        await registry.initialize_all()
        adapter = registry.get_adapter("ccxt")
    if not adapter:
        raise HTTPException(status_code=404, detail="CCXT adapter not available")
    try:
        ohlcv = await adapter.get_ohlcv(body.symbol, timeframe="1d", limit=max(200, body.long_ma * 3))
        closes = [c[4] for c in ohlcv]
        if len(closes) <= body.long_ma:
            raise HTTPException(status_code=502, detail="Datos insuficientes para el backtest")

        import pandas as pd

        series = pd.Series(closes, dtype=float)
        short = series.rolling(body.short_ma).mean()
        long = series.rolling(body.long_ma).mean()
        position = (short > long).shift(1).fillna(0)
        returns = series.pct_change().fillna(0)
        strategy_returns = returns * position
        equity = body.initial_capital * (1 + strategy_returns).cumprod()

        trades = int((position.diff().fillna(0).abs() > 0).sum())
        total_return = float(equity.iloc[-1] / body.initial_capital - 1)
        in_market = float(position.mean())
        return {
            "success": True,
            "result": {
                "symbol": body.symbol,
                "short_ma": body.short_ma,
                "long_ma": body.long_ma,
                "initial_capital": body.initial_capital,
                "final_equity": round(float(equity.iloc[-1]), 2),
                "total_return_pct": round(total_return * 100, 2),
                "trades": trades,
                "time_in_market_pct": round(in_market * 100, 1),
                "buy_and_hold_return_pct": round(float(series.iloc[-1] / series.iloc[0] - 1) * 100, 2),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
