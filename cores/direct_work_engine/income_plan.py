"""Unified Income Plan — fusiona los dos planes de ingreso de OWNEX en una cola.

Dos vías complementarias, no reemplazo:

- **Track ACTIVO** (resultado entregado): First-Day Guide + Work Bank —
  primer cobro potencial en días (dev bounty micro, bug bounty Level S).
- **Track PASIVO** (AI-training): Application Assistant — postulaciones a
  Outlier/Mercor/Alignerr/Mindrift/Fiverr corren en paralelo mientras esperás
  aprobaciones; ingreso estable semanal cuando aprueban.

Ordenamiento (corrección 2026-08-25, spec "Zero Experience ≠ Zero Barrier"):

Las acciones se rankean por **dinero esperado por hora de intervención
humana**, con regla bootstrap: mientras NINGÚN stream esté aprobado, la
acción que desbloquea el stream con mejor tarifa documentada gana (valor-de-
opción: un assessment de ~90 min abre $8–40/h recurrentes). Una entrega
lista del Work Bank siempre gana (plata sobre la mesa).

Honestidad económica: las tasas provienen del catálogo curado
(``find_curated_entry_model``, source="platform"); los rangos de bounties
del First-Day Guide están documentados en la propia guía; NUNCA se inventan
probabilidades de aceptación ni disponibilidad — se etiquetan desconocidas.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from cores.direct_work_engine.availability import get_available_hours
from cores.opportunity.global_sources import find_curated_entry_model
from cores.result_based import FirstDayGuide

logger = logging.getLogger("cores.direct_work_engine.income_plan")

_TERMINAL_APP_STATUS = frozenset({"accepted", "rejected", "paused"})
_ACCEPTED_STATUS = frozenset({"accepted"})

_SOURCE_DELIVER = "workbank"
_SOURCE_FIRST_DAY = "first_day"
_SOURCE_APPLICATIONS = "applications"

# Payoff documentado en la propia First-Day Guide para dev-bounty micro.
_FD_PAYOFF_LOW, _FD_PAYOFF_HIGH = 50.0, 150.0


class UnifiedIncomePlan:
    """Compone First-Day Guide + Application Assistant + Work Bank en un plan."""

    def __init__(
        self,
        assistant: Any | None = None,
        first_day: FirstDayGuide | None = None,
        bank: Any | None = None,
    ) -> None:
        self._assistant = assistant
        self._first_day = first_day
        self._bank = bank

    # ── API pública ──

    def build(self) -> dict[str, Any]:
        assistant, first_day, bank = self._engines()

        apps_overview = assistant.overview()
        apps_plan = assistant.get_plan()
        guide = first_day.guidance()
        fd_progress = first_day.progress()
        ready_items = [i.to_dict() for i in bank.best_ready(3)]
        wb_progress = bank.progress()

        done_fd = set(fd_progress["completed_steps"])
        fd_pending = [s for s in guide["steps"] if s["step"] not in done_fd]

        accepted_keys = {p["key"] for p in apps_plan["platforms"] if p["status"] in _ACCEPTED_STATUS}
        waiting = self._waiting_platforms(apps_plan)

        deliver_actions = [self._deliver_action(item) for item in ready_items]
        fd_actions = [self._fd_action(s) for s in fd_pending]
        app_actions, bootstrap = self._app_actions(apps_overview.get("next_action"), apps_plan, accepted_keys)

        ranked = self._rank(deliver_actions, fd_actions, app_actions, bootstrap, bool(accepted_keys))
        next_action = ranked[0] if ranked else None

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "philosophy": (
                "Vía activa (resultado entregado) para caja rápida; vía pasiva "
                "(postulaciones AI-training) en paralelo para ingreso estable. "
                "Acciones ordenadas por dinero esperado por hora humana."
            ),
            "next_action": next_action,
            "phases": {
                "now": self._distinct_sources(ranked, limit=3),
                "this_week": ranked[3:11],
                "waiting": waiting,
            },
            "tracks": {
                "active": {
                    "label": "Resultado entregado (First-Day Guide + Work Bank)",
                    "first_day_progress_pct": fd_progress["pct"],
                    "first_day_completed": fd_progress["completed_steps"],
                    "first_day_total": fd_progress["total_steps"],
                    "workbank_ready_to_deliver": len(ready_items),
                    "workbank_targets": wb_progress,
                },
                "passive": {
                    "label": "Postulaciones AI-training (Application Assistant)",
                    "progress_pct": apps_overview.get("progress_pct", 0),
                    "by_status": apps_overview.get("by_status", {}),
                    "accepted_streams": sorted(accepted_keys),
                },
            },
            "income_command_center": self._command_center(ranked[:3], ready_items, apps_plan, accepted_keys),
        }

    # ── Motores (lazy defaults, injectables para tests) ──

    def _engines(self) -> tuple[Any, FirstDayGuide, Any]:
        assistant = self._assistant
        if assistant is None:
            from core.application_assistant import get_application_assistant

            assistant = get_application_assistant()
        first_day = self._first_day or FirstDayGuide()
        bank = self._bank
        if bank is None:
            from cores.direct_work_engine.workbank import get_workbank

            bank = get_workbank()
        return assistant, first_day, bank

    # ── Constructores de acciones ──

    def _deliver_action(self, item: dict[str, Any]) -> dict[str, Any]:
        reward = float(item.get("reward") or 0.0)
        return {
            "source": _SOURCE_DELIVER,
            "title": f"Entregá: {item['title']}",
            "detail": item.get("description") or "Paquete ready_to_deliver del Work Bank.",
            "url": item.get("url") or None,
            "human_hours": None,
            "ev_per_human_hour_usd": None,
            "payoff_range": {"low": reward, "high": reward},
            "cash_speed_days": None,
            "zero_experience": True,
            "assessment_required": False,
            "access_probability": "desconocida",
            "sort": (0, -reward),
            "item_id": item["id"],
        }

    def _fd_action(self, step: dict[str, Any]) -> dict[str, Any]:
        hours = float(step.get("effort_hours") or 1.0)
        return {
            "source": _SOURCE_FIRST_DAY,
            "title": f"Paso {step['step']}: {step['title']}",
            "detail": step["action"],
            "why": step["why"],
            "url": None,
            "human_hours": hours,
            "ev_per_human_hour_usd": round(_FD_PAYOFF_LOW / hours, 2),  # cota conservadora
            "payoff_range": {"low": _FD_PAYOFF_LOW, "high": _FD_PAYOFF_HIGH},
            "cash_speed_days": None,
            "zero_experience": True,
            "assessment_required": False,
            "access_probability": "desconocida",
            "step_number": step["step"],
        }

    def _app_actions(
        self,
        passive_head: dict[str, Any] | None,
        apps_plan: dict[str, Any],
        accepted_keys: set[str],
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """Construye acciones de postulación + detecta el bootstrap.

        Bootstrap = PRIMERA plataforma en orden de catálogo que sigue sin
        aprobarse y tiene tarifa documentada: su secuencia de entrada se
        completa antes de que plataformas posteriores compitan (el screening
        de una desbloquea SU stream; saltar de plataforma no acelera nada).
        """
        actions: list[dict[str, Any]] = []
        bootstrap: dict[str, Any] | None = None
        bootstrap_key: str | None = None

        for platform in apps_plan["platforms"]:
            if platform["status"] in _TERMINAL_APP_STATUS or platform["key"] in accepted_keys:
                continue
            facts = find_curated_entry_model(platform["key"])
            if facts and facts.get("hourly_rate_usd"):
                bootstrap_key = platform["key"]
            break

        for head in actions_sorted_by_catalog(self._platform_heads(passive_head, apps_plan)):
            facts = find_curated_entry_model(head["platform_key"])
            rate = float(facts["hourly_rate_usd"]) if facts and facts.get("hourly_rate_usd") else None
            tt_first_work = (
                float(facts["time_to_first_work_hours"]) if facts and facts.get("time_to_first_work_hours") else None
            )
            cash_days = int(facts["payout_cadence_days"]) if facts and facts.get("payout_cadence_days") else None
            unlocks = head["platform_key"] not in accepted_keys
            minutes = head.pop("est_minutes", None)
            human_hours = tt_first_work if _is_entry_step(head) else (round(minutes / 60.0, 2) if minutes else None)
            action = {
                **head,
                "human_hours": human_hours,
                "ev_per_human_hour_usd": rate,
                "rate_source": (facts or {}).get("rate_source", "unknown") if rate else "unknown",
                "payoff_range": None,
                "cash_speed_days": cash_days,
                "zero_experience": True,
                "assessment_required": bool(facts and facts.get("assessment")) and _is_entry_step(head),
                "access_probability": "desconocida",
                "unlocks_stream": (
                    {"hourly_rate_usd": rate, "cash_speed_days": cash_days} if unlocks and rate else None
                ),
            }
            actions.append(action)
            if bootstrap is None and bootstrap_key is not None and head["platform_key"] == bootstrap_key:
                bootstrap = action
        return actions, bootstrap

    def _platform_heads(self, passive_head: dict[str, Any] | None, apps_plan: dict[str, Any]) -> list[dict[str, Any]]:
        heads: list[dict[str, Any]] = []
        for platform in apps_plan["platforms"]:
            if platform["status"] in _TERMINAL_APP_STATUS:
                continue
            pending = [s for s in platform["steps"] if not s["done"]]
            if not pending:
                continue
            heads.append(
                {
                    "source": _SOURCE_APPLICATIONS,
                    "title": f"{platform['name']}: {pending[0]['title']}",
                    "detail": pending[0]["detail"],
                    "url": platform["url"],
                    "est_minutes": pending[0].get("est_minutes"),
                    "payoff": platform.get("pay_range", ""),
                    "platform_key": platform["key"],
                    "is_head_of_overview": (
                        passive_head is not None
                        and platform["key"] == passive_head.get("platform")
                        and pending[0]["title"] == passive_head.get("step")
                    ),
                }
            )
        # El head del overview (orden de prioridad del catálogo) primero.
        heads.sort(key=lambda h: not h.pop("is_head_of_overview"))
        return heads

    # ── Ranking ──

    def _rank(
        self,
        deliver: list[dict[str, Any]],
        fd_actions: list[dict[str, Any]],
        app_actions: list[dict[str, Any]],
        bootstrap: dict[str, Any] | None,
        any_stream_accepted: bool,
    ) -> list[dict[str, Any]]:
        """Orden determinista por (tier, -EV/hora conservadora).

        Tier 0: entrega lista (plata sobre la mesa).
        Tier 1: bootstrap — desbloquear el mejor stream documentado mientras
                no haya ninguno aprobado (valor-de-opción del assessment).
        Tier 2: resto por EV/hora descendente (None al final).
        """
        keys: dict[int, tuple[int, float]] = {}
        for a in deliver:
            keys[id(a)] = (0, 0.0)
        for a in app_actions:
            if a is bootstrap and not any_stream_accepted:
                keys[id(a)] = (1, 0.0)
            else:
                ev = a.get("ev_per_human_hour_usd")
                keys[id(a)] = (2, -ev) if ev is not None else (2, float("-inf"))
        for a in fd_actions:
            ev = a.get("ev_per_human_hour_usd")
            keys[id(a)] = (2, -(ev or 0.0))

        pool = [*deliver, *fd_actions, *app_actions]
        pool.sort(key=lambda a: keys[id(a)])
        return pool

    @staticmethod
    def _distinct_sources(ranked: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        """Top-N garantizando diversidad de vías (una por fuente primero)."""
        picked: list[dict[str, Any]] = []
        seen: set[str] = set()
        rest: list[dict[str, Any]] = []
        for action in ranked:
            src = action["source"]
            if src not in seen:
                seen.add(src)
                picked.append(action)
            else:
                rest.append(action)
            if len(picked) >= limit:
                break
        picked.extend(rest[: max(0, limit - len(picked))])
        return picked[:limit]

    def _waiting_platforms(self, apps_plan: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {"key": p["key"], "name": p["name"], "status": p["status"]}
            for p in apps_plan["platforms"]
            if p["status"] in {"applied", "in_review"}
        ]

    # ── Income Command Center (spec §13, §18) ──

    def _command_center(
        self,
        now_actions: list[dict[str, Any]],
        ready_items: list[dict[str, Any]],
        apps_plan: dict[str, Any],
        accepted_keys: set[str],
    ) -> dict[str, Any]:
        def _sum_range(actions: list[dict[str, Any]]) -> tuple[float, float]:
            low = high = 0.0
            for a in actions:
                rng = a.get("payoff_range")
                if rng:
                    low += float(rng["low"])
                    high += float(rng["high"])
            return low, high

        today_low, today_high = _sum_range(now_actions)
        availability = get_available_hours("this_week")

        stream_low = stream_high = 0.0
        stack: list[dict[str, Any]] = []
        for platform in apps_plan["platforms"]:
            facts = find_curated_entry_model(platform["key"])
            rate = float(facts["hourly_rate_usd"]) if facts and facts.get("hourly_rate_usd") else None
            if platform["key"] in accepted_keys and rate is not None:
                stream_low += rate * availability * 0.5
                stream_high += rate * availability
            stack.append(
                {
                    "key": platform["key"],
                    "name": platform["name"],
                    "rate_documented": rate,
                    "status": platform["status"],
                }
            )

        def _proj(multiplier: float, utilization_note: str) -> dict[str, Any]:
            weeks = multiplier
            return {
                "low": round(today_low + stream_low * weeks, 2),
                "high": round(today_high + stream_high * weeks, 2),
            }

        note_streams = (
            f"{len(accepted_keys)} stream(s) aprobado(s); supuesto declarado: "
            "utilización 50%–100% de la disponibilidad configurada"
            if accepted_keys
            else "sin streams aprobados aún — el rango viene solo de acciones concretas"
        )

        return {
            "today": {"low": round(today_low, 2), "high": round(today_high, 2)},
            "week": _proj(1.0, "semana"),
            "fortnight": _proj(2.0, "quincena"),
            "month": _proj(4.33, "mes"),
            "basis": {
                "availability_hours_per_week": availability,
                "note": note_streams,
                "sources": "rates=documented(platform); bounty payoffs=First-Day Guide; sin probabilidades inventadas",
            },
            "active_stack": stack,
            "ready_to_deliver_count": len(ready_items),
        }


def _is_entry_step(action: dict[str, Any]) -> bool:
    """True si el paso pendiente es el gate de entrada (cuenta/assessment)."""
    title = action.get("title", "").lower()
    detail = action.get("detail", "").lower()
    markers = ("crear cuenta", "assessment", "evaluaci", "verificaci", "entrevista", "prueba")
    return any(m in title or m in detail for m in markers)


def actions_sorted_by_catalog(heads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ya vienen ordenados por prioridad de catálogo desde _platform_heads."""
    return heads


def build_unified_income_plan() -> dict[str, Any]:
    """Entrada única para API/scheduler."""
    return UnifiedIncomePlan().build()
