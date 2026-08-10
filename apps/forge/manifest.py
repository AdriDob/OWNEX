"""FORGE App Manifest — Open Source Funding & Issue Bounties."""

from __future__ import annotations

from fastapi import APIRouter

from core.interfaces.app import IAppPlugin
from core.scheduler.jobs import get_forge_jobs

# Adapter provider strings for the adapter registry
FORGE_ADAPTERS = [
    "core.opportunity.adapters.forge.opencollective:fetch_opportunities",
    "core.opportunity.adapters.forge.opencollective_projects:fetch_opportunities",
    "core.opportunity.adapters.forge.algora:fetch_opportunities",
    "core.opportunity.adapters.forge.superteam:fetch_opportunities",
    "core.opportunity.adapters.forge.github_sponsors:fetch_opportunities",
    "core.opportunity.adapters.forge.freelancer:fetch_opportunities",
    "core.opportunity.adapters.forge.issuehunt:fetch_opportunities",
    "core.opportunity.adapters.forge.opire:fetch_opportunities",
]


# Router will be auto-discovered from api/routers/forge.py if it exists
forge_router = APIRouter(prefix="/forge", tags=["forge"])


manifest = IAppPlugin(
    id="forge",
    name="FORGE",
    version="7.0.0",
    description="Open Source Funding & Issue Bounty Platforms — Algora, OpenCollective, GitHub Sponsors, Superteam, Freelancer, IssueHunt, IssueHand, Opire",
    icon="Hammer",
    order=10,
    db_path="forge/forge.db",
    models=[],
    routers=[forge_router],
    router_prefix="/forge",
    scheduler_jobs=get_forge_jobs(),
    agent_class=None,
    frontend_routes=[
        {"path": "/forge", "component": "Forge.vue", "meta": {"title": "FORGE — Open Source Funding"}},
        {
            "path": "/forge/opportunities",
            "component": "ForgeOpportunities.vue",
            "meta": {"title": "FORGE Opportunities"},
        },
    ],
    widgets=[
        {
            "id": "forge-monthly-revenue",
            "label": "Monthly Revenue",
            "icon": "DollarSign",
            "query": "forge/revenue/monthly",
        },
        {"id": "forge-top-platform", "label": "Top Platform", "icon": "Trophy", "query": "forge/top-platform"},
        {"id": "forge-active-bounties", "label": "Active Bounties", "icon": "Target", "query": "forge/active-bounties"},
    ],
    providers=FORGE_ADAPTERS,
    requires_auth=True,
    hidden=False,
)
