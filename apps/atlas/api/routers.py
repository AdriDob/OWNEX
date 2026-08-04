"""ATLAS API — FastAPI routers for investment management."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter

from apps.atlas.engines.analytics import AnalyticsEngine
from apps.atlas.engines.performance import PerformanceEngine
from apps.atlas.engines.portfolio import PortfolioEngine
from apps.atlas.engines.risk import RiskEngine
from apps.atlas.engines.strategy import StrategyEngine
from apps.atlas.models import Asset, Transaction, Wallet
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.atlas.api")
router = APIRouter(prefix="/api/atlas", tags=["atlas"])


# ── Portfolio ──


@router.get("/portfolio/value")
async def portfolio_value():
    engine = PortfolioEngine()
    portfolio = await engine.aggregate()
    if portfolio is None:
        return {"value": 0.0, "positions": 0}
    return {"value": round(portfolio.total_value, 2), "positions": len(portfolio.positions)}


@router.get("/portfolio")
async def get_portfolio():
    engine = PortfolioEngine()
    portfolio = await engine.aggregate()
    if portfolio is None:
        return {"total_value": 0.0, "positions": [], "cash": 0.0}
    return {
        "total_value": round(portfolio.total_value, 2),
        "cash": round(portfolio.cash, 2),
        "positions": [
            {
                "symbol": p.symbol,
                "name": p.name,
                "asset_type": p.asset_type,
                "quantity": p.quantity,
                "avg_price": p.avg_price,
                "current_price": p.current_price,
                "value": round(p.value, 2),
                "pnl_percent": round(p.pnl_percent, 2) if p.pnl_percent else None,
            }
            for p in portfolio.positions
        ],
    }


# ── Assets ──


@router.get("/assets")
async def list_assets():
    db = get_db_manager().get_session("atlas")
    try:
        assets = db.query(Asset).all()
        return [
            {
                "id": a.id,
                "symbol": a.symbol,
                "name": a.name,
                "asset_type": a.asset_type,
                "quantity": a.quantity,
                "avg_price": a.avg_price,
                "value": round(a.quantity * a.avg_price, 2),
            }
            for a in assets
        ]
    finally:
        db.close()


@router.get("/assets/count")
async def asset_count():
    db = get_db_manager().get_session("atlas")
    try:
        count = db.query(Asset).count()
        return {"count": count}
    finally:
        db.close()


# ── Transactions ──


@router.get("/transactions")
async def list_transactions(limit: int = 50):
    db = get_db_manager().get_session("atlas")
    try:
        txs = db.query(Transaction).order_by(Transaction.executed_at.desc()).limit(limit).all()
        return [
            {
                "id": t.id,
                "symbol": None,  # TODO: join with asset
                "tx_type": t.tx_type,
                "quantity": t.quantity,
                "price": t.price,
                "fees": t.fees,
                "total": t.total,
                "executed_at": t.executed_at.isoformat() if t.executed_at else None,
            }
            for t in txs
        ]
    finally:
        db.close()


# ── Performance ──


@router.get("/performance/daily")
async def daily_performance():
    engine = PerformanceEngine()
    metrics = await engine.calculate()
    return {"pnl": metrics.daily_pnl, "total_pnl_percent": metrics.total_pnl_percent}


@router.get("/performance")
async def performance():
    engine = PerformanceEngine()
    metrics = await engine.calculate()
    return {
        "total_invested": metrics.total_invested,
        "current_value": metrics.current_value,
        "total_pnl": metrics.total_pnl,
        "total_pnl_percent": metrics.total_pnl_percent,
        "best_performer": metrics.best_performer,
        "worst_performer": metrics.worst_performer,
    }


# ── Risk ──


@router.get("/risk")
async def risk_assessment():
    engine = PortfolioEngine()
    portfolio = await engine.aggregate()
    risk_engine = RiskEngine()
    profile = await risk_engine.assess(portfolio)
    return {
        "total_value": profile.total_value,
        "cash_percent": round(profile.cash_percent, 1),
        "top_concentration": round(profile.top_concentration, 1),
        "crypto_exposure": round(profile.crypto_exposure, 1),
        "stock_exposure": round(profile.stock_exposure, 1),
        "diversification_score": profile.diversification_score,
        "warnings": profile.warnings,
    }


# ── Analytics ──


@router.get("/analytics/allocation")
async def allocation():
    engine = PortfolioEngine()
    portfolio = await engine.aggregate()
    analytics = AnalyticsEngine()
    alloc = await analytics.analyze_allocation(portfolio)
    return {
        "by_type": alloc.by_type,
        "by_symbol": alloc.by_symbol,
        "num_assets": alloc.num_assets,
        "top_symbols": alloc.top_symbols,
    }


# ── Strategy / Rebalance ──


@router.get("/strategy/rebalance")
async def rebalance():
    engine = PortfolioEngine()
    portfolio = await engine.aggregate()
    strategy = StrategyEngine()
    rec = await strategy.recommend_rebalance(portfolio)
    return {
        "suggestions": [
            {
                "symbol": s.symbol,
                "current_percent": s.current_percent,
                "target_percent": s.target_percent,
                "action": s.action,
                "delta_value": s.delta_value,
            }
            for s in rec.suggestions
        ],
        "total_trades": rec.total_trades,
        "estimated_cost": rec.estimated_cost,
    }


# ── Wallets ──


@router.get("/wallets")
async def list_wallets():
    db = get_db_manager().get_session("atlas")
    try:
        wallets = db.query(Wallet).all()
        return [
            {
                "id": w.id,
                "name": w.name,
                "wallet_type": w.wallet_type,
                "balance": w.balance,
                "currency": w.currency,
                "provider": w.provider,
            }
            for w in wallets
        ]
    finally:
        db.close()


# ── Health ──


@router.get("/health")
async def atlas_health():
    db = get_db_manager().get_session("atlas")
    try:
        db.execute(Wallet.__table__.select().limit(1))
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        db.close()
    return {"status": "ok", "db": db_ok, "timestamp": datetime.now(UTC).isoformat()}
