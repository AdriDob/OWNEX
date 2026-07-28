"""Widget Dashboard API — provides available widget definitions for the UI."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/core", tags=["widgets"])

# ── Widget registry ──────────────────────────────────────────────────

WIDGETS = [
    {
        "id": "opportunity-radar",
        "name": "Opportunity Radar",
        "description": "Real-time vulnerability opportunities ranked by EVH",
        "icon": "radar",
        "default_cols": 2,
        "default_rows": 2,
        "refresh_interval": 300,
    },
    {
        "id": "throughput-core",
        "name": "Throughput Core",
        "description": "Findings submitted, accepted, and pending per cycle",
        "icon": "activity",
        "default_cols": 1,
        "default_rows": 1,
        "refresh_interval": 600,
    },
    {
        "id": "agent-fleet",
        "name": "Agent Fleet",
        "description": "Status of autonomous agents and their current tasks",
        "icon": "cpu",
        "default_cols": 2,
        "default_rows": 1,
        "refresh_interval": 60,
    },
    {
        "id": "knowledge-feed",
        "name": "Knowledge Feed",
        "description": "Recent intelligence, research, and system events",
        "icon": "book-open",
        "default_cols": 1,
        "default_rows": 2,
        "refresh_interval": 120,
    },
    {
        "id": "next-best-action",
        "name": "Next Best Action",
        "description": "AI-recommended high-impact actions based on current state",
        "icon": "target",
        "default_cols": 1,
        "default_rows": 1,
        "refresh_interval": 300,
    },
    {
        "id": "system-health",
        "name": "System Health",
        "description": "Watchdog, pipeline, scheduler, and service status",
        "icon": "heart",
        "default_cols": 1,
        "default_rows": 1,
        "refresh_interval": 60,
    },
]


@router.get("/widgets")
async def list_widgets():
    """Return available widget definitions for the dashboard UI."""
    return {"widgets": WIDGETS, "total": len(WIDGETS)}
