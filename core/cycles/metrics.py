"""Cycle Engine — Metrics computation for Work Cycles."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from core.cycles.models import Cycle
from core.database.manager import get_db_manager

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
        # Get data from existing Rastro APIs via internal calls
        # For now return structured placeholders that will be populated by API calls
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
