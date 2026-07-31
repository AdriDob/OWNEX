"""MERLIN — Automation & Operations Agent (ORION Platform app manifest)."""

from __future__ import annotations

from core.interfaces.app import IAppPlugin

manifest = IAppPlugin(
    id="hermes",
    name="MERLIN",
    version="7.0.0",
    description="MERLIN — Automation & Operations Agent: system monitoring, package management, process control, services, files. EventBus integration, permission system, security layer, 14 commands, tool-calling architecture.",
    icon="Bot",
    order=4,
    db_path="",
    models=[],
    routers=[],
    router_prefix="hermes",
    scheduler_jobs=[
        {
            "job_id": "hermes_health_check",
            "app_id": "hermes",
            "handler": "apps.hermes.engine.run_health_check",
            "trigger": "interval",
            "seconds": 3600,
        },
    ],
    agent_class=None,
    frontend_routes=[],
    widgets=[
        {"id": "merlin-status", "label": "MERLIN Status", "icon": "Bot", "query": "hermes/status"},
        {"id": "merlin-last-backup", "label": "Last Backup", "icon": "Shield", "query": "hermes/backup/last"},
        {"id": "merlin-actions-today", "label": "Actions Today", "icon": "Activity", "query": "hermes/actions/today"},
    ],
    providers=[],
)
