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
