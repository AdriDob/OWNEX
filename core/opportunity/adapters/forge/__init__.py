"""Forge cycle adapters — dev bounty platform discovery.

Each module exposes an async ``fetch_opportunities()`` function
that returns ``list[RawOpportunity]`` or ``list[dict]``.

Backward compatible re-exports from the original forge module.
"""

from __future__ import annotations

# Backwards-compatible class re-exports for existing code in engine.py, OpportunityEngine, etc.
from ..forge_legacy import (
    AlgoraAdapter,
    ForgeAdapter,
    OpireAdapter,
    SuperteamAdapter,
)

# Re-export function-based adapters (import from per-module functions into canary toolchains)
from .algora import fetch_opportunities as fetch_algora_opportunities
from .freelancer import fetch_opportunities as fetch_freelancer_opportunities
from .github_sponsors import fetch_opportunities as fetch_github_sponsors_opportunities
from .issuehunt import fetch_opportunities as fetch_issuehunt_opportunities
from .opencollective import fetch_opportunities as fetch_opencollective_opportunities
from .opencollective_projects import fetch_opportunities as fetch_opencollective_projects_opportunities
from .opire import fetch_opportunities as fetch_opire_opportunities
from .superteam import fetch_opportunities as fetch_superteam_opportunities

__all__ = [
    "fetch_algora_opportunities",
    "fetch_opire_opportunities",
    "fetch_superteam_opportunities",
    "fetch_github_sponsors_opportunities",
    "fetch_freelancer_opportunities",
    "fetch_issuehunt_opportunities",
    "fetch_opencollective_opportunities",
    "fetch_opencollective_projects_opportunities",
    "AlgoraAdapter",
    "ForgeAdapter",
    "OpireAdapter",
    "SuperteamAdapter",
]
