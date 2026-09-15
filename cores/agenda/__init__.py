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
        # Use mission target when available, else current plan's target; never hardcode WEEKLY_500 alone
        target = None
        try:
            from api.routers.mission_hub import _load_state

            st = _load_state()
            usd = float(st.get("target_usd", 5000) or 5000)
            # Map to tier: 500/2500/5000
            if usd >= 4000:
                target = engine.create_target(TargetTier.MONTHLY_5000)
            elif usd >= 1500:
                target = engine.create_target(TargetTier.MONTHLY_2500)
            else:
                target = engine.create_target(TargetTier.WEEKLY_500)
        except Exception:
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
                            url="/operations/work-queue",
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
        from cores.capital.forecasting import get_forecasting_engine

        # Real forecast with correct signature: work_income + savings vanish, not expenses inventados
        try:
            from cores.revenue.ledger import get_revenue_ledger

            ledger = get_revenue_ledger()
            paid = (
                ledger.get_paid_entries()
                if hasattr(ledger, "get_paid_entries")
                else ledger.get_by_state("PAID")
                if hasattr(ledger, "get_by_state")
                else []
            )
            monthly_net = round(
                sum(float((e.to_dict() if hasattr(e, "to_dict") else e).get("net_usd", 0) or 0) for e in (paid or []))
                / max(1, 1),
                2,
            )
        except Exception:
            monthly_net = 0.0
        fc = get_forecasting_engine()
        result = fc.forecast(work_income_usd_per_month=monthly_net or 0, savings_usd_per_month=0, horizon_months=12)
        horizons = result.get("horizons", {}) if isinstance(result, dict) else getattr(result, "horizons", {})
        if horizons:
            # Pick 12m P50 as long-term milestone
            h12 = horizons.get("month_12")
            if h12:
                p50 = getattr(h12, "p50", None) if not isinstance(h12, dict) else h12.get("p50")
                eta = datetime.now(UTC) + timedelta(days=365)
                items.append(
                    AgendaItem(
                        date=eta.strftime("%Y-%m-%d"),
                        horizon=Horizon.LONG.value,
                        source=Source.CAPITAL.value,
                        title=f"Capital 12m P50: ${int(p50 or 0):,}" if p50 else "Capital: revisá runway mensual",
                        reward_or_value=float(p50 or 0) if p50 else None,
                        url="/capital",
                        action="Revisar allocation y runway mensualmente",
                    )
                )
    except Exception as e:
        logger.debug("capital agenda error: %s", e)
    return items


def build_unified_agenda() -> dict[str, Any]:
    """Agrega TODO en una sola vista de agenda. Best action balancea reward + learning + deadline."""
    all_items: list[AgendaItem] = []

    for fetcher in (_from_workbank, _from_income_target, _from_career, _from_capital):
        with contextlib.suppress(Exception):
            all_items.extend(fetcher())

    by_horizon: dict[str, list[dict]] = {}
    for item in all_items:
        by_horizon.setdefault(item.horizon, []).append(item.to_dict())

    for h in by_horizon:
        by_horizon[h].sort(key=lambda x: -(x.get("reward") or 0))

    # Best action: balance work (reward) + career (unlock) + capital (deadline)
    # Score: reward*0.5 + horizon bonus + source diversity (don't always pick work)
    best = None
    if all_items:

        def _score(it: AgendaItem) -> float:
            base = float(it.reward_or_value or 0)
            # Career unlocks get minimum 50 to compete with $0 work items without reward
            if it.source == Source.CAREER.value and base == 0:
                base = 50.0
            # Boost medium/long that are overdue (progress <30%)
            if it.horizon in (Horizon.MEDIUM.value, Horizon.LONG.value) and it.progress_pct < 30:
                base += 20.0
            # Today horizon bonus
            if it.horizon == Horizon.TODAY.value:
                base += 10.0
            return base

        best = max(all_items, key=_score).to_dict()

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_items": len(all_items),
        "today": by_horizon.get("today", [])[:5],
        "short_term": by_horizon.get("short", [])[:5],
        "medium_term": by_horizon.get("medium", [])[:5],
        "long_term": by_horizon.get("long", [])[:5],
        "counts": {h: len(items) for h, items in by_horizon.items()},
        "best_action": best,
    }
