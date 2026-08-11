"""SystemContextBuilder — aggregates system-wide state for COPILOT recommendations.

This is the bridge between raw system state and COPILOT context.
It queries the DB, scheduler, and other modules to answer:
"What is happening in ORION right now?"
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.copilot.context import CopilotContext
from core.copilot.permissions import AuthorityLevel

logger = logging.getLogger("orion.core.copilot.system_context")


class SystemContextBuilder:
    """Builds a CopilotContext populated with system-wide state."""

    def __init__(self, db_session_factory: Any | None = None) -> None:
        self._db_factory = db_session_factory

    def build(
        self,
        authority: AuthorityLevel = AuthorityLevel.SENIOR_HUNTER,
        extra: dict[str, Any] | None = None,
    ) -> CopilotContext:
        ctx = CopilotContext(app_id="orion", authority_level=authority)
        state = self._collect_system_state()
        if extra:
            state.update(extra)
        ctx.set_system_state(state)
        return ctx

    def _collect_system_state(self) -> dict[str, Any]:
        """Query DB for targets, findings, and scheduler info."""
        state: dict[str, Any] = {
            "collected_at": datetime.now(UTC).isoformat(),
            "targets": self._get_targets_summary(),
            "findings": self._get_findings_summary(),
            "scheduler": self._get_scheduler_status(),
        }
        return state

    def _get_targets_summary(self) -> list[dict[str, Any]]:
        """Return pending targets from the database."""
        if not self._db_factory:
            return []
        try:
            from database.models import Target

            session = self._db_factory()
            rows = (
                session.query(
                    Target.id,
                    Target.name,
                    Target.domain,
                    Target.status,
                    Target.last_scanned,
                    Target.orion_score,
                )
                .filter(Target.status.in_(["active", "pending"]))
                .order_by(Target.orion_score.desc().nullslast())
                .limit(20)
                .all()
            )
            session.close()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "domain": r.domain,
                    "status": r.status,
                    "last_scanned": str(r.last_scanned) if r.last_scanned else None,
                    "score": float(r.orion_score or 0.0),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.debug("Could not query targets: %s", exc)
            return []

    def _get_findings_summary(self) -> dict[str, int]:
        """Return counts of findings grouped by status."""
        if not self._db_factory:
            return {}
        try:
            from database.models import Finding

            session = self._db_factory()
            total = session.query(Finding).count()
            open_count = session.query(Finding).filter(Finding.status == "open").count()
            confirmed = session.query(Finding).filter(Finding.status == "confirmed").count()
            rejected = session.query(Finding).filter(Finding.status == "rejected").count()
            session.close()
            return {"total": total, "open": open_count, "confirmed": confirmed, "rejected": rejected}
        except Exception as exc:
            logger.debug("Could not query findings: %s", exc)
            return {}

    def _get_scheduler_status(self) -> dict[str, Any]:
        """Return scheduler metadata (no direct access, just a placeholder)."""
        return {
            "available": True,
            "note": "Scheduler status available via /api/health",
        }

    def prioritize_targets(self, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort targets by combined score, highest first."""
        return sorted(targets, key=lambda t: t.get("score", 0.0), reverse=True)

    def top_actions(self, ctx: CopilotContext) -> list[dict[str, Any]]:
        """Derive top-level actions from system state."""
        actions: list[dict[str, Any]] = []
        state = ctx.system_state
        findings = state.get("findings", {})
        targets = state.get("targets", [])

        if findings.get("open", 0) > 0:
            actions.append(
                {
                    "action": "validate_findings",
                    "count": findings["open"],
                    "priority": 5,
                    "reason": f"{findings['open']} findings pending validation",
                }
            )
        if findings.get("confirmed", 0) > 0:
            actions.append(
                {
                    "action": "generate_reports",
                    "count": findings["confirmed"],
                    "priority": 4,
                    "reason": f"{findings['confirmed']} findings ready for reporting",
                }
            )
        if targets:
            high_value = [t for t in targets if t.get("score", 0) >= 7.0]
            if high_value:
                actions.append(
                    {
                        "action": "deep_study_targets",
                        "count": len(high_value),
                        "priority": 5,
                        "reason": f"{len(high_value)} high-value targets ready for deep analysis",
                    }
                )
            medium = [t for t in targets if 4.0 <= t.get("score", 0) < 7.0]
            if medium:
                actions.append(
                    {
                        "action": "recon_targets",
                        "count": len(medium),
                        "priority": 3,
                        "reason": f"{len(medium)} medium-value targets need recon",
                    }
                )
        if not targets and findings.get("total", 0) == 0:
            actions.append(
                {
                    "action": "discover_targets",
                    "priority": 2,
                    "reason": "No targets or findings — start discovery",
                }
            )
        return sorted(actions, key=lambda a: a.get("priority", 0), reverse=True)
