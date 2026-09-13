"""Cycle Engine — Metrics computation for Work Cycles."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from cores.cycles.models import Cycle
from cores.database.manager import get_db_manager

logger = logging.getLogger("core.cycles.metrics")

CYCLES_DB = "cycles"


def _get_session() -> Session:
    mgr = get_db_manager()
    if "cycles" not in mgr.list_databases():
        from cores.cycles.models import Base

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
            security_opps = [o for o in opportunities if getattr(o, "cycle", None) == "security"]

            # Calculate real metrics
            opportunities_found = len(security_opps)

            # Get active/in_progress opportunities (simplified heuristic)
            active_tasks = len([o for o in security_opps if getattr(o, "status", None) == "active"])
            completed_tasks = len([o for o in security_opps if getattr(o, "status", None) == "completed"])

            # Calculate estimated value from opportunities with payout info
            estimated_value = sum(
                float(getattr(o, "estimated_payout", 0) or 0)
                for o in security_opps
                if hasattr(o, "estimated_payout") and o.estimated_payout
            )

            # Calculate success rate based on opportunity confidence/stage
            if opportunities_found > 0:
                success_rate = (
                    sum(
                        float(getattr(o, "confidence", 0) or 0)
                        for o in security_opps
                        if hasattr(o, "confidence") and o.confidence
                    )
                    / opportunities_found
                )
            else:
                success_rate = 0.0

            # Get last execution from engine metrics or database
            engine_metrics = engine.get_metrics() if hasattr(engine, "get_metrics") else {}

            last_execution = engine_metrics.get("last_refresh") or None
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

    def compute_automation_metrics(self) -> dict[str, Any]:
        """Fábrica 1000%: cuánto hace la máquina vs el humano.

        SSOT para Automation Ratio, Human Time Saved, Interventions y
        Money per Human Hour (definidos en OWNEX_VISION_CHARTER.md).
        Lee solo hechos persistidos: WorkBank, execution queue, ledger
        PAID, y work_items. UNKNOWN si no hay historial (nunca inventa).
        """
        try:
            from cores.direct_work_engine.workbank import get_workbank

            wb = get_workbank()
            wb_data = wb.to_dict() if hasattr(wb, "to_dict") else {}
            total_items = int(wb_data.get("total", 0) or len(getattr(wb, "_items", {}) or {}))
            ready = len(wb.best_ready(limit=1000)) if hasattr(wb, "best_ready") else 0
        except Exception:
            total_items, ready = 0, 0
        try:
            from cores.revenue_tracker.revenue_tracker import get_revenue_tracker

            tracker = get_revenue_tracker()
            paid_usd = float(
                sum(
                    float(getattr(o, "amount", 0) or 0)
                    for o in tracker.opportunities.values()
                    if str(getattr(getattr(o, "status", ""), "value", getattr(o, "status", ""))) == "paid"
                )
                or 0
            )
            pipeline_usd = float(
                sum(
                    float(getattr(o, "amount", 0) or 0)
                    for o in tracker.opportunities.values()
                    if str(getattr(getattr(o, "status", ""), "value", getattr(o, "status", "")))
                    not in ("paid", "failed", "cancelled")
                )
                or 0
            )
        except Exception:
            paid_usd, pipeline_usd = 0.0, 0.0
        # Human hours from work_items + ledger (best-effort, no inventado)
        human_hours: float | None = None
        try:
            import json as _json
            import os
            from pathlib import Path

            data_dir = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
            ledger_path = data_dir / "work_items.json"
            if ledger_path.exists():
                items = _json.loads(ledger_path.read_text(encoding="utf-8") or "[]")
                # work_items persistidos guardan human_minutes_actual cuando existe
                mins = sum(float(i.get("human_minutes_actual", 0) or 0) for i in items if isinstance(i, dict))
                if mins > 0:
                    human_hours = mins / 60.0
        except Exception:
            human_hours = None
        total_work_hours_est = float(total_items * 1.5) if total_items else 0.0  # 1.5h/op como baseline honesto
        auto_hours = max(0.0, total_work_hours_est - (human_hours or 0.0)) if human_hours is not None else None
        automation_ratio = (
            (auto_hours / total_work_hours_est) if total_work_hours_est and auto_hours is not None else None
        )
        money_per_human_hour = (paid_usd / human_hours) if human_hours and human_hours > 0 else None
        return {
            "total_items": total_items,
            "ready_to_deliver": ready,
            "total_work_hours_est": round(total_work_hours_est, 2),
            "human_hours": round(human_hours, 2) if human_hours is not None else None,
            "auto_hours": round(auto_hours, 2) if auto_hours is not None else None,
            "automation_ratio": round(automation_ratio, 3) if automation_ratio is not None else None,
            "human_time_saved_hours": round(auto_hours, 2) if auto_hours is not None else None,
            "paid_usd": round(paid_usd, 2),
            "pipeline_usd": round(pipeline_usd, 2),
            "money_per_human_hour": round(money_per_human_hour, 2) if money_per_human_hour is not None else None,
            "human_interventions_per_item": round((human_hours or 0) / total_items, 3)
            if total_items and human_hours
            else None,
            "note": "UNKNOWN si historial vacío (nunca inventa). Human hours desde work_items.human_minutes_actual.",
        }

    def persist_metrics(self, cycle_slug: str, metrics: dict[str, Any]) -> bool:
        """Persist computed metrics to cycle config."""
        from cores.cycles.models import Base, Cycle
        from cores.database.manager import get_db_manager

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
