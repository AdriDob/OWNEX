"""PULSE App Manifest — AI Work & Microtask Platforms."""

from __future__ import annotations

from fastapi import APIRouter

from core.interfaces.app import IAppPlugin
from core.scheduler.jobs import get_pulse_jobs

# Adapter provider strings for the adapter registry
PULSE_ADAPTERS = [
    "core.opportunity.adapters.pulse.outlier:OutlierAdapter",
    "core.opportunity.adapters.pulse.mindrift:MindriftAdapter",
    "core.opportunity.adapters.pulse.dataannotation:DataAnnotationAdapter",
    "core.opportunity.adapters.pulse.remotasks:RemotasksAdapter",
    "core.opportunity.adapters.pulse.freelancer_micro:FreelancerMicrotaskAdapter",
    "core.opportunity.adapters.pulse.linkedin_easyapply:LinkedInEasyApplyAdapter",
    "core.opportunity.adapters.pulse.opyre_microtask:OpyreMicrotaskAdapter",
]


# Router will be auto-discovered from api/routers/pulse.py if it exists
pulse_router = APIRouter(prefix="/pulse", tags=["pulse"])


manifest = IAppPlugin(
    id="pulse",
    name="PULSE",
    version="7.0.0",
    description="AI Work & Microtask Platforms — Outlier, Mindrift, DataAnnotation, Remotasks, Freelancer Microtasks, LinkedIn Easy Apply, Opyre Microtasks",
    icon="Zap",
    order=11,
    db_path="pulse/pulse.db",
    models=[],
    routers=[pulse_router],
    router_prefix="/pulse",
    scheduler_jobs=get_pulse_jobs(),
    agent_class=None,
    frontend_routes=[
        {"path": "/pulse", "component": "Pulse.vue", "meta": {"title": "PULSE — AI Work"}},
        {
            "path": "/pulse/opportunities",
            "component": "PulseOpportunities.vue",
            "meta": {"title": "PULSE Opportunities"},
        },
    ],
    widgets=[
        {
            "id": "pulse-monthly-revenue",
            "label": "Monthly Earnings",
            "icon": "DollarSign",
            "query": "pulse/revenue/monthly",
        },
        {"id": "pulse-top-platform", "label": "Top Platform", "icon": "Trophy", "query": "pulse/top-platform"},
        {
            "id": "pulse-available-tasks",
            "label": "Available Tasks",
            "icon": "ListChecks",
            "query": "pulse/available-tasks",
        },
    ],
    providers=PULSE_ADAPTERS,
    requires_auth=True,
    hidden=False,
)
