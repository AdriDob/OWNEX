from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.investment.manager import get_investment_manager
from core.investment.models import STRATEGY_REGISTRY, get_strategy

logger = logging.getLogger("orion.api.investment")

router = APIRouter(prefix="/api/investment", tags=["investment"])


@router.get("/status")
async def investment_status():
    """Get complete investment system status."""
    try:
        manager = get_investment_manager()
        return {"success": True, "status": manager.risk_report()}
    except Exception as e:
        logger.exception("Investment status failed")
        return {"success": False, "error": str(e)}


@router.get("/snapshot")
async def investment_snapshot():
    """Get current investment snapshot (capital, deployed, PnL)."""
    try:
        manager = get_investment_manager()
        snap = manager.snapshot()
        return {"success": True, "snapshot": snap.to_dict()}
    except Exception as e:
        logger.exception("Investment snapshot failed")
        return {"success": False, "error": str(e)}


@router.get("/strategies")
async def list_strategies():
    """List all available investment strategies with profiles."""
    return {
        "success": True,
        "strategies": [
            {
                "id": s.id,
                "name": s.name,
                "type": s.strategy_type.value,
                "risk_level": s.risk_level.value,
                "max_allocation_pct": s.max_allocation_pct,
                "expected_roi_pct": s.expected_roi_pct,
                "max_drawdown_pct": s.max_drawdown_pct,
                "sharpe_target": s.sharpe_target,
                "requires_api_keys": s.requires_api_keys,
                "description": s.description,
                "tags": s.tags,
            }
            for s in STRATEGY_REGISTRY
        ],
        "total": len(STRATEGY_REGISTRY),
    }


@router.get("/strategies/{strategy_id}")
async def get_strategy_detail(strategy_id: str):
    """Get detailed strategy info including allocation and risk metrics."""
    sdef = get_strategy(strategy_id)
    if not sdef:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    manager = get_investment_manager()
    metrics = manager.metrics.get_strategy_metrics(strategy_id)
    alloc = manager.allocation.get_strategy_allocation(strategy_id)

    return {
        "success": True,
        "strategy": {
            "profile": {
                "id": sdef.id,
                "name": sdef.name,
                "type": sdef.strategy_type.value,
                "risk_level": sdef.risk_level.value,
                "max_allocation_pct": sdef.max_allocation_pct,
                "expected_roi_pct": sdef.expected_roi_pct,
                "description": sdef.description,
                "tags": sdef.tags,
            },
            "allocation": alloc.__dict__ if alloc else {},
            "risk_metrics": {
                "sharpe_ratio": metrics.sharpe_ratio,
                "win_rate": metrics.win_rate,
                "profit_factor": metrics.profit_factor,
                "total_trades": metrics.total_trades,
                "winning_trades": metrics.winning_trades,
                "losing_trades": metrics.losing_trades,
                "current_drawdown_pct": metrics.current_drawdown_pct,
                "max_drawdown_pct": metrics.max_drawdown_pct,
                "avg_win_pct": metrics.avg_win_pct,
                "avg_loss_pct": metrics.avg_loss_pct,
                "is_drawdown": metrics.is_drawdown,
                "should_pause": metrics.should_pause,
                "is_healthy": metrics.is_healthy,
                "consecutive_losses": metrics.consecutive_losses,
            },
            "paused": manager.is_strategy_paused(strategy_id),
        },
    }


@router.post("/strategies/{strategy_id}/deploy")
async def deploy_to_strategy(strategy_id: str, data: dict[str, Any]):
    """Deploy capital to a strategy."""
    amount = data.get("amount", 0.0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    manager = get_investment_manager()
    result = manager.deploy(strategy_id, amount)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Deployment failed"))
    return {"success": True, "result": result}


@router.post("/strategies/{strategy_id}/pause")
async def pause_strategy(strategy_id: str):
    """Pause a specific strategy."""
    manager = get_investment_manager()
    if not manager.pause_strategy(strategy_id):
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not active")
    return {"success": True, "strategy_id": strategy_id, "paused": True}


@router.post("/strategies/{strategy_id}/resume")
async def resume_strategy(strategy_id: str):
    """Resume a paused strategy."""
    manager = get_investment_manager()
    manager.resume_strategy(strategy_id)
    return {"success": True, "strategy_id": strategy_id, "paused": False}


@router.get("/exposure")
async def high_risk_exposure():
    """Get high-risk exposure report."""
    manager = get_investment_manager()
    return {"success": True, "exposure": manager.allocation.get_high_risk_exposure()}


@router.get("/allocation")
async def allocation_status():
    """Get allocation breakdown across all strategies."""
    manager = get_investment_manager()
    snap = manager.allocation.snapshot()
    return {
        "success": True,
        "allocation": snap.to_dict(),
        "config": {
            "total_capital_usd": manager.allocation.config.total_capital_usd,
            "max_high_risk_pct": manager.allocation.config.max_high_risk_pct,
            "max_speculative_pct": manager.allocation.config.max_speculative_pct,
            "emergency_reserve_pct": manager.allocation.config.emergency_reserve_pct,
            "auto_rebalance": manager.allocation.config.auto_rebalance,
        },
    }


@router.post("/allocation/update-capital")
async def update_capital(data: dict[str, Any]):
    """Update total capital amount."""
    total = data.get("total_usd", 0.0)
    if total <= 0:
        raise HTTPException(status_code=400, detail="Total capital must be positive")
    manager = get_investment_manager()
    manager.allocation.update_capital(total)
    return {"success": True, "total_capital_usd": total}


@router.post("/allocation/allocate-payout")
async def allocate_payout(data: dict[str, Any]):
    """Allocate a payout across investment strategies."""
    amount = data.get("amount", 0.0)
    source = data.get("source", "")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    manager = get_investment_manager()
    result = manager.allocation.allocate_payout(amount, source)
    return {"success": True, "allocation": result}


@router.get("/metrics")
async def investment_metrics():
    """Get consolidated investment metrics."""
    manager = get_investment_manager()
    return {
        "success": True,
        "metrics": manager.metrics.consolidated_metrics(),
        "pnl_chart": manager.metrics.pnl_chart_data(days=30),
    }


@router.get("/events")
async def investment_events(limit: int = Query(50, ge=1, le=500)):
    """Get investment event history (allocations, deployments, trades)."""
    manager = get_investment_manager()
    return {
        "success": True,
        "events": manager.allocation.get_event_history(limit=limit),
    }


@router.post("/pause")
async def pause_investments():
    """Globally pause all investment strategies."""
    manager = get_investment_manager()
    manager.pause_all()
    return {"success": True, "paused": True}


@router.post("/resume")
async def resume_investments():
    """Resume all paused investment strategies."""
    manager = get_investment_manager()
    manager.resume_all()
    return {"success": True, "paused": False}


@router.post("/config")
async def update_investment_config(data: dict[str, Any]):
    """Update investment manager configuration."""
    manager = get_investment_manager()
    manager.update_config(**data)
    return {
        "success": True,
        "config": {
            "drawdown_protection": manager.drawdown_protection,
            "max_high_risk_pct": manager.allocation.config.max_high_risk_pct,
            "pause_on_drawdown_pct": 15.0,
        },
    }


@router.post("/max-revenue")
async def activate_max_revenue():
    """Activate max revenue mode with risk-managed deployment."""
    manager = get_investment_manager()
    result = manager.activate_max_revenue_mode()
    return {"success": result.get("success", False), "result": result}


@router.get("/ccxt/info")
async def ccxt_exchange_info(exchange: str = Query("binance")):
    """Get CCXT exchange info without connecting."""
    from core.investment.adapters.ccxt_adapter import CCXTAdapter

    adapter = CCXTAdapter(exchange_id=exchange)
    info = await adapter.get_exchange_info()
    return {"success": "error" not in info, "exchange": exchange, "info": info}


@router.post("/ccxt/connect")
async def ccxt_connect(data: dict[str, Any]):
    """Connect to a CCXT exchange."""
    exchange = data.get("exchange", "binance")
    api_key = data.get("api_key", "")
    api_secret = data.get("api_secret", "")

    from core.investment.adapters.ccxt_adapter import CCXTAdapter

    adapter = CCXTAdapter(exchange_id=exchange, config={"api_key": api_key, "api_secret": api_secret})
    connected = await adapter.connect()
    return {"success": connected, "exchange": exchange, "connected": connected}


@router.get("/ccxt/balance")
async def ccxt_balance(exchange: str = Query("binance")):
    """Get balance from a CCXT exchange (requires prior connect)."""
    from core.investment.adapters.ccxt_adapter import CCXTAdapter

    adapter = CCXTAdapter(exchange_id=exchange)
    if not adapter.is_connected:
        return {"success": False, "error": "Not connected. Use POST /api/investment/ccxt/connect first"}
    balance = await adapter.get_balance()
    return {"success": "error" not in balance, "exchange": exchange, "balance": balance}


@router.get("/ccxt/ticker")
async def ccxt_ticker(symbol: str = Query("BTC/USDT"), exchange: str = Query("binance")):
    """Get ticker from a CCXT exchange."""
    from core.investment.adapters.ccxt_adapter import CCXTAdapter

    adapter = CCXTAdapter(exchange_id=exchange)
    if not adapter.is_connected:
        return {"success": False, "error": "Not connected"}
    ticker = await adapter.get_ticker(symbol)
    return {"success": "error" not in ticker, "symbol": symbol, "ticker": ticker}


# ── Backtest ──


class BacktestRequest(BaseModel):
    symbol: str = "BTC-USD"
    short_ma: int = 20
    long_ma: int = 50
    start_date: date | None = None
    end_date: date | None = None
    initial_capital: float = 10_000.0


class BacktestTrade(BaseModel):
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    side: str
    pnl: float
    pnl_pct: float
    bars_held: int


class BacktestResult(BaseModel):
    symbol: str
    total_return_pct: float
    total_pnl: float
    sharpe: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    trades: list[BacktestTrade]
    data_source: str


@router.post("/backtest", response_model=dict)
async def run_backtest(req: BacktestRequest) -> dict:
    """Simple SMA crossover backtest using Yahoo Finance or simulated data."""
    end = req.end_date or date.today()
    start = req.start_date or date(end.year - 2, end.month, 1)
    prices: list[float] = []
    source = "simulated"

    try:
        import yfinance as yf

        ticker = yf.Ticker(req.symbol)
        hist = ticker.history(start=start.isoformat(), end=end.isoformat())
        if not hist.empty:
            prices = hist["Close"].tolist()
            source = "yfinance"
    except ImportError:
        logger.info("yfinance not installed, using simulated data for backtest")

    if not prices:
        import random

        random.seed(42)
        base = 100.0 if "USD" not in req.symbol else 50000.0
        days = (end - start).days or 365
        for _ in range(days):
            drift = 0.0003
            noise = random.gauss(0, 0.015)
            base = base * (1.0 + drift + noise)
            prices.append(round(max(base, 1.0), 2))

    if len(prices) < req.long_ma + 1:
        return {"success": False, "error": f"Not enough data: {len(prices)} bars, need {req.long_ma + 1}"}

    short_ma = req.short_ma
    long_ma = req.long_ma
    sma_short: list[float | None] = [None] * (short_ma - 1)
    sma_long: list[float | None] = [None] * (long_ma - 1)

    for i in range(short_ma - 1, len(prices)):
        sma_short.append(sum(prices[i - short_ma + 1 : i + 1]) / short_ma)
    for i in range(long_ma - 1, len(prices)):
        sma_long.append(sum(prices[i - long_ma + 1 : i + 1]) / long_ma)

    capital = req.initial_capital
    position = 0.0
    trades: list[BacktestTrade] = []
    entry_price = 0.0
    entry_date_str = ""
    side = ""

    for i in range(long_ma, len(prices)):
        prev_short = sma_short[i - 1]
        prev_long = sma_long[i - 1]
        curr_short = sma_short[i]
        curr_long = sma_long[i]
        if prev_short is None or prev_long is None or curr_short is None or curr_long is None:
            continue

        if prev_short <= prev_long and curr_short > curr_long and position == 0:
            position = capital / prices[i]
            entry_price = prices[i]
            entry_date_str = str(i)
            side = "long"
            capital = 0.0

        elif curr_short < curr_long and position > 0:
            exit_price = prices[i]
            pnl = position * (exit_price - entry_price)
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            trades.append(
                BacktestTrade(
                    entry_date=entry_date_str,
                    entry_price=round(entry_price, 2),
                    exit_date=str(i),
                    exit_price=round(exit_price, 2),
                    side=side,
                    pnl=round(pnl, 2),
                    pnl_pct=round(pnl_pct, 2),
                    bars_held=i - (int(entry_date_str) if entry_date_str.isdigit() else 0),
                )
            )
            capital = position * exit_price
            position = 0.0

    if position > 0:
        exit_price = prices[-1]
        pnl = position * (exit_price - entry_price)
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        trades.append(
            BacktestTrade(
                entry_date=entry_date_str,
                entry_price=round(entry_price, 2),
                exit_date=str(len(prices) - 1),
                exit_price=round(exit_price, 2),
                side=side,
                pnl=round(pnl, 2),
                pnl_pct=round(pnl_pct, 2),
                bars_held=len(prices) - 1 - (int(entry_date_str) if entry_date_str.isdigit() else 0),
            )
        )
        capital = position * exit_price

    final_value = capital if capital > 0 else req.initial_capital
    total_return = ((final_value - req.initial_capital) / req.initial_capital) * 100
    winning = sum(1 for t in trades if t.pnl > 0)
    losing = sum(1 for t in trades if t.pnl <= 0)
    win_rate = (winning / len(trades) * 100) if trades else 0.0

    returns = [t.pnl_pct for t in trades]
    avg_return = sum(returns) / len(returns) if returns else 0.0
    std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if len(returns) > 1 else 1.0
    sharpe = (avg_return / std_return * (252**0.5)) if std_return > 0 else 0.0

    max_dd = 0.0
    peak = prices[long_ma]
    for p in prices[long_ma:]:
        if p > peak:
            peak = p
        dd = (peak - p) / peak * 100
        if dd > max_dd:
            max_dd = dd

    result = BacktestResult(
        symbol=req.symbol,
        total_return_pct=round(total_return, 2),
        total_pnl=round(final_value - req.initial_capital, 2),
        sharpe=round(sharpe, 2),
        max_drawdown_pct=round(max_dd, 2),
        win_rate=round(win_rate, 1),
        total_trades=len(trades),
        winning_trades=winning,
        losing_trades=losing,
        trades=trades[-20:],
        data_source=source,
    )
    return {"success": True, "result": result.model_dump()}


class OptimizationRequest(BaseModel):
    symbols: list[str]
    expected_returns: list[float]
    covariance: list[list[float]]
    risk_free_rate: float = 0.05
    method: str = "max_sharpe"


@router.post("/optimize")
async def optimize_portfolio(req: OptimizationRequest) -> dict:
    """Portfolio optimization via Riskfolio-Lib (Mean-Variance)."""
    try:
        from apps.atlas.engines.optimizer import PortfolioOptimizer

        result = PortfolioOptimizer().optimize(
            symbols=req.symbols,
            expected_returns=req.expected_returns,
            covariance=req.covariance,
            risk_free_rate=req.risk_free_rate,
            method=req.method,
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.exception("Portfolio optimization failed")
        return {"success": False, "error": str(e)}


@router.get("/portfolio-dashboard")
async def portfolio_dashboard() -> dict:
    """Unified portfolio dashboard (ATLAS + Riskfolio).

    Aggregates positions, performance, risk, and allocation.
    Replaces Ghostfolio as native portfolio dashboard.
    """
    result: dict[str, Any] = {
        "positions": [],
        "performance": {},
        "risk": {},
        "allocation": {},
        "optimization": {"available": False},
    }
    try:
        from apps.atlas.engines.analytics import AnalyticsEngine
        from apps.atlas.engines.performance import PerformanceEngine
        from apps.atlas.engines.portfolio import PortfolioEngine
        from apps.atlas.engines.risk import RiskEngine

        engine = PortfolioEngine()
        portfolio = await engine.aggregate()

        result["positions"] = [
            {
                "symbol": p.symbol,
                "name": p.name,
                "asset_type": p.asset_type,
                "quantity": p.quantity,
                "avg_price": p.avg_price,
                "value": round(p.value, 2),
            }
            for p in portfolio.positions
        ]
        result["total_value"] = round(portfolio.total_value, 2)

        perf = await PerformanceEngine().calculate()
        result["performance"] = {
            "total_invested": round(perf.total_invested, 2),
            "current_value": round(perf.current_value, 2),
            "total_pnl": round(perf.total_pnl, 2),
            "total_pnl_percent": round(perf.total_pnl_percent, 2),
            "best_performer": perf.best_performer,
            "worst_performer": perf.worst_performer,
        }

        risk = await RiskEngine().assess(portfolio)
        result["risk"] = {
            "concentration": risk.top_concentration,
            "diversification": risk.diversification_score,
            "warnings": risk.warnings,
        }

        analytics = await AnalyticsEngine().analyze_allocation(portfolio)
        result["allocation"] = {
            "by_type": analytics.by_type,
            "top_symbols": analytics.top_symbols[:5],
        }

        symbols = [p.symbol for p in portfolio.positions if p.value > 0]
        if len(symbols) >= 2:
            from apps.atlas.engines.optimizer import PortfolioOptimizer

            n = len(symbols)
            er = [0.10] * n
            cov = [[0.05 if i == j else 0.01 for j in range(n)] for i in range(n)]
            opt = PortfolioOptimizer().optimize(symbols, er, cov)
            result["optimization"] = {
                "available": True,
                "weights": opt.weights,
                "sharpe": opt.sharpe_ratio,
                "method": opt.method,
            }

        return {"success": True, "dashboard": result}
    except Exception as e:
        logger.exception("Portfolio dashboard failed")
        return {"success": False, "error": str(e), "dashboard": result}


def register_investment_capabilities() -> None:
    try:
        from core.capabilities.registry import get_capability_registry

        reg = get_capability_registry()
        reg.register("investment_status", "investment", {}, "Get investment system status")
        reg.register("deploy_capital", "investment", {}, "Deploy capital to a strategy")
        reg.register("investment_metrics", "investment", {}, "Get investment performance metrics")
        reg.register("ccxt_trading", "investment", {"exchanges": "100+"}, "Trade on 100+ exchanges via CCXT")
        reg.register("high_risk_exposure", "investment", {}, "Check high-risk allocation limits")
        reg.register("allocate_payout", "investment", {}, "Allocate a payout across strategies")
        reg.register("portfolio_optimize", "investment", {}, "Run Riskfolio-Lib portfolio optimization (Mean-Variance)")
        reg.register("portfolio_dashboard", "investment", {}, "Unified portfolio dashboard (ATLAS + Riskfolio)")
    except Exception as e:
        logger.warning("Failed to register investment capabilities: %s", e)
