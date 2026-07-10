"""ODYSSEY API — FastAPI routers for gambling analytics."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apps.odyssey.providers.kelly import KellyProvider
from fastapi import APIRouter
from sqlalchemy import func

from apps.odyssey.models import Bankroll, Bet, Strategy
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.odyssey.api")
router = APIRouter(prefix="/api/odyssey", tags=["odyssey"])


# ── Bankroll ──

@router.get("/bankroll/total")
async def bankroll_total():
    db = get_db_manager().get_session("odyssey")
    try:
        total = db.query(func.sum(Bankroll.balance)).scalar() or 0.0
        return {"total": round(float(total), 2)}
    finally:
        db.close()


@router.get("/bankroll")
async def list_bankrolls():
    db = get_db_manager().get_session("odyssey")
    try:
        bankrolls = db.query(Bankroll).all()
        return [
            {
                "id": b.id,
                "name": b.name,
                "platform": b.platform,
                "balance": b.balance,
                "currency": b.currency,
                "risk_level": b.risk_level,
                "max_stake_percent": b.max_stake_percent,
            }
            for b in bankrolls
        ]
    finally:
        db.close()


# ── Bets ──

@router.get("/bets/active")
async def active_bets_count():
    db = get_db_manager().get_session("odyssey")
    try:
        count = db.query(Bet).filter(Bet.outcome == "pending").count()
        return {"count": count}
    finally:
        db.close()


@router.get("/bets")
async def list_bets(limit: int = 50, status: str = ""):
    db = get_db_manager().get_session("odyssey")
    try:
        q = db.query(Bet).order_by(Bet.placed_at.desc())
        if status:
            q = q.filter(Bet.outcome == status)
        bets = q.limit(limit).all()
        return [
            {
                "id": b.id,
                "event": b.event,
                "market": b.market,
                "platform": b.platform,
                "bet_type": b.bet_type,
                "odds": b.odds,
                "stake": b.stake,
                "outcome": b.outcome,
                "payout": b.payout,
                "roi": b.roi,
                "ev": b.ev,
                "clv": b.clv,
                "placed_at": b.placed_at.isoformat() if b.placed_at else None,
            }
            for b in bets
        ]
    finally:
        db.close()


# ── Analytics ──

@router.get("/analytics/roi")
async def roi():
    db = get_db_manager().get_session("odyssey")
    try:
        settled = db.query(Bet).filter(Bet.outcome.in_(["win", "loss"])).all()
        if not settled:
            return {"roi": 0.0, "total_staked": 0.0, "total_payout": 0.0}
        total_staked = sum(b.stake for b in settled)
        total_payout = sum(b.payout for b in settled)
        profit = total_payout - total_staked
        roi_pct = (profit / total_staked * 100) if total_staked else 0.0
        return {"roi": round(roi_pct, 2), "total_staked": round(total_staked, 2), "total_payout": round(total_payout, 2)}
    finally:
        db.close()


@router.get("/analytics/summary")
async def summary():
    db = get_db_manager().get_session("odyssey")
    try:
        total = db.query(Bet).count()
        wins = db.query(Bet).filter(Bet.outcome == "win").count()
        losses = db.query(Bet).filter(Bet.outcome == "loss").count()
        pushes = db.query(Bet).filter(Bet.outcome == "push").count()
        pending = db.query(Bet).filter(Bet.outcome == "pending").count()
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) else 0.0
        return {
            "total_bets": total,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "pending": pending,
            "win_rate": round(win_rate, 1),
        }
    finally:
        db.close()


@router.get("/analytics/performance")
async def performance():
    db = get_db_manager().get_session("odyssey")
    try:
        bets = db.query(Bet).filter(Bet.outcome.in_(["win", "loss"])).all()
        if not bets:
            return {"profit": 0.0, "avg_odds": 0.0, "avg_ev": 0.0, "avg_stake": 0.0, "best_streak": 0}
        total_staked = sum(b.stake for b in bets)
        total_payout = sum(b.payout for b in bets)
        profit = total_payout - total_staked
        avg_odds = sum(b.odds for b in bets) / len(bets) if bets else 0.0
        avg_ev = sum(b.ev for b in bets) / len(bets) if bets else 0.0
        avg_stake = total_staked / len(bets) if bets else 0.0

        # Best win streak
        streak = 0
        best_streak = 0
        for b in sorted(bets, key=lambda x: x.placed_at or datetime.min.replace(tzinfo=timezone.utc)):
            if b.outcome == "win":
                streak += 1
                best_streak = max(best_streak, streak)
            else:
                streak = 0

        return {
            "profit": round(profit, 2),
            "avg_odds": round(avg_odds, 2),
            "avg_ev": round(avg_ev, 4),
            "avg_stake": round(avg_stake, 2),
            "best_streak": best_streak,
        }
    finally:
        db.close()


# ── Strategies ──

@router.get("/strategies")
async def list_strategies():
    db = get_db_manager().get_session("odyssey")
    try:
        strategies = db.query(Strategy).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "kelly_fraction": s.kelly_fraction,
                "max_stake": s.max_stake,
                "min_odds": s.min_odds,
                "max_odds": s.max_odds,
                "min_ev": s.min_ev,
                "active": bool(s.active),
            }
            for s in strategies
        ]
    finally:
        db.close()


# ── Kelly Calculator ──

@router.post("/strategies/kelly")
async def kelly_calculate(odds: float, win_probability: float, bankroll: float, fraction: float = 0.25):
    kelly = KellyProvider()
    result = kelly.calculate(odds, win_probability, bankroll, fraction)
    return {
        "full_kelly": round(result["full_kelly"], 4),
        "fractional_kelly": round(result["fractional_kelly"], 4),
        "stake_amount": round(result["stake_amount"], 2),
        "ev": round(result["ev"], 4),
        "growth_rate": round(result["growth_rate"], 4),
    }


# ── Health ──

@router.get("/health")
async def odyssey_health():
    db = get_db_manager().get_session("odyssey")
    try:
        db.execute(Bankroll.__table__.select().limit(1))
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        db.close()
    return {"status": "ok", "db": db_ok, "timestamp": datetime.now(timezone.utc).isoformat()}
