"""Payout Planner — plan de cobro en Argentina desde cada plataforma.

Cierra el gap "cobrar": para cada fuente (pulse/forge/vault) busca el mejor
método de cobro viable en AR (crypto, Wise, Payoneer, transferencia) con
simulación de fechas, moneda y si llega directo. Reutiliza financial_hub
cuando está disponible; si no, usa una tabla local.

Persistencia: ~/.config/ownex/payout_planner/state.json
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("core.payout_planner")

PLATFORMS = [
    {
        "id": "pulse",
        "name": "Outlier / DA / Mindrift",
        "method": "AirTM / Payoneer → USDT/ARS",
        "arrival_days": 2.0,
        "note": "Requiere VPN estable y cuenta de pago; retiro cada semana.",
    },
    {
        "id": "forge",
        "name": "Opire / Algora / Superteam",
        "method": "USDC (Polygon) → cex/ARS",
        "arrival_days": 1.0,
        "note": "Bounts pagan en USDC; cambiar a ARS cuando convenga.",
    },
    {
        "id": "bounty",
        "name": "HackerOne / Intigriti / Immunefi",
        "method": "Payoneer / cripto",
        "arrival_days": 14.0,
        "note": "Pagos más lentos; guardar para capital pot.",
    },
    {
        "id": "freelance",
        "name": "Freelancer / Upwork",
        "method": "Payoneer → USDT",
        "arrival_days": 7.0,
        "note": "Retiro cada mes por mínimos de plataforma.",
    },
    {
        "id": "mirror",
        "name": "Venta directa / licencias",
        "method": "Stripe/cripto",
        "arrival_days": 3.0,
        "note": "Stripe requiere KYC para AR.",
    },
]

_DEFAULT_STATE = {
    "platforms": [],
    "custom_routes": {},
}


class PayoutPlanner:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/payout_planner/")
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
        plans = []
        for p in PLATFORMS:
            plans.append(
                {
                    **p,
                    "configured": self._is_configured(p["id"]),
                }
            )
        return {"success": True, "platforms": plans, "message": self._message(plans)}

    def _message(self, plans: list[dict[str, Any]]) -> str:
        done = sum(1 for p in plans if p.get("configured"))
        if not done:
            return "Ninguna plataforma de cobro configurada — configurá al menos la principal (pulse)."
        return f"{done} método(s) configurado(s) — el pago ya tiene ruta hacia AR."

    def _is_configured(self, platform_id: str) -> bool:
        state = self._load()
        configured = state.get("configured_platforms", [])
        return platform_id in configured

    def set_configured(self, platform_id: str) -> dict[str, Any]:
        valid = [p["id"] for p in PLATFORMS]
        if platform_id not in valid:
            return {"success": False, "message": "Plataforma inválida."}
        state = self._load()
        configured = set(state.get("configured_platforms", []))
        configured.add(platform_id)
        state["configured_platforms"] = sorted(configured)
        self._save(state)
        return {"success": True, "configured_platforms": state["configured_platforms"]}


_pp: PayoutPlanner | None = None


def get_payout_planner() -> PayoutPlanner:
    global _pp
    if _pp is None:
        _pp = PayoutPlanner()
    return _pp
