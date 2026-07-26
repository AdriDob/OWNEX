"""CATEYE — Bug Bounty Intelligence (legacy base app for ORION Platform).

NOTE: CATEYE is the ORIGINAL monolithic system. Unlike ATLAS/ODYSSEY,
its routers (~55) are mounted directly in api/main.py because each
has its own prefix (e.g., /api/targets, /api/findings). The AppRegistry
can only mount all routers under a single /api/cateye/ prefix, which
would conflict with the manual mounts in api/main.py.

Scheduler jobs are managed by the legacy ScanScheduler in api/scheduler.py,
which is started in api/main.py lifespan and runs pipeline stages
(discover, recon, hypothesis, validate, report, ai_bounty) independently
from the ORION CoreScheduler. The jobs below register CATEYE's pipeline
stages with CoreScheduler for ORION app-level visibility.

Frontend routes are namespaced under /cateye/* in the shell.

See AGENTS.md → CATEYE.md → api/main.py for the full architecture.
"""

from __future__ import annotations

from core.interfaces.app import IAppPlugin

# CATEYE pipeline stages — registered with CoreScheduler for visibility
_CATEYE_JOBS = [
    {"job_id": "cateye_discover", "app_id": "cateye",
     "handler": "api.scheduler.ScanScheduler._stage_discover",
     "trigger": "interval", "seconds": 3600},
    {"job_id": "cateye_recon", "app_id": "cateye",
     "handler": "api.scheduler.ScanScheduler._stage_recon",
     "trigger": "interval", "seconds": 1800},
    {"job_id": "cateye_hypothesis", "app_id": "cateye",
     "handler": "api.scheduler.ScanScheduler._stage_hypothesis",
     "trigger": "interval", "seconds": 900},
    {"job_id": "cateye_auto_validate", "app_id": "cateye",
     "handler": "api.scheduler.ScanScheduler._stage_auto_validate",
     "trigger": "interval", "seconds": 1800},
    {"job_id": "cateye_promote", "app_id": "cateye",
     "handler": "api.scheduler.ScanScheduler._stage_promote",
     "trigger": "interval", "seconds": 600},
    {"job_id": "cateye_validate", "app_id": "cateye",
     "handler": "api.scheduler.ScanScheduler._stage_validate",
     "trigger": "interval", "seconds": 7200},
    {"job_id": "cateye_report", "app_id": "cateye",
     "handler": "api.scheduler.ScanScheduler._stage_report",
     "trigger": "interval", "seconds": 3600},
    {"job_id": "cateye_ai_bounty", "app_id": "cateye",
     "handler": "api.scheduler.ScanScheduler._stage_ai_bounty",
     "trigger": "interval", "seconds": 7200},
]

manifest = IAppPlugin(
    id="cateye",
    name="CATEYE",
    version="3.0.0",
    description="Bug Bounty Intelligence System — automated hunting, validation, and reporting",
    icon="Bug",
    order=1,
    # Database is managed by database/db.py — not through AppRegistry
    db_path="",
    # Routers mounted directly in api/main.py (prefix per module, not managed by AppRegistry)
    router_prefix="",
    # Scheduler jobs for ORION CoreScheduler visibility
    scheduler_jobs=_CATEYE_JOBS,
    # Agent registration handled by core/ai/runtime.py
    agent_class=None,
    # Frontend routes under /cateye/* in the shell
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
