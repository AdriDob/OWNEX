"""CATEYE — Bug Bounty Intelligence (wrapped as ORION Platform app)."""

from __future__ import annotations

from core.interfaces.app import IAppPlugin

manifest = IAppPlugin(
    id="cateye",
    name="CATEYE",
    version="3.0.0",
    description="Bug Bounty Intelligence System — automated hunting, validation, and reporting",
    icon="Bug",
    order=1,
    # Database is managed by existing database/db.py — no separate registration
    db_path="",
    # Routers are auto-discovered from api/routers/ by the existing api/main.py
    # The bridge router (api/routers/orion_bridge.py) provides the /api/core/apps endpoint
    router_prefix="cateye",
    # Scheduler jobs are defined in the existing api/scheduler.py
    scheduler_jobs=[],
    # Agent will be registered by core/ai/runtime.py
    agent_class=None,
    # Frontend routes are namespaced under /cateye/* in the shell
    frontend_routes=[
        {"path": "/cateye/", "name": "cateye-dashboard", "component": "Dashboard"},
        {"path": "/cateye/mission-control", "name": "cateye-mission-control", "component": "MissionControl"},
        {"path": "/cateye/findings", "name": "cateye-findings", "component": "Findings"},
        {"path": "/cateye/reports", "name": "cateye-reports", "component": "ReportCenter"},
        {"path": "/cateye/targets/:id", "name": "cateye-target-detail", "component": "TargetDetail"},
        {"path": "/cateye/settings", "name": "cateye-settings", "component": "Settings"},
    ],
    widgets=[
        {"id": "cateye-findings-count", "label": "Findings", "icon": "Bug", "query": "findings/count"},
        {"id": "cateye-active-targets", "label": "Active Targets", "icon": "Target", "query": "targets/count"},
        {"id": "cateye-bounties", "label": "Bounties Earned", "icon": "DollarSign", "query": "bounties/total"},
    ],
    providers=[],
)
