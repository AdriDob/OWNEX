"""OWNEX MAX DAILY INCOME — plan de ejecución diaria con EV honesto.

Cierra el loop "¿cuánto puedo cobrar HOY?" con números reales, no teóricos:

- Reutiliza `success_engine.plan_opportunity_success` (probabilidad de aceptación
  con ceilings honestos por categoría) y `cashflow_radar` helpers.
- Aplica un factor de VELOCIDAD DE COBRO por categoría: un bug bounty se acepta
  en semanas (colas de revisión), un microtask se paga en días. El EV diario
  real = reward × aceptación × velocidad de cobro.
- El techo diario realista = suma de EV de los trabajos cobrables HOY
  (categorías de ciclo corto, sin acceso bloqueado).
- Tres techos con argumentos: conservative (prob base), realistic (prob
  post-plan completo) y optimistic (realista + accesos desbloqueados).
  El digest presenta primero el optimista, siempre respaldado por datos
  reales del Success Rate Engine.
- La meta diaria es configurable y persistente (UnifiedMemoryStore); sin meta
  configurada el plan reporta el techo realista, nunca inventa un número.
- Toda sección es defensiva: un motor caído no rompe el plan.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar

T = TypeVar("T")

MAX_ITEMS: int = 10
MAX_ACTIONS: int = 5
MAX_NOTES: int = 4

# Meta diaria por defecto: sin meta configurada → el plan reporta el techo realista.
DEFAULT_DAILY_TARGET: float = 0.0
TARGET_MEMORY_NAMESPACE: str = "user"
TARGET_MEMORY_KEY: str = "daily_income_target"

# Factor de velocidad de cobro por categoría (1.0 = se cobra en días,
# 0.25 = cola de revisión de semanas/meses). Derivado de cómo paga realmente
# cada categoría; nunca promete plazos exactos.
CASH_SPEED_FACTORS: dict[str, float] = {
    "data_annotation": 1.0,
    "ai_training": 1.0,
    "ai_evaluation": 1.0,
    "synthetic_data": 1.0,
    "fiverr": 0.9,
    "web_scraping": 0.85,
    "prompt_engineering": 0.85,
    "qa_automation": 0.85,
    "browser_automation": 0.85,
    "dev_bounty": 0.7,
    "oss_bounties": 0.7,
    "open_source": 0.7,
    "software_engineering": 0.7,
    "backend": 0.7,
    "frontend": 0.7,
    "full_stack": 0.7,
    "devops": 0.7,
    "cloud": 0.7,
    "infrastructure": 0.7,
    "mobile_development": 0.7,
    "desktop_development": 0.7,
    "api_development": 0.7,
    "sdk_development": 0.7,
    "data_engineering": 0.7,
    "ai_engineering": 0.7,
    "ml_engineering": 0.7,
    "llm_engineering": 0.7,
    "technical_writing": 0.7,
    "documentation": 0.7,
    "code_review": 0.7,
    "digital_product": 0.7,
    "game_dev": 0.6,
    "game_development": 0.6,
    "embedded": 0.6,
    "iot": 0.6,
    "security_research": 0.4,
    "reverse_engineering": 0.4,
    "malware_analysis": 0.4,
    "blockchain_development": 0.4,
    "smart_contracts": 0.4,
    "hackathon": 0.3,
    "bug_bounty": 0.25,
    "competition": 0.25,
    "competitions": 0.25,
    "general": 0.5,
}
DEFAULT_CASH_SPEED: float = 0.5

# Ventanas de cobro derivadas de la velocidad: qué se puede cobrar HOY.
WINDOW_TODAY: tuple[str, ...] = ("hoy",)
_WINDOW_SPEED_HOY: float = 0.85


def _safe(fn: Callable[[], T], default: T) -> T:
    """Degradación defensiva: un motor caído nunca rompe el plan."""
    try:
        return fn()
    except Exception:
        return default


@dataclass
class MaxDailyItem:
    platform: str
    title: str
    category: str
    reward: float
    acceptance_probability: float
    probability_base: float
    probability_full: float
    cash_speed: float
    cash_window: str
    expected_value_usd: float
    hours_estimate: float
    blocked: bool
    direct_link: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "title": self.title,
            "category": self.category,
            "reward": self.reward,
            "acceptance_probability": self.acceptance_probability,
            "probability_base": self.probability_base,
            "probability_full": self.probability_full,
            "cash_speed": self.cash_speed,
            "cash_window": self.cash_window,
            "expected_value_usd": self.expected_value_usd,
            "hours_estimate": self.hours_estimate,
            "blocked": self.blocked,
            "direct_link": self.direct_link,
        }


@dataclass
class MaxDailyIncomePlan:
    generated_at: str
    daily_target_usd: float
    conservative_max_usd: float
    realistic_max_usd: float
    optimistic_max_usd: float
    unlock_potential_usd: float
    gap_usd: float
    optimism_arguments: list[str] = field(default_factory=list)
    items: list[MaxDailyItem] = field(default_factory=list)
    needs_access_count: int = 0
    actions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    digest: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "daily_target_usd": self.daily_target_usd,
            "conservative_max_usd": self.conservative_max_usd,
            "realistic_max_usd": self.realistic_max_usd,
            "optimistic_max_usd": self.optimistic_max_usd,
            "unlock_potential_usd": self.unlock_potential_usd,
            "gap_usd": self.gap_usd,
            "optimism_arguments": self.optimism_arguments,
            "items": [i.to_dict() for i in self.items],
            "needs_access_count": self.needs_access_count,
            "actions": self.actions,
            "notes": self.notes,
            "digest": self.digest,
        }


class MaxDailyIncomeEngine:
    """Rankea los trabajos del banco por probabilidad real de cobrar HOY.

    Tres techos, siempre respaldados por el Success Rate Engine (optimismo con
    argumentos, no humo):
    - conservative: prob base, sin ejecutar el plan completo.
    - realistic: prob post-plan (`probability_after_full_plan`).
    - optimistic: realista + desbloquear los trabajos bloqueados por acceso.
    """

    def plan(
        self, opportunities: list[dict[str, Any]] | None = None, daily_target_usd: float | None = None
    ) -> dict[str, Any]:
        from cores.direct_work_engine.cashflow_radar import _estimate_hours, _to_float
        from cores.direct_work_engine.execution_planner import plan_execution
        from cores.direct_work_engine.success_engine import plan_opportunity_success

        items = opportunities if opportunities is not None else _workbank_items()
        target = daily_target_usd if daily_target_usd is not None else _load_target()

        ranked: list[MaxDailyItem] = []
        for opp in items:
            item = self._score_item(opp, plan_opportunity_success, plan_execution, _estimate_hours, _to_float)
            if item is not None:
                ranked.append(item)

        ranked.sort(key=lambda i: i.expected_value_usd, reverse=True)

        today = [i for i in ranked if i.cash_window in WINDOW_TODAY]
        conservative = round(sum(i.reward * i.probability_base * i.cash_speed for i in today if not i.blocked), 2)
        realistic = round(sum(i.expected_value_usd for i in today if not i.blocked), 2)
        unlock = round(sum(i.expected_value_usd for i in today if i.blocked), 2)
        optimistic = round(realistic + unlock, 2)
        gap = round(max(0.0, target - optimistic), 2)

        plan = MaxDailyIncomePlan(
            generated_at=datetime.now(UTC).isoformat(),
            daily_target_usd=round(target, 2),
            conservative_max_usd=conservative,
            realistic_max_usd=realistic,
            optimistic_max_usd=optimistic,
            unlock_potential_usd=unlock,
            gap_usd=gap,
            items=ranked[:MAX_ITEMS],
            needs_access_count=sum(1 for i in ranked if i.blocked),
        )
        plan.optimism_arguments = self._optimism_arguments(plan, ranked)
        plan.actions = self._actions(plan, ranked)
        plan.notes = self._notes(plan)
        plan.digest = self.digest(plan.to_dict())
        return plan.to_dict()

    @staticmethod
    def _score_item(
        opp: dict[str, Any],
        plan_opportunity_success: Callable[[dict[str, Any]], dict[str, Any]],
        plan_execution: Callable[[dict[str, Any]], Any],
        _estimate_hours: Callable[..., float],
        _to_float: Callable[[Any], float],
    ) -> MaxDailyItem | None:
        try:
            category = str(opp.get("category", "") or "general")
            reward = _to_float(opp.get("reward"))
            if reward <= 0:
                return None

            success = _safe(lambda: plan_opportunity_success(opp), {})
            prediction = success.get("prediction", {}) or {}
            probability_base = float(prediction.get("probability", 0.0) or 0.0)
            probability_full = float(prediction.get("probability_after_full_plan", 0.0) or probability_base)
            speed = CASH_SPEED_FACTORS.get(category, DEFAULT_CASH_SPEED)

            hours = 0.5
            plan = _safe(lambda: plan_execution(opp), None)
            if plan is not None:
                plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else plan
                hours = _estimate_hours(opp, _to_float(plan_dict.get("human_work_minutes")), category)

            ev = round(reward * probability_full * speed, 2)
            window = "hoy" if speed >= _WINDOW_SPEED_HOY else ("semana" if speed >= 0.6 else "colas")
            blocked = bool(opp.get("needs_access", False))
            link = str(opp.get("direct_link") or opp.get("url") or "")
            return MaxDailyItem(
                platform=str(opp.get("platform", "")),
                title=str(opp.get("title", "")),
                category=category,
                reward=reward,
                acceptance_probability=round(probability_full, 3),
                probability_base=round(probability_base, 3),
                probability_full=round(probability_full, 3),
                cash_speed=speed,
                cash_window=window,
                expected_value_usd=ev,
                hours_estimate=hours,
                blocked=blocked,
                direct_link=link,
            )
        except Exception:
            return None

    @staticmethod
    def _optimism_arguments(plan: MaxDailyIncomePlan, all_items: list[MaxDailyItem]) -> list[str]:
        arguments: list[str] = []
        today_unblocked = [i for i in all_items if i.cash_window in WINDOW_TODAY and not i.blocked]
        if today_unblocked:
            categories: dict[str, list[MaxDailyItem]] = {}
            for item in today_unblocked:
                categories.setdefault(item.category, []).append(item)
            for category, group in sorted(categories.items(), key=lambda kv: -sum(i.expected_value_usd for i in kv[1]))[
                :3
            ]:
                avg_prob = round(sum(i.probability_full for i in group) / len(group) * 100)
                total_ev = round(sum(i.expected_value_usd for i in group), 2)
                arguments.append(
                    f"{len(group)} trabajos de {category} cobrables hoy: {avg_prob}% de aceptación post-plan "
                    f"→ techo de ${total_ev}"
                )
            boosted = [i for i in today_unblocked if i.probability_full > i.probability_base + 0.01]
            if boosted:
                max_gain = max(i.probability_full - i.probability_base for i in boosted)
                arguments.append(
                    f"ejecutar el plan completo eleva la aceptación hasta +{max_gain * 100:.0f} puntos "
                    f"(boost verificado del Success Rate Engine)"
                )
        if plan.unlock_potential_usd > 0:
            arguments.append(
                f"desbloquear {plan.needs_access_count} accesos suma ${plan.unlock_potential_usd} al techo diario"
            )
        if plan.daily_target_usd > 0 and plan.optimistic_max_usd >= plan.daily_target_usd:
            arguments.append(f"la meta de ${plan.daily_target_usd}/día es alcanzable con el techo optimista")
        return arguments[:MAX_ITEMS]

    def _actions(self, plan: MaxDailyIncomePlan, all_items: list[MaxDailyItem]) -> list[str]:
        actions: list[str] = []
        today_items = [i for i in all_items if i.cash_window in WINDOW_TODAY and not i.blocked]
        if today_items:
            actions.append(f"entregar hoy: {today_items[0].platform} — {today_items[0].title[:50]}")
        if plan.unlock_potential_usd > 0:
            actions.append(
                f"configurar accesos de {plan.needs_access_count} trabajos bloqueados "
                f"(suma ${plan.unlock_potential_usd} al techo diario)"
            )
        if plan.gap_usd > 0:
            actions.append(
                "la meta supera el techo optimista: correr work_bank_daily_cycle para más trabajo de ciclo corto"
            )
        return actions[:MAX_ACTIONS]

    def _notes(self, plan: MaxDailyIncomePlan) -> list[str]:
        notes = [
            "techo optimista = desbloquear todos los accesos + ejecutar cada entrega con el plan completo",
            "los bounties de alta recompensa (bug_bounty) aportan hits, no liquidez diaria",
        ]
        if plan.daily_target_usd <= 0:
            notes.append("sin meta diaria configurada: fijala para que el plan mida el gap")
        if plan.realistic_max_usd == 0:
            notes.append("sin trabajo cobrable hoy: primero configurar accesos y correr el ciclo del banco")
        return notes[:MAX_NOTES]

    @staticmethod
    def digest(plan: dict[str, Any]) -> dict[str, str]:
        lines = ["OWNEX MAX DAILY INCOME", ""]
        lines.append(f"Daily target: ${plan['daily_target_usd']}")
        lines.append(f"Optimistic ceiling: ${plan['optimistic_max_usd']} (accesos desbloqueados + plan completo)")
        lines.append(f"Realistic ceiling: ${plan['realistic_max_usd']} (con lo preparado hoy)")
        lines.append(f"Conservative floor: ${plan['conservative_max_usd']} (sin plan de ejecución)")
        if plan["optimism_arguments"]:
            lines.append("")
            lines.append("Argumentos de optimismo:")
            for argument in plan["optimism_arguments"]:
                lines.append(f"- {argument}")
        lines.append("")
        top = plan["items"][0] if plan["items"] else None
        if top is not None:
            lines.append(
                f"Top pick: {top['title'][:60]} | ${top['expected_value_usd']} EV "
                f"({top['cash_window']}, {top['acceptance_probability'] * 100:.0f}% aceptación post-plan)"
            )
        else:
            lines.append("Top pick: ninguno — no hay trabajo cobrable preparado")
        if plan["gap_usd"] > 0:
            lines.append(f"Gap vs meta: ${plan['gap_usd']} (requiere más fuentes de ciclo corto)")
        for action in plan["actions"]:
            lines.append(f"- {action}")
        return {"text": "\n".join(lines)}


# ── helpers ───────────────────────────────────────────────────


def _workbank_items() -> list[dict[str, Any]]:
    from cores.direct_work_engine.workbank import get_workbank

    return [i.to_dict() for i in get_workbank().best_ready(limit=200)]


def _load_target() -> float:
    def _read() -> float:
        from core.memory.store import get_memory_store

        entry = get_memory_store().get(TARGET_MEMORY_NAMESPACE, TARGET_MEMORY_KEY)
        if not entry:
            return DEFAULT_DAILY_TARGET
        return float(entry.get("content", 0.0) or 0.0)

    try:
        return _safe(_read, DEFAULT_DAILY_TARGET)
    except Exception:
        return DEFAULT_DAILY_TARGET


def _save_target(daily_target_usd: float) -> None:
    if daily_target_usd <= 0:
        return
    try:
        from core.memory.store import get_memory_store

        get_memory_store().store(
            namespace=TARGET_MEMORY_NAMESPACE,
            key=TARGET_MEMORY_KEY,
            content=str(daily_target_usd),
            tags=["income", "target"],
            priority=2.0,
        )
    except Exception:
        pass


def get_max_daily_plan(
    opportunities: list[dict[str, Any]] | None = None,
    daily_target_usd: float | None = None,
) -> dict[str, Any]:
    """Public entry point: OWNEX MAX DAILY INCOME plan (data + digest)."""
    if daily_target_usd is not None and daily_target_usd > 0:
        _save_target(daily_target_usd)
    return MaxDailyIncomeEngine().plan(opportunities=opportunities, daily_target_usd=daily_target_usd)
