"""Account Health — monitoreo anti-ban de cuentas en plataformas (Outlier/DA/etc).

Riesgo invisible: bans por VPN, calidad de QA, velocidad de submit. OWNEX
guarda estado de cada cuenta, métricas de riesgo y genera alertas con
umbral persistente para actuar antes de perder la fuente.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.account_health")

_DEFAULT_STATE = {
    "accounts": [],
    "alerts": [],
}


class AccountHealth:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/account_health/")
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

    def register_account(self, platform: str, name: str = "") -> dict[str, Any]:
        state = self._load()
        exists = any(a.get("platform") == platform for a in state["accounts"])
        if exists:
            return {"success": False, "message": f"Cuenta {platform} ya registrada."}
        state["accounts"].append(
            {
                "platform": platform,
                "name": name or platform,
                "created_at": datetime.now(UTC).isoformat(),
                "health_score": 100,
                "events": [],
                "notes": "",
            }
        )
        self._save(state)
        return {"success": True, "accounts": len(state["accounts"])}

    def report_event(self, platform: str, event_type: str, detail: str = "", impact: float = 0) -> dict[str, Any]:
        """Registrar un evento que afecta salud: 'qa_fail', 'warn', 'vpn_issue', 'suspend_risk'."""
        state = self._load()
        acc = next((a for a in state["accounts"] if a.get("platform") == platform), None)
        if not acc:
            return {"success": False, "message": f"Cuenta {platform} no registrada."}
        acc.setdefault("events", []).append(
            {
                "type": event_type,
                "detail": detail,
                "impact": impact,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        acc["health_score"] = max(0, min(100, float(acc.get("health_score", 100)) - impact))
        self._save(state)
        return self.get_status(platform=platform)

    def update(self, platform: str, notes: str = "") -> dict[str, Any]:
        state = self._load()
        acc = next((a for a in state["accounts"] if a.get("platform") == platform), None)
        if not acc:
            return {"success": False, "message": "Cuenta no registrada."}
        if notes:
            acc["notes"] = notes
        self._save(state)
        return {"success": True}

    def get_status(self, platform: str = "") -> dict[str, Any]:
        state = self._load()
        accts = state["accounts"]
        if platform:
            accts = [a for a in accts if a.get("platform") == platform]
        alerts = []
        now = datetime.now(UTC)
        for a in accts:
            last_event = (a.get("events") or [{}])[-1]
            try:
                last_dt = datetime.fromisoformat((last_event or {}).get("created_at", "2000-01-01"))
            except Exception:
                last_dt = now
            days = (now - last_dt).days
            score = a.get("health_score", 100)
            if score < 50:
                alerts.append(
                    {"platform": a["platform"], "level": "riesgo alto", "why": f"Health {score}% — pausar y revisar."}
                )
            elif score < 80:
                alerts.append(
                    {
                        "platform": a["platform"],
                        "level": "riesgo medio",
                        "why": f"Health {score}% — revisar eventos recientes.",
                    }
                )
            elif days >= 7:
                alerts.append(
                    {
                        "platform": a["platform"],
                        "level": "riesgo bajo",
                        "why": "Sin eventos recientes pero inactivo 7+ días.",
                    }
                )
        return {"success": True, "accounts": accts, "total": len(accts), "alerts": alerts}


_h: AccountHealth | None = None


def get_account_health() -> AccountHealth:
    global _h
    if _h is None:
        _h = AccountHealth()
    return _h
