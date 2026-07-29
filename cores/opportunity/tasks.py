"""Background tasks for the opportunity pipeline — sync scores, scoring, and cleanup.

These functions are invoked by the scheduler as cron/interval jobs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("ownex.opportunity.tasks")


async def prioritize_targets(
    raw_opps: list[Any],
    cycle: str = "forge",
) -> list[dict[str, Any]]:
    """Score and rank raw opportunities.

    Uses reward/effort ratio, tags, and freshness to prioritize.
    """
    scored = []
    for opp in raw_opps:
        reward = getattr(opp, "reward", opp.get("reward", 0) if isinstance(opp, dict) else 0)
        effort = getattr(opp, "effort_hours", opp.get("effort_hours", 4) if isinstance(opp, dict) else 4)

        # Score = reward per hour, with diminishing returns for very high rewards
        score = (float(reward or 0) / max(1, float(effort or 1))) / 10.0
        scored.append((score, opp))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [dict(s[1]) if hasattr(s[1], "items") else s[1] for s in scored]


async def sync_cycle_scores(cycle: str = "forge", dry_run: bool = False) -> dict[str, Any]:
    """Sync and score all opportunities for a cycle."""
    logger.info(f"sync_cycle_scores({cycle}) — starting")

    try:
        from core.opportunity.engine import OpportunityOrchestrator

        orchestrator = OpportunityOrchestrator()
        results = await orchestrator.execute_cycle(cycle, limit=50)
        logger.info(f"sync_cycle_scores({cycle}) — {len(results)} opportunities processed")

        return {
            "cycle": cycle,
            "count": len(results),
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"sync_cycle_scores({cycle}) FAILED: {e}")
        return {
            "cycle": cycle,
            "count": 0,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def purge_stale_opportunities(hours: int = 72) -> dict[str, Any]:
    """Remove stale opportunities older than `hours`."""
    from datetime import timedelta

    stale_before = datetime.now(timezone.utc) - timedelta(hours=hours)
    logger.info(f"Purge stale opportunities before {stale_before.isoformat()}")

    try:
        from core.opportunity import get_engine

        engine = get_engine()
        purged = engine.purge_stale(before=stale_before)
        logger.info(f"Purged {purged} stale opportunities")
        return {"purged": purged, "success": True}

    except Exception as e:
        logger.error(f"Purge FAILED: {e}")
        return {"purged": 0, "success": False, "error": str(e)}
