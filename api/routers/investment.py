"""Investment API Router for OWNEX.

Exposes all investment adapters and functionality via REST API.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from core.investment.adapters import (
    AgentFactory,
    AgentType,
    InvestmentAdapterRegistry,
    build_agent_factory,
    build_default_registry,
)
from core.investment.manager import get_investment_manager

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


@router.get("/strategies")
async def list_strategies(
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


@router.post("/portfolio/max-revenue")
async def activate_max_revenue(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Activate maximum revenue mode."""
    return manager.activate_max_revenue_mode()


@router.post("/portfolio/pause")
async def pause_all(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Pause all investment strategies."""
    manager.pause_all()
    return {"success": True, "message": "All strategies paused"}


@router.post("/portfolio/resume")
async def resume_all(
    manager=Depends(get_investment_manager),
) -> dict[str, Any]:
    """Resume all investment strategies."""
    manager.resume_all()
    return {"success": True, "message": "All strategies resumed"}


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


@router.get("/strategies")
async def list_strategies() -> dict[str, Any]:
    """List all available strategies."""
    manager = get_investment_manager()
    return {"success": True, "strategies": manager.list_strategies(), "total": len(manager.list_strategies())}


@router.post("/strategies/{strategy_id}/deploy")
async def deploy_strategy(strategy_id: str, request: DeployStrategyRequest) -> dict[str, Any]:
    """Deploy capital to a strategy."""
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
    manager = get_investment_manager()
    allocation = manager.allocate_payout(request.amount, request.source)
    return {"success": True, "allocation": allocation}


@router.post("/allocation/update-capital")
async def update_capital(request: UpdateCapitalRequest) -> dict[str, Any]:
    """Update total investment capital."""
    manager = get_investment_manager()
    manager.update_total_capital(request.total_usd)
    return {"success": True, "total_capital_usd": request.total_usd}


@router.post("/pause")
async def pause_all() -> dict[str, Any]:
    """Pause all investment strategies."""
    manager = get_investment_manager()
    manager.pause_all()
    return {"success": True, "paused": True}


@router.post("/resume")
async def resume_all() -> dict[str, Any]:
    """Resume all investment strategies."""
    manager = get_investment_manager()
    manager.resume_all()
    return {"success": True, "paused": False}


@router.post("/max-revenue")
async def activate_max_revenue() -> dict[str, Any]:
    """Activate maximum revenue mode."""
    manager = get_investment_manager()
    result = manager.activate_max_revenue()
    return {"success": True, "result": result}


@router.post("/config")
async def update_config(request: UpdateConfigRequest) -> dict[str, Any]:
    """Update investment configuration."""
    manager = get_investment_manager()
    manager.update_config(**request.config)
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


# ─── System ───


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
