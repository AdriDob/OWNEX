"""Work Log — registro de sesiones de trabajo reales (tiempo + foco + energía).

OwnEX usa datos verdaderos de lo que el operador hace, no suposiciones.
Cada sesión guarda: fecha, horas, foco (bounty/skill/pulse), plataforma,
momentum (1-5). Con el acumulado el Goal Evaluator y el Daily Board
tienen un "input real" de cuánto se trabaja y qué rinde.

Persistencia: ~/.config/ownex/work_log/state.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.work_log")

FOCO_OPTIONS = ["bounty", "skill", "pulse", "recon", "writeup", "setup", "otro"]

_DEFAULT_STATE = {
    "sessions": [],
    "started_on": None,
}


class WorkLog:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/work_log/")
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

    def register_session(
        self, hours: float, foco: str = "bounty", detail: str = "", momentum: int = 5
    ) -> dict[str, Any]:
        hours = float(hours)
        if hours <= 0 or hours > 24:
            return {"success": False, "message": "Horas inválidas (0-24)."}
        if foco not in FOCO_OPTIONS:
            return {"success": False, "message": f"Foco inválido. Opciones: {', '.join(FOCO_OPTIONS)}"}
        momentum = max(1, min(10, int(momentum)))

        state = self._load()
        state["started_on"] = state.get("started_on") or datetime.now(UTC).isoformat()
        now = datetime.now(UTC)
        entry = {
            "id": f"wrk-{int(now.timestamp() * 1000)}",
            "hours": round(hours, 2),
            "foco": foco,
            "detail": detail.strip(),
            "momentum": momentum,
            "created_at": now.isoformat(),
        }
        state["sessions"].append(entry)
        self._save(state)
        return {"success": True, "entry": entry, "total": len(state["sessions"])}

    def get_status(self) -> dict[str, Any]:
        state = self._load()
        sessiones = state.get("sessions", [])
        recent = sessiones[-30:]
        total_hours = round(sum(s["hours"] for s in sessiones), 2)
        hours_7d = round(
            sum(s["hours"] for s in sessiones if (datetime.now(UTC) - self._parse(s.get("created_at", ""))).days <= 7),
            2,
        )
        hours_30d = round(
            sum(s["hours"] for s in sessiones if (datetime.now(UTC) - self._parse(s.get("created_at", ""))).days <= 30),
            2,
        )
        by_foco: dict[str, float] = {}
        for s in sessiones:
            by_foco[s.get("foco", "otro")] = by_foco.get(s.get("foco", "otro"), 0) + s["hours"]
        avg_momentum = round(sum(s.get("momentum", 0) for s in recent) / len(recent), 1) if recent else 0
        return {
            "success": True,
            "sessions": sessiones[-10:][::-1],
            "total_sessions": len(sessiones),
            "total_hours": total_hours,
            "hours_7d": hours_7d,
            "hours_30d": hours_30d,
            "by_foco": by_foco,
            "avg_momentum": avg_momentum,
            "foco_options": FOCO_OPTIONS,
            "started_on": state.get("started_on"),
            "message": self._message(hours_7d),
        }

    def _message(self, hours_7d: float) -> str:
        if hours_7d < 5:
            return "Menos de 5h en la última semana: menos input real = menos proyección real."
        if hours_7d < 20:
            return "Buen ritmo semanal. Cargá sesiones todos los días para datos reales."
        return "Ritmo sólido (20h+/sem). Tus proyecciones ya usan horas verdaderas."

    @staticmethod
    def _parse(iso: str) -> datetime:
        try:
            return datetime.fromisoformat(iso)
        except Exception:
            return datetime.min.replace(tzinfo=UTC)


_wl: WorkLog | None = None


def get_work_log() -> WorkLog:
    global _wl
    if _wl is None:
        _wl = WorkLog()
    return _wl
