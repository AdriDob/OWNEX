"""OWNEX Rapid Income Engine — Cashflow Radar (Today / Week / Growth).

Filosofía del spec "OWNEX RAPID INCOME ENGINE": maximizar la probabilidad de
encontrar tareas con ciclo corto (encontrar → ejecutar → entregar → cobrar),
NUNCA prometer sueldo garantizado (ninguna plataforma externa puede garantizar
pagos; OWNEX solo prioriza por probabilidad real).

El radar clasifica oportunidades por horizonte de cobro:

- 🟢 TODAY: completables en horas (liquidez inmediata).
- 🔵 WEEK: 1-7 días (ingreso semanal).
- 🟣 GROWTH: más largas o recurrentes (ingresos futuros / activos reutilizables).

Regla de mezcla (filosofía del owner): no perseguir solo dinero inmediato.
El mix recomendado balancea liquidez rápida + proyectos estratégicos, y cambia
según si el usuario ya tiene una base de ingresos estable.

Reutiliza motores existentes (Regla de Oro, no reimplementa):
- `success_engine.plan_opportunity_success` → probability_after_full_plan,
  humano/automatizado, approach.
- `execution_planner.plan_execution` → automation_pct, human_work_minutes,
  direct_links.
- `workbank.WorkBank` → items ya preparados listos para entregar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, TypeAlias

OpportunityDict: TypeAlias = dict[str, Any]

# Horizontes de cobro (horas humanas estimadas).
TODAY_MAX_HOURS: float = 8.0
WEEK_MAX_HOURS: float = 168.0

# Umbral de automatización para marcar "OWNEX termina antes que un humano".
SPECIAL_ADVANTAGE_AUTOMATION_PCT: int = 70

# Mix recomendado cuando el usuario NO tiene base estable: liquidez primero.
MIX_LIQUIDITY_NEEDED: dict[str, float] = {"today": 0.5, "week": 0.3, "growth": 0.2}
# Mix recomendado cuando ya existe ingreso estable: crecer activos recurrentes.
MIX_INCOME_STABLE: dict[str, float] = {"today": 0.2, "week": 0.3, "growth": 0.5}

# Categorías de ciclo corto por naturaleza: si no hay estimación de horas,
# se clasifican como TODAY en lugar de descartarlas.
_FAST_CYCLE_CATEGORIES: frozenset[str] = frozenset(
    {
        "data_annotation",
        "ai_evaluation",
        "ai_training",
        "synthetic_data",
        "prompt_engineering",
        "web_scraping",
        "qa_automation",
        "fiverr",
    }
)


class CashflowHorizon(StrEnum):
    TODAY = "today"
    WEEK = "week"
    GROWTH = "growth"


@dataclass
class RadarItem:
    id: str
    title: str
    platform: str
    category: str
    horizon: str
    reward_usd: float
    estimated_hours: float
    acceptance_probability: float
    automation_pct: int
    expected_value: float
    special_advantage: bool
    recurring: bool
    direct_link: str
    best_approach: str = ""
    automated_work: list[str] = field(default_factory=list)
    human_work: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "platform": self.platform,
            "category": self.category,
            "horizon": self.horizon,
            "reward_usd": self.reward_usd,
            "estimated_hours": self.estimated_hours,
            "acceptance_probability": self.acceptance_probability,
            "automation_pct": self.automation_pct,
            "expected_value": self.expected_value,
            "special_advantage": self.special_advantage,
            "recurring": self.recurring,
            "direct_link": self.direct_link,
            "best_approach": self.best_approach,
            "what_ownrex_prepared": self.automated_work,
            "what_remains_manual": self.human_work,
        }


@dataclass
class CashflowRadar:
    generated_at: str
    buckets: dict[str, list[RadarItem]]
    recommended_mix: dict[str, float]
    expected_income_usd: dict[str, float]
    top_pick: dict[str, Any] | None
    special_opportunities: list[dict[str, Any]]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "buckets": {k: [i.to_dict() for i in v] for k, v in self.buckets.items()},
            "recommended_mix": self.recommended_mix,
            "expected_income_usd": self.expected_income_usd,
            "top_pick": self.top_pick,
            "special_opportunities": self.special_opportunities,
            "notes": self.notes,
        }


class RapidIncomeEngine:
    """Orquesta el Cashflow Radar sobre oportunidades (dicts) o WorkBank items."""

    def radar(self, opportunities: list[OpportunityDict] | None = None) -> dict[str, Any]:
        items = self._build_items(opportunities or [])
        radar = self._assemble(items)
        return radar.to_dict()

    # ── pipeline ─────────────────────────────────────────────

    def _build_items(self, opportunities: list[OpportunityDict]) -> list[RadarItem]:
        from cores.direct_work_engine.execution_planner import plan_execution
        from cores.direct_work_engine.success_engine import plan_opportunity_success

        items: list[RadarItem] = []
        for opp in opportunities:
            try:
                plan = plan_opportunity_success(opp)
            except Exception:
                plan = {}
            prediction = plan.get("prediction", {})
            prob_after = float(prediction.get("probability_after_full_plan", 0.0) or 0.0)

            execution: Any = {}
            try:
                execution = plan_execution(opp)
                if hasattr(execution, "to_dict"):
                    execution = execution.to_dict()
            except Exception:
                pass
            automation_pct = int(execution.get("automation_pct", 0) or 0)
            human_minutes = float(execution.get("human_work_minutes", 0.0) or 0.0)
            links = execution.get("direct_links", {}) or {}
            direct_link = str(opp.get("direct_link") or opp.get("url") or links.get("apply") or "")

            reward = _to_float(opp.get("reward") or opp.get("reward_usd") or 0.0)
            hours = _estimate_hours(opp, human_minutes, str(opp.get("category", "")).lower())
            recurring = _is_recurring(opp)
            horizon = self._classify(hours, recurring)
            ev = round(reward * prob_after / max(1.0, hours), 2)

            items.append(
                RadarItem(
                    id=str(opp.get("id") or opp.get("opportunity_id") or "unknown"),
                    title=str(opp.get("title", "Untitled opportunity")),
                    platform=str(opp.get("platform", "unknown")),
                    category=str(opp.get("category", "general")),
                    horizon=horizon,
                    reward_usd=round(reward, 2),
                    estimated_hours=round(hours, 1),
                    acceptance_probability=round(prob_after, 3),
                    automation_pct=automation_pct,
                    expected_value=ev,
                    special_advantage=automation_pct >= SPECIAL_ADVANTAGE_AUTOMATION_PCT,
                    recurring=recurring,
                    direct_link=direct_link,
                    best_approach=str(plan.get("best_approach", "")),
                    automated_work=list(plan.get("automated_work", [])),
                    human_work=list(plan.get("human_work", [])),
                )
            )
        return items

    @staticmethod
    def _classify(hours: float, recurring: bool) -> str:
        if recurring or hours > WEEK_MAX_HOURS:
            return CashflowHorizon.GROWTH
        if hours <= TODAY_MAX_HOURS:
            return CashflowHorizon.TODAY
        return CashflowHorizon.WEEK

    def _assemble(self, items: list[RadarItem]) -> CashflowRadar:
        buckets: dict[str, list[RadarItem]] = {
            CashflowHorizon.TODAY: [],
            CashflowHorizon.WEEK: [],
            CashflowHorizon.GROWTH: [],
        }
        for item in items:
            buckets[item.horizon].append(item)
        for group in buckets.values():
            group.sort(key=lambda i: i.expected_value, reverse=True)

        mix = self._recommended_mix(items)
        expected = {h: round(sum(i.expected_value for i in group), 2) for h, group in buckets.items()}
        top_pick = self._top_pick(buckets)
        special = [
            i.to_dict()
            for i in sorted(
                (it for it in items if it.special_advantage),
                key=lambda it: it.expected_value,
                reverse=True,
            )
        ]
        notes = self._notes(mix)
        return CashflowRadar(
            generated_at=datetime.now(UTC).isoformat(),
            buckets=buckets,
            recommended_mix=mix,
            expected_income_usd=expected,
            top_pick=top_pick,
            special_opportunities=special,
            notes=notes,
        )

    @staticmethod
    def _recommended_mix(items: list[RadarItem]) -> dict[str, float]:
        has_stable_base = any(i.recurring and i.acceptance_probability >= 0.5 for i in items)
        return dict(MIX_INCOME_STABLE if has_stable_base else MIX_LIQUIDITY_NEEDED)

    @staticmethod
    def _top_pick(buckets: dict[str, list[RadarItem]]) -> dict[str, Any] | None:
        liquidity = buckets[CashflowHorizon.TODAY] + buckets[CashflowHorizon.WEEK]
        if liquidity:
            best = max(liquidity, key=lambda i: i.expected_value)
        elif buckets[CashflowHorizon.GROWTH]:
            best = max(buckets[CashflowHorizon.GROWTH], key=lambda i: i.expected_value)
        else:
            return None
        return best.to_dict()

    @staticmethod
    def _notes(mix: dict[str, float]) -> list[str]:
        if mix == MIX_LIQUIDITY_NEEDED:
            return [
                "Sin base de ingreso estable detectada: priorizá liquidez rápida (TODAY) "
                "para cubrir flujo, sin descuidar la siembra semanal (WEEK).",
                "El mix es una recomendación de foco, no una promesa de pago. "
                "Ninguna plataforma externa puede garantizar cobro.",
            ]
        return [
            "Base de ingreso estable detectada: la mayoría del foco va a GROWTH "
            "(proyectos recurrentes y activos reutilizables) para aumentar ingresos futuros.",
            "El mix es una recomendación de foco, no una promesa de pago. "
            "Ninguna plataforma externa puede garantizar cobro.",
        ]

    # ── formatos del spec ────────────────────────────────────

    @staticmethod
    def daily_digest(radar: dict[str, Any]) -> dict[str, str]:
        lines = ["OWNEX DAILY OPPORTUNITIES", ""]
        for i, item in enumerate(radar["buckets"].get("today", [])[:5], start=1):
            lines.append(
                f"{i}. {item['title']} | Reward: ${item['reward_usd']} | "
                f"Estimated time: {item['estimated_hours']}h | "
                f"Acceptance probability: {int(item['acceptance_probability'] * 100)}% | "
                f"Automation potential: {item['automation_pct']}% | "
                f"Direct link: {item['direct_link'] or 'n/a'}"
            )
        if len(lines) == 2:
            lines.append("Sin oportunidades TODAY: corré /direct-work/workbank/cycle primero.")
        return {"text": "\n".join(lines)}

    @staticmethod
    def weekly_plan(radar: dict[str, Any]) -> dict[str, Any]:
        week_items = radar["buckets"].get("week", [])
        growth_items = radar["buckets"].get("growth", [])
        all_items = week_items + growth_items
        expected_earnings = radar["expected_income_usd"].get("week", 0.0) + radar["expected_income_usd"].get(
            "growth", 0.0
        )
        human_hours = round(sum(i["estimated_hours"] for i in all_items), 1)
        priority = [i["title"] for i in sorted(all_items, key=lambda i: i["expected_value"], reverse=True)]
        return {
            "text": (
                "OWNEX WEEKLY INCOME PLAN\n\n"
                f"Highest probability opportunities: {', '.join(priority[:3]) or 'n/a'}\n"
                f"Expected earnings (EV): ${expected_earnings}\n"
                f"Required human hours: {human_hours}\n"
                f"Automation possible: {round(sum(i['automation_pct'] for i in all_items) / max(1, len(all_items)), 0)}%\n"
                f"Priority order: {', '.join(priority) or 'n/a'}"
            ),
            "expected_earnings_usd": round(expected_earnings, 2),
            "human_hours": human_hours,
            "automation_pct": round(sum(i["automation_pct"] for i in all_items) / max(1, len(all_items)), 0),
            "priority_order": priority,
        }


# ── helpers deterministas ────────────────────────────────────


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _estimate_hours(opp: OpportunityDict, human_minutes: float, category: str) -> float:
    explicit = _to_float(opp.get("estimated_hours") or opp.get("estimated_time_hours") or 0.0)
    if explicit > 0:
        return explicit
    if human_minutes > 0:
        return human_minutes / 60.0
    if category in _FAST_CYCLE_CATEGORIES:
        return 4.0
    return 24.0


def _is_recurring(opp: OpportunityDict) -> bool:
    return bool(opp.get("recurring") or opp.get("recurring_income"))


def get_radar(opportunities: list[OpportunityDict] | None = None) -> dict[str, Any]:
    """Public entry point: Cashflow Radar sobre oportunidades dadas o el WorkBank."""
    engine = RapidIncomeEngine()
    if opportunities is None:
        from cores.direct_work_engine.workbank import get_workbank

        bank_items = get_workbank().best_ready(limit=50)
        opportunities = [item.to_dict() for item in bank_items]
    return engine.radar(opportunities)
