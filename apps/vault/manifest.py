"""VAULT App Manifest — Bug Bounty Platforms."""

from __future__ import annotations

from fastapi import APIRouter

from core.interfaces.app import IAppPlugin
from core.scheduler.jobs import get_vault_jobs

# Adapter provider strings for the adapter registry
VAULT_ADAPTERS = [
    "core.opportunity.adapters.security_bounty:HackerOneAdapter",
    "core.opportunity.adapters.security_bounty:BugcrowdAdapter",
    "core.opportunity.adapters.security_bounty:IntigritiAdapter",
    "core.opportunity.adapters.security_bounty:YesWeHackAdapter",
]


# Router
vault_router = APIRouter(prefix="/vault", tags=["vault"])


manifest = IAppPlugin(
    id="vault",
    name="VAULT",
    version="7.0.0",
    description="Bug Bounty Platforms — HackerOne, Bugcrowd, Intigriti, Synack, YesWeHack, Immunefi",
    icon="Shield",
    order=20,
    db_path="vault/vault.db",
    models=[],
    routers=[vault_router],
    router_prefix="/vault",
    scheduler_jobs=get_vault_jobs(),
    agent_class=None,
    frontend_routes=[
        {"path": "/vault", "component": "Vault.vue", "meta": {"title": "VAULT — Bug Bounty"}},
        {"path": "/vault/programs", "component": "VaultPrograms.vue", "meta": {"title": "VAULT Programs"}},
    ],
    widgets=[
        {"id": "vault-total-bounty", "label": "Total Bounty Pool", "icon": "DollarSign", "query": "vault/bounty/total"},
        {"id": "vault-active-programs", "label": "Active Programs", "icon": "Shield", "query": "vault/active-programs"},
        {"id": "vault-top-severity", "label": "Top Severity", "icon": "AlertTriangle", "query": "vault/top-severity"},
    ],
    providers=VAULT_ADAPTERS,
    requires_auth=True,
    hidden=False,
)
