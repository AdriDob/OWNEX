"""Revenue Multiplier API — MAX REVENUE MODE, tools, metrics, events."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("orion.revenue.api")
router = APIRouter(prefix="/api/revenue-multiplier", tags=["revenue_multiplier"])


@router.get("/status")
async def revenue_status():
    """Get current orchestrator status."""
    try:
        from core.revenue_multiplier import get_revenue_multiplier

        rm = get_revenue_multiplier()
        return {"success": True, "status": rm.get_status()}
    except Exception as e:
        logger.exception("Failed to get revenue multiplier status")
        return {"success": False, "error": str(e)}


@router.post("/activate")
async def activate_max_revenue(data: dict[str, Any] | None = None):
    """Activate MAX REVENUE MODE — runs bounty pipeline and/or crypto trading."""
    try:
        from core.revenue_multiplier import (
            ExecutionMode,
            RevenueMultiplierConfig,
            RevenueMultiplierOrchestrator,
            get_revenue_multiplier,
        )

        if data and "mode" in data:
            mode = ExecutionMode(data["mode"])
            cfg = RevenueMultiplierConfig(mode=mode)
            rm = RevenueMultiplierOrchestrator(cfg)
        else:
            rm = get_revenue_multiplier()

        result = rm.activate_max_revenue_mode()
        return {"success": True, "result": result}
    except Exception as e:
        logger.exception("Failed to activate MAX REVENUE MODE")
        return {"success": False, "error": str(e)}


@router.get("/tools")
async def list_tools(category: str | None = None):
    """List all registered tools with availability status."""
    try:
        from core.revenue_multiplier import get_tool_registry

        reg = get_tool_registry()
        if category:
            from core.revenue_multiplier.models import ToolCategory

            cat = ToolCategory(category)
            tools = reg.list_by_category(cat)
        else:
            tools = reg.get_available() + reg.get_unavailable()

        return {
            "success": True,
            "total": reg.count,
            "available": len(reg.get_available()),
            "unavailable": len(reg.get_unavailable()),
            "tools": [
                {
                    "name": t.name,
                    "category": t.category.value,
                    "description": t.description,
                    "available": shutil_which(t.binary) if t.binary else False,
                    "binary": t.binary,
                }
                for t in tools
            ],
        }
    except Exception as e:
        logger.exception("Failed to list tools")
        return {"success": False, "error": str(e)}


def shutil_which(binary: str) -> bool:
    import shutil

    return shutil.which(binary) is not None


@router.get("/metrics")
async def revenue_metrics():
    """Get combined bounty + trading metrics."""
    try:
        from core.revenue_multiplier import get_revenue_multiplier

        rm = get_revenue_multiplier()
        return {"success": True, "metrics": rm.metrics.to_dict()}
    except Exception as e:
        logger.exception("Failed to get metrics")
        return {"success": False, "error": str(e)}


@router.get("/events")
async def recent_events(limit: int = 20):
    """Get recent revenue events."""
    try:
        from core.revenue_multiplier import get_revenue_multiplier

        rm = get_revenue_multiplier()
        events = rm.publisher.get_recent_events(limit=limit)
        return {
            "success": True,
            "events": [
                {
                    "source": e.source,
                    "category": e.category.value,
                    "amount": str(e.amount),
                    "description": e.description[:200],
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in events
            ],
            "total": len(events),
        }
    except Exception as e:
        logger.exception("Failed to get events")
        return {"success": False, "error": str(e)}


@router.get("/config")
async def get_config():
    """Get current revenue multiplier configuration."""
    try:
        from core.revenue_multiplier import get_revenue_multiplier

        rm = get_revenue_multiplier()
        return {"success": True, "config": rm.get_status().get("config", {})}
    except Exception as e:
        logger.exception("Failed to get config")
        return {"success": False, "error": str(e)}


@router.post("/config")
async def update_config(data: dict[str, Any]):
    """Update revenue multiplier configuration for current session."""
    try:
        from core.revenue_multiplier import (
            ExecutionMode,
            get_revenue_multiplier,
        )

        rm = get_revenue_multiplier()
        if "mode" in data:
            rm._config.mode = ExecutionMode(data["mode"])
        if "auto_report_enabled" in data:
            rm._config.auto_report_enabled = bool(data["auto_report_enabled"])
        if "auto_trade_enabled" in data:
            rm._config.auto_trade_enabled = bool(data["auto_trade_enabled"])
        if "max_daily_bounty_targets" in data:
            rm._config.max_daily_bounty_targets = int(data["max_daily_bounty_targets"])
        if "max_concurrent_trades" in data:
            rm._config.max_concurrent_trades = int(data["max_concurrent_trades"])
        if "min_confidence_for_report" in data:
            rm._config.min_confidence_for_report = float(data["min_confidence_for_report"])
        if "trading_pair_whitelist" in data:
            rm._config.trading_pair_whitelist = list(data["trading_pair_whitelist"])

        return {"success": True, "config": rm.get_status().get("config", {})}
    except Exception as e:
        logger.exception("Failed to update config")
        return {"success": False, "error": str(e)}


@router.get("/report")
async def generate_report():
    """Generate a revenue report from accumulated events."""
    try:
        from core.revenue_multiplier import get_revenue_multiplier

        rm = get_revenue_multiplier()
        events = rm.publisher.get_recent_events()
        metrics = rm.metrics.to_dict()
        report = rm.publisher.generate_report(
            findings_count=metrics.get("bounty", {}).get("findings_total", 0),
            trades_count=metrics.get("trading", {}).get("total_trades", 0),
        )
        return {
            "success": True,
            "report": {
                "daily_revenue": str(report.daily_revenue),
                "weekly_revenue": str(report.weekly_revenue),
                "monthly_revenue": str(report.monthly_revenue),
                "total_revenue": str(report.total_revenue),
                "bounty_revenue": str(report.bounty_revenue),
                "trading_revenue": str(report.trading_revenue),
                "total_findings": report.total_findings,
                "total_trades": report.total_trades,
                "win_rate": report.win_rate,
                "estimated_yearly": str(report.estimated_yearly),
                "generated_at": report.generated_at.isoformat(),
            },
            "events_tracked": len(events),
        }
    except Exception as e:
        logger.exception("Failed to generate report")
        return {"success": False, "error": str(e)}
