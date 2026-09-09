"""Supervisor — User-facing dashboard for evolution status."""

from __future__ import annotations

from typing import Any


class EvolutionSupervisor:
    def get_status(self) -> dict[str, Any]:
        from core.evolution.engine import get_evolution_engine

        engine = get_evolution_engine()
        summary = engine.summary()
        pending = engine.pending_approvals()

        return {
            "autonomy_level": summary["autonomy_level"],
            "proposals": {
                "total": summary["total_proposals"],
                "applied": summary["applied"],
                "pending_approval": summary["pending_approval"],
                "rejected": summary["rejected"],
            },
            "pending_approvals": [
                {
                    "id": p.id,
                    "title": p.title,
                    "description": p.description,
                    "risk_score": p.risk_score,
                    "level_required": p.level_required.name,
                    "impact_areas": p.impact_areas,
                }
                for p in pending[-10:]
            ],
            "health": self._get_health_summary(),
        }

    def _get_health_summary(self) -> dict[str, Any]:
        health = {}
        try:
            import psutil

            health["cpu"] = psutil.cpu_percent(interval=0.1)
            health["memory"] = psutil.virtual_memory().percent
            health["disk"] = psutil.disk_usage("/").percent
        except Exception:
            pass
        try:
            from core.commander.context_engine import build_context

            ctx = build_context()
            health["context_blocks"] = list(ctx.blocks.keys())
        except Exception:
            pass
        return health
