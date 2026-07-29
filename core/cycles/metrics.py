"""Cycle Engine — Metrics computation for Work Cycles."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from core.cycles.models import Cycle
from core.database.manager import get_db_manager

logger = logging.getLogger("core.cycles.metrics")

CYCLES_DB = "cycles"


def _get_session() -> Session:
    mgr = get_db_manager()
    if "cycles" not in mgr.list_databases():
        from core.cycles.models import Base
        mgr.register("cycles", "cycles.db")
        mgr.run_migrations("cycles", Base)
    return mgr.get_session("cycles")


class CycleMetricsEngine:
    """Computes metrics for Work Cycles from live system data."""

    def __init__(self) -> None:
        self._session = _get_session()

    def _get_cycle(self, slug: str):
        return self._session.query(Cycle).filter(Cycle.slug == slug).first()

    def compute_security_cycle(self) -> dict[str, Any]:
        """Compute metrics for Security Cycle (Rastro/Bug Bounty)."""
        # Get data from real Rastro opportunities via OpportunityEngine
        try:
            from cores.opportunity.engine import get_engine
            engine = get_engine()
            opportunities = engine.get_all()

            # Filter to security cycle opportunities
            security_opps = [o for o in opportunities if getattr(o, 'cycle', None) == 'security']

            # Calculate real metrics
            opportunities_found = len(security_opps)

            # Get active/in_progress opportunities (simplified heuristic)
            active_tasks = len([o for o in security_opps if getattr(o, 'status', None) == 'active'])
            completed_tasks = len([o for o in security_opps if getattr(o, 'status', None) == 'completed'])

            # Calculate estimated value from opportunities with payout info
            estimated_value = sum(
                float(getattr(o, 'estimated_payout', 0) or 0)
                for o in security_opps
                if hasattr(o, 'estimated_payout') and o.estimated_payout
            )

            # Calculate success rate based on opportunity confidence/stage
            if opportunities_found > 0:
                success_rate = sum(
                    float(getattr(o, 'confidence', 0) or 0)
                    for o in security_opps
                    if hasattr(o, 'confidence') and o.confidence
                ) / opportunities_found
            else:
                success_rate = 0.0

            # Get last execution from engine metrics or database
            engine_metrics = engine.get_metrics() if hasattr(engine, 'get_metrics') else {}

            last_execution = engine_metrics.get('last_refresh') or None
            next_action = "Scan targets in Rastro"

            return {
                "opportunities_found": opportunities_found,
                "tasks_active": active_tasks,
                "tasks_completed": completed_tasks,
                "estimated_value": estimated_value,
                "success_rate": success_rate,
                "last_execution": last_execution,
                "next_action": next_action,
            }
        except Exception as e:
            # Fallback to placeholder if real data unavailable
            logger.warning("Failed to compute security cycle from real data: %s", e)
            return {
                "opportunities_found": 0,
                "tasks_active": 0,
                "tasks_completed": 0,
                "estimated_value": 0.0,
                "success_rate": 0.0,
                "last_execution": None,
                "next_action": "Scan targets in Rastro",
            }

    def compute_forge_cycle(self) -> dict[str, Any]:
        """Compute metrics for Forge Cycle (Dev Bounty)."""
        return {
            "opportunities_found": 0,
            "tasks_active": 0,
            "tasks_completed": 0,
            "estimated_value": 0.0,
            "success_rate": 0.0,
            "last_execution": None,
            "next_action": "Connect Superteam/Opire APIs",
        }

    def compute_pulse_cycle(self) -> dict[str, Any]:
        """Compute metrics for Pulse Cycle (AI Work)."""
        return {
            "opportunities_found": 0,
            "tasks_active": 0,
            "tasks_completed": 0,
            "estimated_value": 0.0,
            "success_rate": 0.0,
            "last_execution": None,
            "next_action": "Configure AI work platforms",
        }

    def compute_vault_cycle(self) -> dict[str, Any]:
        """Compute metrics for Vault Cycle (Wealth/Finance)."""
        return {
            "opportunities_found": 0,
            "tasks_active": 0,
            "tasks_completed": 0,
            "estimated_value": 0.0,
            "success_rate": 0.0,
            "last_execution": None,
            "next_action": "Connect financial data sources",
        }

    def compute_atlas_cycle(self) -> dict[str, Any]:
        """Compute metrics for Atlas Cycle (Research/Intelligence)."""
        return {
            "opportunities_found": 0,
            "tasks_active": 0,
            "tasks_completed": 0,
            "estimated_value": 0.0,
            "success_rate": 0.0,
            "last_execution": None,
            "next_action": "Configure research sources",
        }

    def compute_all(self) -> dict[str, dict[str, Any]]:
        """Compute metrics for all cycles."""
        return {
            "security": self.compute_security_cycle(),
            "forge": self.compute_forge_cycle(),
            "pulse": self.compute_pulse_cycle(),
            "vault": self.compute_vault_cycle(),
            "atlas": self.compute_atlas_cycle(),
        }

    def persist_metrics(self, cycle_slug: str, metrics: dict[str, Any]) -> bool:
        """Persist computed metrics to cycle config."""
        from core.cycles.models import Base, Cycle
        from core.database.manager import get_db_manager
        mgr = get_db_manager()
        if "cycles" not in mgr.list_databases():
            mgr.register("cycles", "cycles.db")
            mgr.run_migrations("cycles", Base)

        session = mgr.get_session("cycles")
        try:
            cycle = session.query(Cycle).filter(Cycle.slug == cycle_slug).first()
            if not cycle:
                return False
            import json
            config = json.loads(cycle.config or "{}")
            config["metrics"] = metrics
            cycle.config = json.dumps(config)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
