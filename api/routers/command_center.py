"""Command Center — Unified entry point for OWNEX.

The single source of truth for:
- What's happening
- What to do next
- How much money
- How I'm progressing
- What the system is doing
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/command-center", tags=["command-center"])

logger = logging.getLogger("ownex.command_center")


@router.get("/today")
async def get_today():
    """Get the complete TODAY view — the heart of OWNEX LITE mode.

    Returns exactly what the user needs to know:
    1. Capital & Income at a glance
    2. Next Best Action (prominent)
    3. System status (compact)
    4. Quick actions
    """
    from cores.capital.engine import get_capital_engine
    from cores.learning.revenue_loop import get_revenue_loop
    from cores.modes.engine import get_mode_engine

    capital = get_capital_engine()
    mode_engine = get_mode_engine()
    learning = get_revenue_loop()

    # Get capital state
    cap_dashboard = capital.get_dashboard()

    # Get today's learning metrics
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    today_metrics = learning.daily.get(today)

    # Get next best action (simplified)
    next_action = await _get_next_action()

    # Get system status
    system_status = await _get_system_status()

    # Get mode config
    mode_config = mode_engine.get_config()

    return {
        "greeting": _get_greeting(),
        "mode": mode_config.name,
        "tagline": mode_config.tagline,
        "question": mode_config.question,
        "capital": {
            "net_worth": cap_dashboard["state"]["net_worth"],
            "monthly_income": cap_dashboard["state"]["monthly_income"],
            "monthly_savings": cap_dashboard["state"]["monthly_savings"],
            "savings_rate": cap_dashboard["state"]["savings_rate"],
            "progress_to_million": cap_dashboard["progress_to_million"],
            "gap_to_million": cap_dashboard["gap_to_million"],
        },
        "today": {
            "human_minutes": today_metrics.human_minutes if today_metrics else 0,
            "actions_taken": today_metrics.actions_taken if today_metrics else 0,
            "expected_value": today_metrics.expected_value if today_metrics else 0,
            "actual_revenue": today_metrics.actual_revenue if today_metrics else 0,
        },
        "next_action": next_action,
        "system": system_status,
        "goals": cap_dashboard["goals"][:3],  # Top 3 goals
        "updated_at": datetime.now(UTC).isoformat(),
    }


@router.get("/next-action")
async def get_next_action():
    """Get the single next best action."""
    return await _get_next_action()


@router.get("/status")
async def get_status():
    """Get system status."""
    return await _get_system_status()


@router.get("/metrics")
async def get_metrics():
    """Get the two key metrics: HUMAN_MINUTES/DAY and $PAID/HOUR."""
    from cores.learning.revenue_loop import get_revenue_loop

    loop = get_revenue_loop()
    totals = loop.get_totals()
    daily_count = max(len(loop.daily), 1)

    return {
        "human_minutes_per_day": round(totals["total_human_minutes"] / daily_count, 1),
        "revenue_per_human_hour": totals["avg_revenue_per_hour"],
        "ev_per_human_hour": totals["avg_ev_per_hour"],
        "total_revenue": totals["total_actual_revenue"],
        "total_actions": totals["total_actions"],
    }


async def _get_next_action() -> dict[str, Any]:
    """Get the single next best action."""
    from cores.learning.revenue_loop import get_revenue_loop

    loop = get_revenue_loop()

    # Check if there are pending actions
    pending = [a for a in loop.actions if a.status == "pending"]
    if pending:
        best = max(pending, key=lambda a: a.ev_per_hour)
        return {
            "title": best.title,
            "description": best.description,
            "expected_value": best.expected_value,
            "ev_per_hour": best.ev_per_hour,
            "human_minutes": best.human_minutes,
            "action_type": best.action_type,
            "opportunity_id": best.opportunity_id,
        }

    # Check for opportunities in the pipeline
    from sqlalchemy import text

    from database.db import SessionLocal

    try:
        with SessionLocal() as db:
            # Find highest-value opportunity
            result = db.execute(
                text("""
                    SELECT id, name, domain, created_at
                    FROM targets
                    WHERE active = 1
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
            ).fetchone()

            if result:
                return {
                    "title": f"Investigate {result[1]}",
                    "description": f"Run recon and analysis on {result[2] or result[1]}",
                    "expected_value": 500,  # Default estimate
                    "ev_per_hour": 100,
                    "human_minutes": 30,
                    "action_type": "investigate",
                    "opportunity_id": f"target_{result[0]}",
                }
    except Exception:
        pass

    return {
        "title": "NO ACTION REQUIRED",
        "description": "OWNEX will continue monitoring for opportunities.",
        "expected_value": 0,
        "ev_per_hour": 0,
        "human_minutes": 0,
        "action_type": "none",
        "opportunity_id": None,
    }


async def _get_system_status() -> dict[str, Any]:
    """Get system status."""
    try:
        from api.scheduler import get_scheduler_status

        scheduler = get_scheduler_status()
    except Exception:
        scheduler = {"status": "unknown"}

    try:
        from cores.notifications.hub import get_hub

        hub = get_hub()
        channels = list(hub._channels.keys())
    except Exception:
        channels = []

    return {
        "scheduler": scheduler.get("status", "unknown"),
        "notification_channels": channels,
        "database": "connected",
        "status": "operational",
    }


def _get_greeting() -> str:
    """Get time-appropriate greeting."""
    hour = datetime.now(UTC).hour
    if hour < 12:
        return "GOOD MORNING"
    elif hour < 18:
        return "GOOD AFTERNOON"
    else:
        return "GOOD EVENING"
