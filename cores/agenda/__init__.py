"""Unified Agenda — conecta tareas, objetivos y metas de TODOS los módulos.

Clasifica por horizonte temporal:
  corto  → hoy-semana
  medio  → mes-trimestre
  largo  → año+

Fuentes: WorkBank · IncomeTarget · CareerRoadmap · LifeManagement · CapitalSavings
NO reconstruye nada — agrega lo que ya existe en una vista unificada.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.agenda")


class Horizon(StrEnum):
    TODAY = "today"
    SHORT = "short"  # esta semana
    MEDIUM = "medium"  # este mes / trimestre
    LONG = "long"  # año +


class Source(StrEnum):
    WORK = "work"
    CAPITAL = "capital"
    CAREER = "career"
    PERSONAL = "personal"


@dataclass(slots=True)
class AgendaItem:
    date: str
    horizon: str
    source: str
    title: str
    progress_pct: float = 0.0
    reward_or_value: float | None = None
    url: str | None = None
    action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "horizon": self.horizon,
            "source": self.source,
            "title": self.title,
            "progress_pct": round(self.progress_pct, 1),
            "reward": self.reward_or_value,
            "url": self.url,
            "action": self.action,
        }


def _from_workbank() -> list[AgendaItem]:
    items: list[AgendaItem] = []
    try:
        from cores.direct_work_engine.workbank import get_workbank

        wb = get_workbank()
        for i in wb._items.values():
            if i.status == "ready_to_deliver" and i.access_status == "public":
                items.append(
                    AgendaItem(
                        date=datetime.now(UTC).strftime("%Y-%m-%d"),
                        horizon=Horizon.TODAY.value,
                        source=Source.WORK.value,
                        title=f"Ejecutar: {i.title[:60]}",
                        reward_or_value=i.reward,
                        url=i.url or None,
                        action=f"Abrir en {i.platform}",
                    )
                )
    except Exception as e:
        logger.debug("workbank agenda error: %s", e)
    return items


def _from_income_target() -> list[AgendaItem]:
    items: list[AgendaItem] = []
    try:
        from cores.direct_work_engine.income_target import TargetTier, get_income_target_engine

        engine = get_income_target_engine()
        target = engine.create_target(TargetTier.WEEKLY_500)
        plan = engine.build_plan(target)
        if plan.weekly_plan:
            for entry in plan.weekly_plan[:5]:
                if entry.get("expected_ev", 0) > 0:
                    items.append(
                        AgendaItem(
                            date=entry["day"],
                            horizon=Horizon.SHORT.value,
                            source=Source.WORK.value,
                            title=f"{entry['action']}",
                            reward_or_value=entry.get("expected_ev", 0),
                            action="Ejecutar tarea",
                        )
                    )
    except Exception as e:
        logger.debug("income_target agenda error: %s", e)
    return items


def _from_career() -> list[AgendaItem]:
    items: list[AgendaItem] = []
    try:
        from cores.career_engine import CareerEngine, register_all_capabilities

        register_all_capabilities()
        ce = CareerEngine()
        from cores.direct_work_engine.profile_kit import ProfileKitEngine

        _kit = ProfileKitEngine()
        _raw = _kit.get() or {}
        _profile = ProfileKitEngine.profile_from_dict(_raw)
        gaps = ce.detect_skill_gaps(_profile)
        for g in gaps[:5]:
            items.append(
                AgendaItem(
                    date=datetime.now(UTC).strftime("%Y-%m-%d"),
                    horizon=Horizon.MEDIUM.value,
                    source=Source.CAREER.value,
                    title=f"Aprender: {g.skill}",
                    action=f"Prioridad {g.priority} — desbloquea categoría {g.category}",
                )
            )
    except Exception as e:
        logger.debug("career agenda error: %s", e)
    return items


def _from_capital() -> list[AgendaItem]:
    items: list[AgendaItem] = []
    try:
        from cores.capital.forecasting import CapitalForecaster

        # Si hay forecast disponible, agregar hito como item largo plazo
        fc = CapitalForecaster()
        result = fc.project(monthly_income=2000, monthly_expenses=1000)
        if result and hasattr(result, "months_to_freedom"):
            months = result.months_to_freedom
            eta = datetime.now(UTC) + timedelta(days=30 * max(1, int(months or 12)))
            items.append(
                AgendaItem(
                    date=eta.strftime("%Y-%m-%d"),
                    horizon=Horizon.LONG.value,
                    source=Source.CAPITAL.value,
                    title=f"Libertad financiera proyectada (~{int(months or 12)} meses)",
                    action="Revisar allocation y runway mensualmente",
                )
            )
    except Exception as e:
        logger.debug("capital agenda error: %s", e)
    return items


def build_unified_agenda() -> dict[str, Any]:
    """Agrega TODO en una sola vista de agenda."""
    all_items: list[AgendaItem] = []

    for fetcher in (_from_workbank, _from_income_target, _from_career, _from_capital):
        with contextlib.suppress(Exception):
            all_items.extend(fetcher())

    by_horizon: dict[str, list[dict]] = {}
    for item in all_items:
        by_horizon.setdefault(item.horizon, []).append(item.to_dict())

    for h in by_horizon:
        by_horizon[h].sort(key=lambda x: -(x.get("reward") or 0))

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_items": len(all_items),
        "today": by_horizon.get("today", [])[:5],
        "short_term": by_horizon.get("short", [])[:5],
        "medium_term": by_horizon.get("medium", [])[:5],
        "long_term": by_horizon.get("long", [])[:5],
        "counts": {h: len(items) for h, items in by_horizon.items()},
        "best_action": (max(all_items, key=lambda x: x.reward_or_value or 0).to_dict() if all_items else None),
    }
