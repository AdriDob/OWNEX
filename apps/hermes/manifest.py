"""Hermes — Automation Agent (ORION Platform app manifest)."""

from __future__ import annotations

from core.interfaces.app import IAppPlugin

manifest = IAppPlugin(
    id="hermes",
    name="Hermes",
    version="0.2.0",
    description="Automation + Desktop Agent — system monitoring, package management, process control, services, files. 13 commands, tool-calling architecture.",
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
        {"id": "hermes-status", "label": "Hermes Status", "icon": "Bot", "query": "hermes/status"},
        {"id": "hermes-last-backup", "label": "Last Backup", "icon": "Shield", "query": "hermes/backup/last"},
        {"id": "hermes-actions-today", "label": "Actions Today", "icon": "Activity", "query": "hermes/actions/today"},
    ],
    providers=[],
)
