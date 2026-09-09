"""Capital Bar — acumulación automática del capital y umbrales pasivos.

Cada payout/ingreso registrado alimenta un "pool de capital" con un % configurable
(feed ratio). El Capital Bar muestra cuánto falta para cada umbral que habilita
modalidad pasiva (DeFi, vault, trading) y proyecta cuándo se alcanza con el
ingreso actual. Persistencia: ~/.config/ownex/capital_bar/state.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.capital_bar")

THRESHOLDS = [
    {"key": "seed", "name": "Seed (arranque DeFi)", "amount": 1000.0, "mode": "Yield de bajo riesgo abierto"},
    {"key": "snowball", "name": "Bola de nieve", "amount": 5000.0, "mode": "Vault + trading con alocador"},
    {"key": "passive", "name": "Capital pasivo", "amount": 25000.0, "mode": "Pasivos + productos + 1 mes tranquilo"},
    {"key": "elite", "name": "Escala elite", "amount": 100000.0, "mode": "Base real de $100K/mes sostenidos"},
]

DEFAULT_PASSIVE_YIELD = {
    500: 0.015,
    5000: 0.025,
    25000: 0.035,
    100000: 0.04,
}

_DEFAULT_STATE = {
    "feed_ratio": 0.7,
    "pool": 0.0,
    "records": [],
    "started_on": None,
}


class CapitalBar:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/capital_bar/")
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

    def get_status(self) -> dict[str, Any]:
        state = self._load()
        pool = float(state.get("pool", 0.0))
        ratio = float(state.get("feed_ratio", 0.8))
        thresholds = []
        for t in THRESHOLDS:
            reached = pool >= t["amount"]
            gap = max(0.0, t["amount"] - pool)
            pct = round(min(100, pool / t["amount"] * 100))
            thresholds.append({**t, "reached": reached, "gap": gap, "pct": pct})
        # Proyección mensual pasivo al pool actual
        monthly_passive = self._project_monthly_passive(pool)
        return {
            "success": True,
            "pool": round(pool, 2),
            "feed_ratio": ratio,
            "thresholds": thresholds,
            "monthly_passive": monthly_passive,
            "records": state.get("records", [])[-10:],
            "started_on": state.get("started_on"),
            "message": self._message(pool),
        }

    def _message(self, pool: float) -> str:
        if pool < 500:
            return "El pool arranca en 0: cada payout registrado suma lo configurado."
        if pool < 25000:
            return "Buen capital acumulándose. Los umbrales te dicen exactamente cuándo se vuelve activo."
        return "Al nivel actual tu capital ya genera un ingreso mensual visible."

    def _project_monthly_passive(self, pool: float) -> float:
        if pool <= 0:
            return 0.0
        for th in THRESHOLDS:
            amt = th["amount"]
            if pool >= amt:
                yield_rate = DEFAULT_PASSIVE_YIELD.get(amt, 0.04)
        return round(pool * yield_rate, 2)

    def set_feed_ratio(self, ratio: float) -> dict[str, Any]:
        ratio = max(0.0, min(1.0, float(ratio)))
        state = self._load()
        state["feed_ratio"] = round(ratio, 2)
        self._save(state)
        return {"success": True, "feed_ratio": state["feed_ratio"]}

    def record_income(self, amount: float, source: str = "", note: str = "") -> dict[str, Any]:
        amount = float(amount)
        if amount <= 0:
            return {"success": False, "message": "El monto debe ser mayor a 0."}
        state = self._load()
        state["started_on"] = state.get("started_on") or datetime.now(UTC).isoformat()
        ratio = float(state.get("feed_ratio", 0.8))
        feed = round(amount * ratio, 2)
        state["pool"] = round(float(state.get("pool", 0.0)) + feed, 2)
        record = {
            "amount": round(amount, 2),
            "feed_ratio": ratio,
            "feed": feed,
            "source": source or "ingreso",
            "note": note,
            "created_at": datetime.now(UTC).isoformat(),
        }
        state["records"].append(record)
        self._save(state)
        return {"success": True, "pool": state["pool"], "feed": feed, "record": record}

    def adjust_pool(self, amount: float, note: str = "") -> dict[str, Any]:
        """Ajuste manual del pool (subir por aportes externos, bajar por retiros)."""
        state = self._load()
        state["pool"] = round(float(state.get("pool", 0.0)) + float(amount), 2)
        if note:
            state["records"].append(
                {
                    "amount": round(float(amount), 2),
                    "feed": 0.0,
                    "source": "ajuste",
                    "note": note,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
        self._save(state)
        return {"success": True, "pool": state["pool"]}


_cb: CapitalBar | None = None


def get_capital_bar() -> CapitalBar:
    global _cb
    if _cb is None:
        _cb = CapitalBar()
    return _cb
