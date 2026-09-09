"""OpenCollective Projects — discover open-source projects seeking funding."""

from __future__ import annotations

import logging
from typing import Any

from .opencollective import fetch_opportunities as _fetch_collectives

logger = logging.getLogger("ownex.adapters.forge.opencollective_projects")


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch project-based funding opportunities from OpenCollective."""
    try:
        # Reuse the base collector, but filter for projects specifically
        results = await _fetch_collectives()
        # Filter for project-type collectives
        projects = [
            opp
            for opp in results
            if any(tag in str(opp.get("tags", [])).lower() for tag in ["project", "oss", "opensource"])
        ]
        return projects or results[:10]
    except Exception as e:
        logger.error(f"OpenCollective projects fetch failed: {e}")
        return []
