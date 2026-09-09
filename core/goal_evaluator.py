"""Goal Evaluator — decile a OWNEX tu meta y que cruce con el estado real.

Meta: "este mes quiero $100K" o "x5 del mes pasado". OWNEX:
1. Recolecta datos reales (ingresos, plan, capital pool, pipeline, skills, perfil).
2. Calcula qué porciento de la meta es viable hoy y qué faltaría.
3. Descompone por fuente (pulse/forge/bounty/invest) con proyección honesta.
4. Devuelve el plan de acción: qué activar para acercarse.

No promete: evalúa. Y cuando una meta es imposible (100K/mes con 5h/día
y $0 de capital), lo dice claro y da la meta real alcanzable.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("core.goal_evaluator")

MULTIPLIER_MEMORY_MONTHS = 3
_DEFAULT_STATE = {
    "history": [],
    "last_eval": None,
}


class GoalEvaluator:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/goal_evaluator/")
        os.makedirs(self.data_dir, exist_ok=True)

    @property
    def state_path(self) -> str:
        return os.path.join(self.data_dir, "state.json")

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                state = json.load(f)
                for k, v in _DEFAULT_STATE.items():
                    state.setdefault(k, v)
                return state
        except Exception:
            return dict(_DEFAULT_STATE)

    def _save(self, state: dict[str, Any]) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    # ── Recolección de datos reales del sistema ──

    def _real_income_monthly(self) -> dict[str, Any]:
        """Ingresos reales registrados (revenue metrics) y proyección del plan."""
        out = {"income_6mo": [], "last_month_total": 0.0, "avg_monthly": 0.0, "plan_weekly_estimate": 0.0}
        try:
            from core.revenue.metrics import get_metrics

            monthly = get_metrics().monthly_revenue(months=6)
            totals = [m.get("total_usd", 0) for m in monthly]
            out["income_6mo"] = [{"month": m.get("month"), "total_usd": m.get("total_usd", 0)} for m in monthly]
            out["last_month_total"] = totals[-1] if totals else 0.0
            out["avg_monthly"] = round(sum(totals) / len(totals), 2) if totals else 0.0
        except Exception as e:
            out["error"] = str(e)
        try:
            from core.money_plan import get_money_plan

            p = get_money_plan().get()
            out["plan_weekly_estimate"] = p.get("realistic_weekly", 0) or 0
            out["plan_target_weekly"] = p.get("target_weekly", 0)
        except Exception:
            pass
        try:
            from core.capital_bar import get_capital_bar

            up = get_capital_bar().get_status()
            out["capital_pool"] = up.get("pool", 0.0)
            out["capital_monthly_passive"] = up.get("monthly_passive", 0.0)
        except Exception:
            pass
        return out

    def _pipeline_potential(self) -> dict[str, Any]:
        """Potencial de pipelines: bounts listos, activos de ingresos."""
        out = {"bounty_ready": 0, "bounty_estimate": 0.0, "sources": []}
        try:
            from core.dev_bounty_autopilot import get_dev_bounty_autopilot

            a = get_dev_bounty_autopilot()
            ready = a._count_pending_proposals() if hasattr(a, "_count_pending_proposals") else 0
            out["bounty_ready"] = ready
            # Estimado conservador por bounty cerrado
            out["bounty_estimate"] = round(ready * 200.0, 2)
        except Exception:
            pass
        try:
            from core.money_plan import get_money_plan

            p = get_money_plan().get()
            for src in p.get("sources", {}).values():
                out["sources"].append(
                    {
                        "name": src.get("name", ""),
                        "type": src.get("type", ""),
                        "monthly_est": self._source_monthly_est(src),
                    }
                )
        except Exception:
            pass
        return out

    def _source_monthly_est(self, src: dict[str, Any]) -> float:
        t = src.get("type", "")
        if t == "rapid":
            hours = float(src.get("hours_share", 0.6)) * 25
            return round(hours * float(src.get("usd_per_hour", 25)), 2)
        if t == "large":
            return round(float(src.get("usd_each", 0)) * float(src.get("count_per_week", 0)) * 4.3, 2)
        if t == "lottery":
            return round(float(src.get("usd_each", 0)) * float(src.get("probability_weekly", 0)) * 4.3, 2)
        return 0.0

    def _readiness(self) -> dict[str, Any]:
        out = {}
        try:
            from core.profile_builder import get_profile_builder

            pb = get_profile_builder().get_status()
            out["profile_score"] = pb.get("score", 0)
        except Exception:
            out["profile_score"] = 0
        try:
            from core.skill_method import get_skill_method

            sm = get_skill_method().get_status()
            out["skill_score"] = sm.get("score", 0)
        except Exception:
            out["skill_score"] = 0
        try:
            from core.vpn_assistant import get_vpn_assistant

            out["vpn_ready"] = get_vpn_assistant().readiness_report().get("ready", False)
        except Exception:
            out["vpn_ready"] = False
        return out

    # ── Eval ──

    def evaluate(self, goal_type: str = "monthly", amount: float = 0, multiplier: float = 0) -> dict[str, Any]:
        data = self._real_income_monthly()
        pipe = self._pipeline_potential()
        read = self._readiness()

        last_month = data.get("last_month_total", 0) or 0
        avg_monthly = data.get("avg_monthly", 0) or 0

        if goal_type == "multiplier" and multiplier > 0:
            target = round(last_month * multiplier, 2) if last_month else 0
        else:
            target = round(float(amount), 2)

        # Proyección realista del mes (fuentes activas + pipelines)
        plan_monthly = (data.get("plan_weekly_estimate", 0) or 0) * 4.3
        realistic_projection = round(plan_monthly + pipe.get("bounty_estimate", 0) + data.get("monthly_passive", 0), 2)

        feasible = realistic_projection >= target or target <= 0
        multiple = round(target / realistic_projection, 2) if realistic_projection > 0 else 0

        if target <= 0:
            verdict = "Sin meta calculable: registrá ingresos o definí un monto."
            status = "nodata"
        elif feasible:
            verdict = "Meta alcanzable con el estado actual — ejecutá el plan."
            status = "on_track"
        elif multiple <= 3:
            verdict = f"Meta alta pero alcanzable este mes con ejecución + pipelines (~{multiple}x lo realista)."
            status = "possible"
        elif multiple <= 10:
            verdict = "Meta agresiva: requiere un golpe de suerte/multiplicador (bug grande, jackpot, producto)."
            status = "ambitious"
        else:
            verdict = (
                "Meta fuera de rango real este mes con los datos actuales. Ruta: multiplicar capital y skill primero."
            )
            status = "unrealistic"

        gaps = self._gap_actions(target, realistic_projection, data, pipe, read)
        breakdown = [
            {
                "name": "Plan base (plata/horas)",
                "monthly_est": round(plan_monthly, 2),
                "note": "Fuente rápida + bounts del plan de plata",
            },
            {
                "name": "Bounts por cerrar",
                "monthly_est": pipe.get("bounty_estimate", 0),
                "note": f"{pipe.get('bounty_ready', 0)} listos en cola",
            },
            {
                "name": "Pasivo capital",
                "monthly_est": data.get("monthly_passive", 0),
                "note": f"pool actual ${data.get('capital_pool', 0)}",
            },
        ]

        result = {
            "success": True,
            "goal": {
                "type": goal_type,
                "amount": target,
                "multiplier": multiplier if goal_type == "multiplier" else 0,
            },
            "context": {
                "last_month": last_month,
                "avg_monthly": avg_monthly,
                "plan_monthly_projection": round(plan_monthly, 2),
                "pool_capital": data.get("capital_pool", 0),
            },
            "evaluation": {
                "status": status,
                "verdict": verdict,
                "realistic_projection": realistic_projection,
                "feasible": feasible,
                "multiple_to_target": multiple,
            },
            "breakdown": breakdown,
            "gaps": gaps,
        }

        # Persistir historial de evaluaciones
        try:
            st = self._load()
            st["last_eval"] = result
            st["history"] = (st.get("history") or [])[-10:] + [result]
            self._save(st)
        except Exception:
            pass
        return result

    def _real_income_data(self) -> dict[str, Any]:
        return self._real_income_monthly()

    def _gap_actions(self, target: float, proj: float, data: dict, pipe: dict, read: dict) -> list[dict[str, Any]]:
        gaps = []
        deficit = target - proj
        if deficit > 0:
            gaps.append(
                {
                    "label": "Ejecutar más bounts de mayor valor",
                    "why": f"Cada bounty tipo large suma ~$200. Necesitás ~{max(1, round(deficit / 200))} más este mes.",
                    "priority": "alta",
                }
            )
        if read.get("vpn_ready") is False:
            gaps.append(
                {
                    "label": "Instalar VPN",
                    "why": "Desbloquea Outlier/DA (la fuente base más rápida).",
                    "priority": "alta",
                }
            )
        if (read.get("skill_score") or 0) < 50 and target > 5000:
            gaps.append(
                {
                    "label": "Subir Skill Method",
                    "why": "Los pagos grandes (bug bounty) exigen skill técnico.",
                    "priority": "media",
                }
            )
        if (data.get("capital_pool") or 0) < 10000 and target > proj * 5:
            gaps.append(
                {
                    "label": "Capital no cubre el pasivo",
                    "why": "Para ese target se necesita capital, no solo horas.",
                    "priority": "media",
                }
            )
        return gaps[:4]

    def get_status(self) -> dict[str, Any]:
        state = self._load()
        last = state.get("last_eval", None)
        return {"success": True, "last_eval": last, "history": state.get("history", [])[-5:]}


_eval: GoalEvaluator | None = None


def get_goal_evaluator() -> GoalEvaluator:
    global _eval
    if _eval is None:
        _eval = GoalEvaluator()
    return _eval
