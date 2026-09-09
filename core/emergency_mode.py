"""Emergency Mode — playbook de contingencia cuando el mes va mal.

El Goal Evaluator dice "no llegás", pero falta el "y qué hago". Este
módulo, al ser consultado, analiza el estado real (proyección vs meta,
bounts pendientes, horas trabajadas, salud de cuentas) y devuelve un
plan de emergencia con acciones concretas ordenadas por impacto.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.emergency_mode")

_ACTIONS = {
    "bounts": {
        "title": "Cerrar bounts pendientes HOY",
        "impact": "alta",
        "why": "Cada bounty tipo large ≈ $200-500. Es la fuente más rápida de activar.",
    },
    "vpn": {
        "title": "Desbloquear VPN + Pulse",
        "impact": "alta",
        "why": "Sin VPN no hay Outlier/DA: tu base segura de $20-30/h.",
    },
    "freelance": {
        "title": "Tomar 1-2 trabajos freelance urgentes",
        "impact": "media",
        "why": "Cliente puntual = pago en 3-7 días si ya tenés método de cobro.",
    },
    "writeups": {
        "title": "Publicar 1 write-up esta semana",
        "impact": "media",
        "why": "Multiplica invitaciones privadas y perfil; paga a mediano plazo.",
    },
    "capital": {
        "title": "No mover capital de riesgo este mes",
        "impact": "media",
        "why": "En mes malo, el capital líquido es tu colchón; no lo arriesgues.",
    },
    "bajar_meta": {
        "title": "Re-encuadrar la meta del mes",
        "impact": "baja",
        "why": "Meta imposible = presión. Meta real = ejecución.",
    },
}

_DEFAULT_STATE = {
    "triggered_at": None,
    "last_verdict": "",
    "plans": [],
}


class EmergencyMode:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/emergency_mode/")
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

    def analyze(self, target_monthly: float = 0, goal_type: str = "monthly") -> dict[str, Any]:
        # Recolección de señales reales
        proj = 0.0
        bount_pending = 0
        hours_7d = 0.0
        vpn_ready = False
        try:
            from core.goal_evaluator import get_goal_evaluator

            r = get_goal_evaluator().evaluate(goal_type=goal_type, amount=target_monthly)
            proj = float(r["evaluation"]["realistic_projection"])
        except Exception:
            pass
        try:
            from core.dev_bounty_autopilot import get_dev_bounty_autopilot

            bount_pending = get_dev_bounty_autopilot()._count_pending_proposals()
        except Exception:
            pass
        try:
            from core.work_log import get_work_log

            hours_7d = get_work_log().get_status().get("hours_7d", 0)
        except Exception:
            pass
        try:
            from core.vpn_assistant import get_vpn_assistant

            vpn_ready = get_vpn_assistant().readiness_report().get("ready", False)
        except Exception:
            pass

        gap = max(0.0, target_monthly - proj)
        level = "normal"
        if target_monthly <= 0:
            level = "info"
        elif gap / max(1.0, target_monthly) > 0.5:
            level = "critical"
        elif gap > 0:
            level = "warning"

        plan = []
        if level in ("warning", "critical"):
            plan.append({**_ACTIONS["bounts"], "detail": f"{bount_pending} listos en cola"})
            if not vpn_ready:
                plan.append({**_ACTIONS["vpn"], "detail": "Instalar y conectar"})
            if hours_7d < 10:
                plan.append({**_ACTIONS["writeups"], "detail": f"{hours_7d}h en la semana"})
            plan.append({**_ACTIONS["capital"]})
            if level == "critical":
                plan.append({**_ACTIONS["bajar_meta"], "detail": f"Proyección $ {round(proj)}"})

        verdict = {
            "info": "Sin meta definida: poné una para que OWNEX sepa si hay emergencia.",
            "normal": "Vas bien: la meta es alcanzable con la proyección actual.",
            "warning": "Riesgo de no llegar: ejecutá el plan de acción abajo.",
            "critical": "EMERGENCIA: no llegás con lo actual. Plan agresivo abajo.",
        }[level]

        state = self._load()
        state["last_verdict"] = verdict
        state["triggered_at"] = state.get("triggered_at") or datetime.now(UTC).isoformat()
        state["plans"] = plan
        self._save(state)
        return {
            "success": True,
            "level": level,
            "verdict": verdict,
            "projection": round(proj, 2),
            "gap": round(gap, 2),
            "plan": plan,
            "signals": {"bount_pending": bount_pending, "hours_7d": hours_7d, "vpn_ready": vpn_ready},
            "triggered_at": state.get("triggered_at"),
        }

    def get_status(self) -> dict[str, Any]:
        state = self._load()
        return {"success": True, "last": state.get("last_verdict"), "triggered_at": state.get("triggered_at")}


_em: EmergencyMode | None = None


def get_emergency_mode() -> EmergencyMode:
    global _em
    if _em is None:
        _em = EmergencyMode()
    return _em
