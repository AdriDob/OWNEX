"""Offramp Executor — ejecución automatizada de retiros a ARS.

Genera deeplinks/URLs listas para abrir y confirmar en cada proveedor.
No ejecuta clics (requiere navegador), pero arma la URL con monto,
destino y referencia pre-rellenada. Para APIs reales (Wise, Payoneer)
usa credenciales del vault si están configuradas.

Persistencia: ~/.config/ownex/offramp/state.json
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.offramp_executor")

PROVIDERS = {
    "binance_p2p": {
        "name": "Binance P2P",
        "type": "deeplink",
        "base_url": "https://p2p.binance.com/en/trade/USDT/ARS",
        "params": ["amount", "fiat", "asset"],
        "requires_kyc": True,
        "min_usd": 10,
    },
    "bybit_p2p": {
        "name": "Bybit P2P",
        "type": "deeplink",
        "base_url": "https://www.bybit.com/en/fiat/trade/otc/USDT/ARS",
        "params": ["amount", "currency", "coin"],
        "requires_kyc": True,
        "min_usd": 10,
    },
    "lemon": {
        "name": "Lemon",
        "type": "deeplink",
        "base_url": "lemon://sell?currency=ARS&crypto=USDT",
        "params": ["amount"],
        "requires_kyc": True,
        "min_usd": 5,
    },
    "buenbit": {
        "name": "Buenbit",
        "type": "deeplink",
        "base_url": "buenbit://sell?from=USDT&to=ARS",
        "params": ["amount"],
        "requires_kyc": True,
        "min_usd": 5,
    },
    "belo": {
        "name": "Belo",
        "type": "deeplink",
        "base_url": "belo://convert?from=USDT&to=ARS",
        "params": ["amount"],
        "requires_kyc": True,
        "min_usd": 5,
    },
    "wise": {
        "name": "Wise",
        "type": "api",
        "base_url": "https://api.transferwise.com/v1",
        "endpoint": "/transfers",
        "requires_kyc": True,
        "min_usd": 1,
        "needs_creds": True,
    },
    "payoneer": {
        "name": "Payoneer",
        "type": "api",
        "base_url": "https://api.payoneer.com/v4",
        "endpoint": "/payments",
        "requires_kyc": True,
        "min_usd": 50,
        "needs_creds": True,
    },
    "dolarapp": {
        "name": "DolarApp",
        "type": "deeplink",
        "base_url": "dolarapp://receive?currency=USDC&amount={amount}",
        "params": ["amount"],
        "requires_kyc": True,
        "min_usd": 1,
    },
    "wallbit": {
        "name": "Wallbit",
        "type": "deeplink",
        "base_url": "wallbit://deposit?currency=USDC&amount={amount}",
        "params": ["amount"],
        "requires_kyc": True,
        "min_usd": 1,
    },
}

_DEFAULT_STATE = {
    "executions": [],
    "default_provider": "binance_p2p",
}


class OfframpExecutor:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/offramp/")
        os.makedirs(self.data_dir, exist_ok=True)

    @property
    def state_path(self) -> str:
        return os.path.join(self.data_dir, "state.json")

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                s = json.load(f)
                for k, v in _DEFAULT_STATE.items():
                    s.setdefault(k, v)
                return s
        except Exception:
            return dict(_DEFAULT_STATE)

    def _save(self, s: dict[str, Any]) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)

    def get_providers(self) -> dict[str, Any]:
        return {"success": True, "providers": PROVIDERS, "default": self._load().get("default_provider", "binance_p2p")}

    def set_default(self, provider_id: str) -> dict[str, Any]:
        if provider_id not in PROVIDERS:
            return {"success": False, "message": "Proveedor no válido."}
        s = self._load()
        s["default_provider"] = provider_id
        self._save(s)
        return {"success": True, "default": provider_id}

    def build_url(self, provider_id: str, amount_usd: float, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        p = PROVIDERS.get(provider_id)
        if not p:
            return {"success": False, "message": "Proveedor no encontrado."}
        if amount_usd < p.get("min_usd", 0):
            return {"success": False, "message": f"Mínimo {p['min_usd']} USD para {p['name']}."}

        url = p["base_url"]
        if p["type"] == "deeplink":
            params = {"amount": f"{amount_usd:.2f}"}
            if extra:
                params.update(extra)
            qs = urllib.parse.urlencode(params)
            if "?" in url:
                url += "&" + qs
            else:
                url += "?" + qs
        else:
            url = p["base_url"] + p.get("endpoint", "")

        exec_id = f"off-{int(datetime.now(UTC).timestamp() * 1000)}"
        entry = {
            "id": exec_id,
            "provider": provider_id,
            "provider_name": p["name"],
            "amount_usd": round(amount_usd, 2),
            "url": url,
            "type": p["type"],
            "created_at": datetime.now(UTC).isoformat(),
            "status": "pending",
        }
        s = self._load()
        s["executions"].append(entry)
        self._save(s)
        return {"success": True, "execution": entry}

    def mark_done(self, execution_id: str, txid: str = "") -> dict[str, Any]:
        s = self._load()
        for e in s["executions"]:
            if e["id"] == execution_id:
                e["status"] = "done"
                e["txid"] = txid
                e["completed_at"] = datetime.now(UTC).isoformat()
                self._save(s)
                return {"success": True, "execution": e}
        return {"success": False, "message": "Ejecución no encontrada."}

    def get_status(self) -> dict[str, Any]:
        s = self._load()
        pending = [e for e in s["executions"] if e.get("status") == "pending"]
        done = [e for e in s["executions"] if e.get("status") == "done"]
        return {
            "success": True,
            "default": s.get("default_provider", "binance_p2p"),
            "pending": len(pending),
            "completed": len(done),
            "total_volume_usd": round(sum(e.get("amount_usd", 0) for e in done), 2),
            "recent": s["executions"][-5:][::-1],
        }


_off: OfframpExecutor | None = None


def get_offramp_executor() -> OfframpExecutor:
    global _off
    if _off is None:
        _off = OfframpExecutor()
    return _off
