"""Investment API Router for OWNEX.

Exposes all investment adapters and functionality via REST API.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, RootModel

from core.investment.adapters import (
    AgentFactory,
    AgentType,
    InvestmentAdapterRegistry,
    build_agent_factory,
    build_default_registry,
)
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


class MarketDataRequest(BaseModel):
    symbols: list[str]
    source: str = "ccxt"


class BacktestRequest(BaseModel):
    strategy: str
    engine: str = "vectorbt"
    params: dict[str, Any] = {}


class ScanRequest(BaseModel):
    scanner: str = "memecoin"
    params: dict[str, Any] = {}


class WalletAnalysisRequest(BaseModel):
    address: str
    chain: str = "ethereum"


class SentimentRequest(BaseModel):
    symbols: list[str] | None = None
    limit: int = 50


class AgentCreateRequest(BaseModel):
    agent_type: str
    objective: str
    name: str | None = None
    config: dict[str, Any] = {}


class AgentRunRequest(BaseModel):
    agent_id: str


class UpdateCapitalRequest(BaseModel):
    total_usd: float


class AllocatePayoutRequest(BaseModel):
    amount: float
    source: str = ""


class DeployStrategyRequest(BaseModel):
    amount: float


class UpdateConfigRequest(BaseModel):
    config: dict[str, Any]


class UpdateConfigFlatRequest(RootModel[dict[str, Any]]):
    pass


class SnapshotRequest(BaseModel):
    pass


# ─── Adapter Management ───


@router.post("/adapters/initialize")
async def initialize_adapters(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Initialize all registered investment adapters."""
    results = await registry.initialize_all()
    return {"initialized": results, "total": len(results)}


@router.get("/adapters")
async def list_adapters(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """List all registered adapters with their status."""
    return {"adapters": registry.list_adapters()}


@router.get("/adapters/{name}")
async def get_adapter(
    name: str,
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get adapter instance by name."""
    adapter = registry.get_adapter(name)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter {name} not found")
    return {"name": name, "available": True}


# ─── Market Data ───


@router.post("/market-data")
async def get_market_data(
    request: MarketDataRequest,
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get market data from specified source."""
    return await registry.get_market_data(request.symbols, request.source)


@router.get("/exchanges")
async def list_exchanges(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """List available exchanges via CCXT."""
    adapter = registry.get_adapter("ccxt")
    if not adapter:
        raise HTTPException(status_code=404, detail="CCXT adapter not available")
    try:
        info = await adapter.get_exchange_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ─── Backtesting ───


@router.post("/backtest")
async def run_backtest(
    request: BacktestRequest,
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Run backtest using specified engine."""
    return await registry.run_backtest(request.strategy, request.engine, **request.params)


@router.get("/strategies/freqtrade")
async def list_freqtrade_strategies(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """List available strategies (Freqtrade)."""
    adapter = registry.get_adapter("freqtrade")
    if not adapter:
        raise HTTPException(status_code=404, detail="Freqtrade adapter not available")
    if hasattr(adapter, "list_strategies"):
        return await adapter.list_strategies()
    return {"strategies": []}


# ─── Opportunity Scanning ───


@router.post("/scan")
async def scan_opportunities(
    request: ScanRequest,
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Scan for opportunities using specified scanner."""
    results = await registry.scan_opportunities(request.scanner, **request.params)
    return {"scanner": request.scanner, "opportunities": results, "count": len(results)}


@router.get("/scanners")
async def list_scanners() -> dict[str, Any]:
    """List available opportunity scanners."""
    return {
        "scanners": [
            {"id": "memecoin", "name": "Memecoin Scanner", "description": "New token detection with risk analysis"},
            {"id": "polymarket", "name": "Polymarket Scanner", "description": "Prediction market mispricing detection"},
            {"id": "arbitrage", "name": "Global Arbitrage", "description": "Cross-exchange arbitrage opportunities"},
            {"id": "yield", "name": "Yield Opportunities", "description": "DeFi yield farming opportunities"},
        ]
    }


# ─── Wallet & On-Chain Analytics ───


@router.post("/wallet/analyze")
async def analyze_wallet(
    request: WalletAnalysisRequest,
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Analyze wallet address."""
    return await registry.analyze_wallet(request.address, request.chain)


@router.get("/whales")
async def track_whales(
    min_balance: float = Query(1_000_000, description="Minimum balance in USD"),
    chains: list[str] = Query(["ethereum", "solana"]),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Track whale wallets."""
    adapter = registry.get_adapter("onchain_analytics")
    if not adapter:
        raise HTTPException(status_code=404, detail="On-chain analytics not available")
    if hasattr(adapter, "track_whales"):
        return await adapter.track_whales(min_balance, chains)
    return {"whales": []}


@router.get("/large-transfers")
async def large_transfers(
    chain: str = Query("ethereum"),
    min_value: float = Query(100_000),
    hours: int = Query(24),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Detect large on-chain transfers."""
    adapter = registry.get_adapter("onchain_analytics")
    if not adapter:
        raise HTTPException(status_code=404, detail="On-chain analytics not available")
    if hasattr(adapter, "detect_large_transfers"):
        return await adapter.detect_large_transfers(chain, min_value, hours)
    return {"transfers": []}


# ─── Sentiment Analysis ───


@router.post("/sentiment/news")
async def news_sentiment(
    request: SentimentRequest,
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get news sentiment for symbols."""
    adapter = registry.get_adapter("sentiment")
    if not adapter:
        raise HTTPException(status_code=404, detail="Sentiment adapter not available")
    return await adapter.get_news_sentiment(request.symbols, request.limit)


@router.post("/sentiment/symbol/{symbol}")
async def symbol_sentiment(
    symbol: str,
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Comprehensive sentiment analysis for a symbol."""
    adapter = registry.get_adapter("sentiment")
    if not adapter:
        raise HTTPException(status_code=404, detail="Sentiment adapter not available")
    return await adapter.analyze_symbol_sentiment(symbol)


@router.get("/sentiment/fear-greed")
async def fear_greed(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get Fear & Greed Index."""
    adapter = registry.get_adapter("sentiment")
    if not adapter:
        raise HTTPException(status_code=404, detail="Sentiment adapter not available")
    return await adapter.get_fear_greed_index()


@router.get("/sentiment/market-regime")
async def market_regime(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get current market regime detection."""
    adapter = registry.get_adapter("sentiment")
    if not adapter:
        raise HTTPException(status_code=404, detail="Sentiment adapter not available")
    return await adapter.get_market_regime()


# ─── AI Agent Factory ───


@router.post("/agents/create")
async def create_agent(
    request: AgentCreateRequest,
    factory: AgentFactory = Depends(get_agent_factory),
) -> dict[str, Any]:
    """Create a new specialized AI agent."""
    try:
        agent_type = AgentType(request.agent_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {request.agent_type}") from None

    agent = factory.create_agent(
        agent_type=agent_type,
        objective=request.objective,
        name=request.name,
        custom_config=request.config,
    )
    return {
        "agent_id": agent.spec.agent_id,
        "name": agent.spec.name,
        "type": agent.spec.agent_type.value,
        "objective": agent.spec.objective,
        "status": agent.status.value,
    }


@router.post("/agents/{agent_id}/run")
async def run_agent(
    agent_id: str,
    factory: AgentFactory = Depends(get_agent_factory),
) -> dict[str, Any]:
    """Run an agent to completion."""
    return await factory.run_agent(agent_id)


@router.get("/agents")
async def list_agents(
    factory: AgentFactory = Depends(get_agent_factory),
) -> dict[str, Any]:
    """List all created agents."""
    return {"agents": factory.list_agents()}


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    factory: AgentFactory = Depends(get_agent_factory),
) -> dict[str, Any]:
    """Get agent details."""
    agent = factory.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": agent.spec.agent_id,
        "name": agent.spec.name,
        "type": agent.spec.agent_type.value,
        "objective": agent.spec.objective,
        "status": agent.status.value,
        "progress": agent.progress,
        "outputs": agent.outputs,
        "logs": agent.logs[-10:],  # Last 10 logs
    }


@router.get("/agent-types")
async def list_agent_types() -> dict[str, Any]:
    """List available agent types."""
    return {"types": [{"id": t.value, "name": t.value.replace("_", " ").title()} for t in AgentType]}


# ─── Quantitative Analysis ───


@router.post("/quant/backtest")
async def quant_backtest(
    request: BacktestRequest,
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Run quantitative backtest."""
    return await registry.run_backtest(request.strategy, request.engine, **request.params)


@router.get("/quant/indicators")
async def quant_indicators(
    symbols: list[str] = Query(...),
    engine: str = "vectorbt",
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get technical indicators for symbols."""
    return await registry.get_quant_analysis(symbols, "indicators")


# ─── Investment Manager Integration ───


@router.get("/portfolio")
async def get_portfolio(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Get portfolio snapshot."""
    snap = manager.snapshot()
    return snap.to_dict()


@router.get("/portfolio/risk")
async def get_risk_report(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Get comprehensive risk report."""
    return manager.risk_report()


@router.post("/portfolio/deploy")
async def deploy_capital(
    strategy_id: str,
    amount: float,
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Deploy capital to a strategy."""
    return manager.deploy(strategy_id, amount)


@router.post("/portfolio/record-trade")
async def record_trade(
    strategy_id: str,
    symbol: str,
    side: str,
    entry_price: float,
    exit_price: float,
    quantity: float,
    pnl: float,
    pnl_pct: float,
    fee: float = 0.0,
    duration_hours: float = 0.0,
    metadata: dict[str, Any] | None = None,
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Record trade result."""
    return manager.record_trade_result(
        strategy_id, symbol, side, entry_price, exit_price, quantity, pnl, pnl_pct, fee, duration_hours, metadata
    )


@router.post("/max-revenue")
async def activate_max_revenue(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Activate maximum revenue mode."""
    return manager.activate_max_revenue_mode()


@router.post("/portfolio/max-revenue")
async def activate_max_revenue_portfolio(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Activate maximum revenue mode (portfolio path)."""
    return manager.activate_max_revenue_mode()


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


# ─── System ───


# ─── Investment Management (Frontend Hub) ───


@router.get("/status")
async def get_investment_status() -> dict[str, Any]:
    """Get investment system status - capital, deployed, available, P&L, strategies."""
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


@router.get("/snapshot")
async def get_snapshot(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Get investment snapshot."""
    snap = manager.snapshot()
    return {"success": True, "snapshot": snap.to_dict()}


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


@router.get("/allocation")
async def get_allocation() -> dict[str, Any]:
    """Get current allocation and config."""
    manager = get_investment_manager()
    return {
        "success": True,
        "allocation": manager.get_allocation(),
        "config": manager.get_config(),
    }


@router.get("/exposure")
async def get_exposure() -> dict[str, Any]:
    """Get exposure and risk limits."""
    manager = get_investment_manager()
    return {"success": True, "exposure": manager.get_exposure()}


@router.get("/events")
async def get_investment_events(limit: int = 50) -> dict[str, Any]:
    """Get recent investment events."""
    manager = get_investment_manager()
    events = manager.get_events(limit)
    return {"success": True, "events": events}


@router.post("/strategies/{strategy_id}/deploy")
async def deploy_strategy(strategy_id: str, request: DeployStrategyRequest) -> dict[str, Any]:
    """Deploy capital to a strategy."""
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


@router.post("/allocation/allocate-payout")
async def allocate_payout(request: AllocatePayoutRequest) -> dict[str, Any]:
    """Allocate payout to investment capital."""
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be greater than zero")
    manager = get_investment_manager()
    allocation = manager.allocate_payout(request.amount, request.source)
    return {"success": True, "allocation": allocation}


@router.post("/allocation/update-capital")
async def update_capital(request: UpdateCapitalRequest) -> dict[str, Any]:
    """Update total investment capital."""
    manager = get_investment_manager()
    manager.update_total_capital(request.total_usd)
    return {"success": True, "total_capital_usd": request.total_usd}


@router.post("/config")
async def update_config(request: UpdateConfigFlatRequest) -> dict[str, Any]:
    """Update investment configuration."""
    manager = get_investment_manager()
    manager.update_config(**request.model_dump())
    return {"success": True, "config": manager.get_config()}


@router.get("/ccxt/info")
async def ccxt_info(exchange: str = "binance") -> dict[str, Any]:
    """Get exchange info via CCXT."""
    registry = get_registry()
    adapter = registry.get_adapter("ccxt")
    if not adapter:
        raise HTTPException(status_code=404, detail="CCXT adapter not available")
    try:
        info = await adapter.get_exchange_info()
        return {"success": True, "exchange": exchange, "info": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ccxt/connect")
async def ccxt_connect(exchange: str, api_key: str, api_secret: str) -> dict[str, Any]:
    """Connect to exchange via CCXT."""
    registry = get_registry()
    adapter = registry.get_adapter("ccxt")
    if not adapter:
        raise HTTPException(status_code=404, detail="CCXT adapter not available")
    try:
        connected = await adapter.connect(exchange, api_key, api_secret)
        return {"success": connected, "connected": connected}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/ccxt/balance")
async def ccxt_balance(exchange: str = "binance") -> dict[str, Any]:
    """Get balance from exchange."""
    registry = get_registry()
    adapter = registry.get_adapter("ccxt")
    if not adapter:
        raise HTTPException(status_code=404, detail="CCXT adapter not available")
    try:
        balance = await adapter.get_balance()
        return {"success": True, "balance": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ─── Stocks & Options ───


@router.get("/stocks/algopaca")
async def alpaca_info(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get Alpaca adapter info."""
    adapter = registry.get_adapter("alpaca")
    if not adapter:
        raise HTTPException(status_code=404, detail="Alpaca adapter not available")
    return {"success": True, "adapter": adapter.name, "connected": adapter.is_connected}


@router.post("/stocks/algopaca/connect")
async def alpaca_connect(
    api_key: str = Query(...),
    secret_key: str = Query(...),
    base_url: str = Query("https://paper-api.alpaca.markets"),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Connect to Alpaca Markets."""
    adapter = registry.get_adapter("alpaca")
    if not adapter:
        raise HTTPException(status_code=404, detail="Alpaca adapter not available")
    adapter._api_key = api_key
    adapter._secret_key = secret_key
    adapter._base_url = base_url
    connected = await adapter.connect()
    return {"success": connected, "connected": connected}


@router.get("/stocks/algopaca/account")
async def alpaca_account(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get Alpaca account info."""
    adapter = registry.get_adapter("alpaca")
    if not adapter:
        raise HTTPException(status_code=404, detail="Alpaca adapter not available")
    return {"success": True, "account": await adapter.get_account()}


@router.get("/stocks/algopaca/positions")
async def alpaca_positions(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get Alpaca positions."""
    adapter = registry.get_adapter("alpaca")
    if not adapter:
        raise HTTPException(status_code=404, detail="Alpaca adapter not available")
    return {"success": True, "positions": await adapter.get_positions()}


@router.post("/stocks/algopaca/order")
async def alpaca_place_order(
    symbol: str = Query(...),
    side: str = Query(...),
    qty: float = Query(...),
    order_type: str = Query("market"),
    time_in_force: str = Query("day"),
    limit_price: float | None = Query(None),
    stop_price: float | None = Query(None),
    take_profit: float | None = Query(None),
    stop_loss: float | None = Query(None),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Place a stock or options order via Alpaca."""
    adapter = registry.get_adapter("alpaca")
    if not adapter:
        raise HTTPException(status_code=404, detail="Alpaca adapter not available")
    result = await adapter.place_order(
        symbol=symbol,
        side=side,
        qty=qty,
        order_type=order_type,
        time_in_force=time_in_force,
        limit_price=limit_price,
        stop_price=stop_price,
        take_profit=take_profit,
        stop_loss=stop_loss,
    )
    return {"success": result.get("status") == "accepted", "result": result}


@router.get("/stocks/algopaca/market-data")
async def alpaca_market_data(
    symbol: str = Query(...),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get market data for a symbol via Alpaca."""
    adapter = registry.get_adapter("alpaca")
    if not adapter:
        raise HTTPException(status_code=404, detail="Alpaca adapter not available")
    return {"success": True, "data": await adapter.get_market_data(symbol)}


@router.get("/stocks/algopaca/options-chain")
async def alpaca_options_chain(
    underlying: str = Query(...),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get options chain for an underlying equity."""
    adapter = registry.get_adapter("alpaca")
    if not adapter:
        raise HTTPException(status_code=404, detail="Alpaca adapter not available")
    return {"success": True, "options": await adapter.get_option_chain(underlying)}


@router.get("/stocks/ibkr")
async def ibkr_info(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get IBKR adapter info."""
    adapter = registry.get_adapter("ibkr")
    if not adapter:
        raise HTTPException(status_code=404, detail="IBKR adapter not available")
    return {"success": True, "adapter": adapter.name, "connected": adapter.is_connected}


@router.post("/stocks/ibkr/connect")
async def ibkr_connect(
    host: str = Query("127.0.0.1"),
    port: int = Query(7497),
    client_id: int = Query(1),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Connect to IBKR TWS/Gateway."""
    adapter = registry.get_adapter("ibkr")
    if not adapter:
        raise HTTPException(status_code=404, detail="IBKR adapter not available")
    adapter._host = host
    adapter._port = port
    adapter._client_id = client_id
    connected = await adapter.connect()
    return {"success": connected, "connected": connected}


@router.get("/stocks/ibkr/account")
async def ibkr_account(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get IBKR account info."""
    adapter = registry.get_adapter("ibkr")
    if not adapter:
        raise HTTPException(status_code=404, detail="IBKR adapter not available")
    return {"success": True, "account": await adapter.get_account()}


@router.get("/stocks/ibkr/positions")
async def ibkr_positions(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get IBKR positions."""
    adapter = registry.get_adapter("ibkr")
    if not adapter:
        raise HTTPException(status_code=404, detail="IBKR adapter not available")
    return {"success": True, "positions": await adapter.get_positions()}


@router.post("/stocks/ibkr/order")
async def ibkr_place_order(
    symbol: str = Query(...),
    side: str = Query(...),
    qty: float = Query(...),
    order_type: str = Query("MKT"),
    sec_type: str = Query("STK"),
    exchange: str = Query("SMART"),
    currency: str = Query("USD"),
    strike: float | None = Query(None),
    right: str | None = Query(None),
    last_trade_date_or_contract_month: str | None = Query(None),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Place a stock/options/futures order via IBKR."""
    adapter = registry.get_adapter("ibkr")
    if not adapter:
        raise HTTPException(status_code=404, detail="IBKR adapter not available")
    result = await adapter.place_order(
        symbol=symbol,
        side=side,
        qty=qty,
        order_type=order_type,
        sec_type=sec_type,
        exchange=exchange,
        currency=currency,
        strike=strike,
        right=right,
        last_trade_date_or_contract_month=last_trade_date_or_contract_month,
    )
    return {"success": result.get("status") in ("accepted", "placed", "filled"), "result": result}


# ─── DeFi Yield ───


@router.get("/defi/aave/info")
async def aave_info(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get Aave adapter info."""
    adapter = registry.get_adapter("aave")
    if not adapter:
        raise HTTPException(status_code=404, detail="Aave adapter not available")
    return {"success": True, "adapter": adapter.name, "connected": adapter.is_connected}


@router.post("/defi/aave/connect")
async def aave_connect(
    chain: str = Query("ethereum"),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Connect to Aave on specified chain."""
    adapter = registry.get_adapter("aave")
    if not adapter:
        raise HTTPException(status_code=404, detail="Aave adapter not available")
    adapter._chain = chain
    connected = await adapter.connect()
    return {"success": connected, "connected": connected}


@router.get("/defi/aave/supply-apy")
async def aave_supply_apy(
    asset: str = Query("USDC"),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get supply APY for an asset on Aave."""
    adapter = registry.get_adapter("aave")
    if not adapter:
        raise HTTPException(status_code=404, detail="Aave adapter not available")
    return {"success": True, "data": await adapter.get_supply_apy(asset)}


@router.get("/defi/aave/top-assets")
async def aave_top_assets(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get top supplied/borrowed assets on Aave."""
    adapter = registry.get_adapter("aave")
    if not adapter:
        raise HTTPException(status_code=404, detail="Aave adapter not available")
    return {"success": True, "assets": await adapter.get_top_assets()}


@router.get("/defi/morpho/info")
async def morpho_info(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get Morpho adapter info."""
    adapter = registry.get_adapter("morpho")
    if not adapter:
        raise HTTPException(status_code=404, detail="Morpho adapter not available")
    return {"success": True, "adapter": adapter.name, "connected": adapter.is_connected}


@router.post("/defi/morpho/connect")
async def morpho_connect(
    chain: str = Query("ethereum"),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Connect to Morpho on specified chain."""
    adapter = registry.get_adapter("morpho")
    if not adapter:
        raise HTTPException(status_code=404, detail="Morpho adapter not available")
    adapter._chain = chain
    connected = await adapter.connect()
    return {"success": connected, "connected": connected}


@router.get("/defi/morpho/market-apy")
async def morpho_market_apy(
    market_id: str = Query(...),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get APY for a specific Morpho market."""
    adapter = registry.get_adapter("morpho")
    if not adapter:
        raise HTTPException(status_code=404, detail="Morpho adapter not available")
    return {"success": True, "data": await adapter.get_market_apy(market_id)}


@router.get("/defi/morpho/top-markets")
async def morpho_top_markets(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get top Morpho markets by TVL."""
    adapter = registry.get_adapter("morpho")
    if not adapter:
        raise HTTPException(status_code=404, detail="Morpho adapter not available")
    return {"success": True, "markets": await adapter.get_top_markets()}


@router.get("/defi/pendle/info")
async def pendle_info(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get Pendle adapter info."""
    adapter = registry.get_adapter("pendle")
    if not adapter:
        raise HTTPException(status_code=404, detail="Pendle adapter not available")
    return {"success": True, "adapter": adapter.name, "connected": adapter.is_connected}


@router.post("/defi/pendle/connect")
async def pendle_connect(
    chain: str = Query("ethereum"),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Connect to Pendle on specified chain."""
    adapter = registry.get_adapter("pendle")
    if not adapter:
        raise HTTPException(status_code=404, detail="Pendle adapter not available")
    adapter._chain = chain
    connected = await adapter.connect()
    return {"success": connected, "connected": connected}


@router.get("/defi/pendle/yield-opportunities")
async def pendle_yield_opportunities(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get yield opportunities with PT/YT pricing data."""
    adapter = registry.get_adapter("pendle")
    if not adapter:
        raise HTTPException(status_code=404, detail="Pendle adapter not available")
    return {"success": True, "opportunities": await adapter.get_yield_opportunities()}


@router.get("/defi/pendle/pt-yield")
async def pendle_pt_yield(
    market_id: str = Query(...),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get PT yield data for a specific Pendle market."""
    adapter = registry.get_adapter("pendle")
    if not adapter:
        raise HTTPException(status_code=404, detail="Pendle adapter not available")
    return {"success": True, "data": await adapter.get_pt_yield(market_id)}


@router.get("/defi/lido/info")
async def lido_info(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get Lido adapter info."""
    adapter = registry.get_adapter("lido")
    if not adapter:
        raise HTTPException(status_code=404, detail="Lido adapter not available")
    return {"success": True, "adapter": adapter.name, "connected": adapter.is_connected}


@router.post("/defi/lido/connect")
async def lido_connect(
    chain: str = Query("ethereum"),
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Connect to Lido on specified chain."""
    adapter = registry.get_adapter("lido")
    if not adapter:
        raise HTTPException(status_code=404, detail="Lido adapter not available")
    adapter._chain = chain
    connected = await adapter.connect()
    return {"success": connected, "connected": connected}


@router.get("/defi/lido/staking-apy")
async def lido_staking_apy(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get current staking APY and TVL for Lido."""
    adapter = registry.get_adapter("lido")
    if not adapter:
        raise HTTPException(status_code=404, detail="Lido adapter not available")
    return {"success": True, "data": await adapter.get_staking_apy()}


@router.get("/defi/lido/protocol-metrics")
async def lido_protocol_metrics(
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get Lido protocol-wide metrics."""
    adapter = registry.get_adapter("lido")
    if not adapter:
        raise HTTPException(status_code=404, detail="Lido adapter not available")
    return {"success": True, "metrics": await adapter.get_protocol_metrics()}


# ─── Polymarket Strategies ───


@router.get("/polymarket/strategies")
async def list_polymarket_strategies() -> dict[str, Any]:
    """List all available Polymarket strategies."""
    from core.polymarket.manager import list_strategies

    return {"success": True, "strategies": list_strategies()}


@router.post("/polymarket/strategies/{strategy_name}/run")
async def run_polymarket_strategy(
    strategy_name: str,
    registry: InvestmentAdapterRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Run a Polymarket strategy scan."""
    from core.polymarket.manager import PolymarketManager

    manager = PolymarketManager()
    result = await manager.run_scan(strategy_name)
    return {"success": True, "strategy": strategy_name, "result": result}


@router.get("/polymarket/strategies/diagnostic")
async def polymarket_diagnostic() -> dict[str, Any]:
    """Run full diagnostic on all Polymarket strategies."""
    from core.polymarket.manager import PolymarketManager

    manager = PolymarketManager()
    result = await manager.full_diagnostic()
    return {"success": True, "diagnostic": result}


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
