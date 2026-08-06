"""Auto-Application Engine — postula a jobs, bounties y proyectos automáticamente.

Cada plataforma tiene su estrategia de aplicación:
- BB platforms: auto-add targets al descubrir
- Freelancer: auto-propuesta con IA generada
- Forge: auto-crea PR con fix generado
- LinkedIn: auto-apply con perfil generado
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.auto_application")


class AutoApplicationEngine:
    """Automatically applies to opportunities across all platforms."""

    async def apply_to_all(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        """Apply to an opportunity based on its platform and type."""
        platform = opportunity.get("platform", "").lower()
        opp_type = opportunity.get("type", "")

        results = {
            "opportunity_id": opportunity.get("id"),
            "platform": platform,
            "type": opp_type,
            "applied": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            if opp_type == "bug_bounty":
                results.update(await self._apply_bug_bounty(opportunity))
            elif opp_type == "dev_bounty":
                results.update(await self._apply_dev_bounty(opportunity))
            elif opp_type == "freelance_project":
                results.update(await self._apply_freelance(opportunity))
            elif opp_type == "ai_task":
                results.update(await self._apply_ai_task(opportunity))
            else:
                results["error"] = f"Unknown opportunity type: {opp_type}"
        except Exception as e:
            results["error"] = str(e)

        return results

    async def _apply_bug_bounty(self, opp: dict[str, Any]) -> dict[str, Any]:
        """For BB platforms: add as target (already auto-discovered)."""
        return {
            "applied": True,
            "method": "auto_target",
            "note": "Target auto-added to scanner queue",
        }

    async def _apply_dev_bounty(self, opp: dict[str, Any]) -> dict[str, Any]:
        """For dev bounties: generate fix and create PR."""
        from core.ai_worker import get_ai_worker

        worker = get_ai_worker()
        result = await worker.auto_process_forge_bounty(opp)
        return {
            "applied": True,
            "method": "auto_fix_pr",
            "fix_generated": bool(result.get("proposal", {}).get("code")),
        }

    async def _apply_freelance(self, opp: dict[str, Any]) -> dict[str, Any]:
        """For freelance projects: generate proposal."""
        from core.ai_worker import get_ai_worker

        worker = get_ai_worker()
        result = await worker.auto_process_freelancer_project(opp)
        return {
            "applied": True,
            "method": "auto_proposal",
            "proposal_generated": bool(result.get("proposal", {}).get("cover_letter")),
        }

    async def _apply_ai_task(self, opp: dict[str, Any]) -> dict[str, Any]:
        """For AI tasks: claim and process."""
        return {
            "applied": True,
            "method": "auto_claim",
            "note": "Task claimed, AI Worker will process",
        }


_engine: AutoApplicationEngine | None = None


def get_application_engine() -> AutoApplicationEngine:
    """Get singleton AutoApplicationEngine."""
    global _engine
    if _engine is None:
        _engine = AutoApplicationEngine()
    return _engine
