"""API endpoints for DeFi Yield Tracker."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core.defi import DefiPosition
from core.defi.strategy import CompoundStrategy
from core.defi.yield_tracker import get_defi_tracker

router = APIRouter(prefix="/api/defi", tags=["defi"])

_tracker = get_defi_tracker()


@router.get("/positions")
def list_positions():
    """List all tracked DeFi positions."""
    positions = _tracker.list_positions()
    return {"positions": [p.to_dict() for p in positions], "total": len(positions)}


@router.post("/positions")
def add_position(body: dict[str, Any]):
    """Add a DeFi position to track."""
    position = DefiPosition(
        protocol=body["protocol"],
        chain=body.get("chain", "ethereum"),
        asset=body.get("asset", "USDC"),
        amount=float(body.get("amount", 0)),
        usd_value=float(body.get("usd_value", 0)),
        apy=float(body.get("apy", 0)),
        category=body.get("category", "yield"),
        pool_name=body.get("pool_name", ""),
        tokens=body.get("tokens", []),
        link=body.get("link", ""),
        notes=body.get("notes", ""),
    )
    _tracker.add_position(position)
    return {"status": "added", "position": position.to_dict()}


@router.delete("/positions/{protocol}/{asset}")
def remove_position(protocol: str, asset: str):
    """Remove a DeFi position."""
    removed = _tracker.remove_position(protocol, asset)
    if not removed:
        raise HTTPException(404, "Position not found")
    return {"status": "removed"}


@router.post("/positions/refresh-apy")
def refresh_apy():
    """Refresh APY from DefiLlama for all tracked positions."""
    apys = _tracker.refresh_apy_from_defillama()
    return {"status": "refreshed", "protocols_updated": len(apys), "apys": apys}


@router.get("/snapshot")
def get_snapshot():
    """Get current yield snapshot."""
    snap = _tracker.snapshot()
    return snap.to_dict()


@router.post("/publish-events")
def publish_events():
    """Publish yield events to EventBus."""
    events = _tracker.publish_yield_events()
    return {"published": len(events), "events": events}


@router.get("/summary")
def get_summary():
    """Get DeFi yield summary."""
    return _tracker.summary()


@router.post("/strategy/project")
def project_strategy(body: dict[str, Any]):
    """Project a compound yield strategy over time.

    Default: the $3K → 5 protocols → $1K/month → retire strategy.
    """
    strategy = CompoundStrategy(
        initial_capital=float(body.get("initial_capital", 3000.0)),
        protocols=body.get("protocols", []),
        apy_per_protocol=body.get("apy_per_protocol", []),
        reinvest_rate=float(body.get("reinvest_rate", 1.0)),
        monthly_yield_target=float(body.get("monthly_yield_target", 1000.0)),
    )
    months = int(body.get("months", 60))
    monthly_contribution = float(body.get("monthly_contribution", 0.0))

    projection = strategy.project(months=months, monthly_contribution=monthly_contribution)
    return projection.to_dict()


@router.get("/strategy/tweet-default")
def tweet_default_strategy():
    """The exact tweet strategy: $3K → 5 protocols → compound → retire."""
    projection = CompoundStrategy.tweet_default()
    return projection.to_dict()
