"""AEGIS — Offensive Security Platform (ORION Platform app).

Integrates the best open-source pentesting tools as interchangeable providers.
Recon → Scanning → Validation → Evidence → Reporting → Learning.
"""

from __future__ import annotations

from apps.aegis.api.routers import router as aegis_router
from apps.aegis.models import (
    AegisTarget,
    KnowHow,
    Payload,
    ScanReport,
    ScanResult,
    VulnFinding,
)
from core.interfaces.app import IAppPlugin

from .providers import PROVIDERS

manifest = IAppPlugin(
    id="aegis",
    name="AEGIS",
    version="5.0.0",
    description="Offensive Security Platform — recon, scanning, validation, evidence, reporting, and learning",
    icon="Shield",
    order=5,
    db_path="aegis.db",
    models=[AegisTarget, ScanResult, VulnFinding, ScanReport, Payload, KnowHow],
    routers=[aegis_router],
    router_prefix="aegis",
    scheduler_jobs=[
        {
            "job_id": "aegis_check_active_targets",
            "app_id": "aegis",
            "handler": "apps.aegis.scheduler.check_active_targets",
            "trigger": "interval",
            "seconds": 3600,
        },
        {
            "job_id": "aegis_cleanup_stale_scans",
            "app_id": "aegis",
            "handler": "apps.aegis.scheduler.cleanup_stale_scans",
            "trigger": "interval",
            "seconds": 86400,
        },
    ],
    agent_class=None,
    frontend_routes=[
        {"path": "/aegis/", "name": "aegis-dashboard", "component": "DashboardAegis"},
        {"path": "/aegis/settings", "name": "aegis-settings", "component": "SettingsAegis"},
    ],
    widgets=[
        {"id": "aegis-targets-active", "label": "Active Targets", "icon": "Crosshair", "query": "aegis/targets/active"},
        {"id": "aegis-findings-open", "label": "Open Findings", "icon": "Bug", "query": "aegis/findings/open"},
        {"id": "aegis-scans-today", "label": "Scans Today", "icon": "Activity", "query": "aegis/scans/today"},
    ],
    providers=PROVIDERS,
)
