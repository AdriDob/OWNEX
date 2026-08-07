"""Plan de plata configurado de OWNEX.

Guarda el perfil del operador (horas/día, prioridades, metas) que consume la
Guía Maestra y Mega Fast Mode para dar planeación real, no genérica.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("core.money_plan")

DEFAULT_PLAN: dict[str, Any] = {
    "hours_per_day": 5,
    "days_per_week": 5,
    "weekly_hours": 25,
    "priority": ["pulse", "forge"],
    "assistant_enabled": True,
    "assistant_efficiency": 0.4,
    "assistant_rate_premium": 0.39,
    "guided_mode": True,
    "guided_priority": "max_success",
    "sources": {
        "pulse": {
            "name": "Outlier / DataAnnotation / Mindrift",
            "type": "rapid",
            "usd_per_hour": 25.0,
            "hours_share": 0.6,
            "description": "Tareas de IA con pago rápido. Base segura. Con asistente: $25/h selectivo.",
        },
        "forge": {
            "name": "Opire / Superteam / Algora",
            "type": "large",
            "usd_each": 200.0,
            "count_per_week": 1,
            "description": "Bounts de código. Pago alto pero más lento.",
        },
        "bugbounty": {
            "name": "HackerOne / Intigriti",
            "type": "lottery",
            "usd_each": 300.0,
            "probability_weekly": 0.15,
            "description": "Probabilístico. Boleto alto.",
        },
    },
    "conservative_weekly": 450.0,
    "realistic_weekly": 720.0,
    "optimistic_weekly": 1000.0,
    "target_weekly": 750.0,
    "target_note": "750/sem (~1500 por quincena): lograble con asistente + tareas premium + constancia. Guiado por OWNEX.",
    "hours_note": "Con 5h/d (~25h/sem): fuente está efectiva realista $600-1000/sem hacia semana 4-6.",
}


class MoneyPlan:
    """Perfil de plata del operador, persistido como JSON."""

    def __init__(self, config_path: str = "") -> None:
        self.config_path = config_path or os.path.expanduser("~/.config/ownex/money_plan.json")
        self._plan = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, encoding="utf-8") as f:
                    saved = json.load(f)
                merged = DEFAULT_PLAN.copy()
                merged.update(saved)
                return merged
        except Exception as e:
            logger.warning("No se pudo leer plan de plata: %s", e)
        return DEFAULT_PLAN.copy()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._plan, f, indent=2, ensure_ascii=False)

    def get(self) -> dict[str, Any]:
        return self._plan

    def update(self, updates: dict[str, Any]) -> dict[str, Any]:
        self._plan.update(updates)
        self._save()
        logger.info("Plan de plata actualizado.")
        return self._plan

    def project_weekly(self) -> dict[str, Any]:
        """Proyecta el ingreso semanal según horas/día y con eficiencia del asistente."""
        plan = self._plan
        hours = plan.get("weekly_hours", 25)
        assistant_on = bool(plan.get("assistant_enabled", True))
        eff = plan.get("assistant_efficiency", 0.4)

        # Pulse: horas share sobre el total, a rate. Con asistente, la tasa sube
        # (selección premium) y la carga real baja.
        pulse = plan.get("sources", {}).get("pulse", {})
        pulse_hours = hours * pulse.get("hours_share", 0.6)
        rate = pulse.get("usd_per_hour", 18)
        if assistant_on:
            rate = rate * (1 + plan.get("assistant_rate_premium", 0.39))
        pulse_income = round(pulse_hours * rate, 0)

        # Forge: count × usd
        forge = plan.get("sources", {}).get("forge", {})
        forge_income = round(forge.get("count_per_week", 1) * forge.get("usd_each", 200), 0)

        # Bug bounty: expectation
        bug = plan.get("sources", {}).get("bugbounty", {})
        bug_income = round(bug.get("usd_each", 300) * bug.get("probability_weekly", 0.15), 0)

        # Carga real de tu parte (solo pulir/refinar con asistente)
        real_hours = hours
        if assistant_on:
            real_hours = round(hours * eff, 1)

        total = pulse_income + forge_income

        return {
            "weekly_hours": hours,
            "real_hours": real_hours,
            "saved_hours": round(hours - real_hours, 1),
            "assistant_enabled": assistant_on,
            "pulse_rate": round(rate, 0),
            "pulse_income": pulse_income,
            "forge_income": forge_income,
            "bug_income_expect": bug_income,
            "total_estimate": total,
            "target_weekly": plan.get("target_weekly", 750),
            "gap_to_target": round(plan.get("target_weekly", 750) - total, 0),
        }


def get_money_plan() -> MoneyPlan:
    global _money_plan
    if _money_plan is None:
        _money_plan = MoneyPlan()
    return _money_plan


_money_plan: MoneyPlan | None = None
