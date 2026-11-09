"""External portfolio view — merged read-model across synced providers.

P13 integration layer: normalized provider data -> canonical read models
consumed by Investments / Capital / Crypto / Revenue views. Read-only;
never mutates ledger or wallet state.

Classification rules for transactions (revenue ledger separation):
  - trade: buy/sell/compra/venta -> NOT income
  - transfer: deposit/withdrawal/transferencia -> NOT income
  - fee: comision/fee/gas -> cost, NOT income
  - income: rendimiento/dividend/interest/staking/yield/airdrop -> candidate income
  - unknown: everything else -> never counted as income
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.connections import financial_normalizer
from cores.env.config import get_config

logger = logging.getLogger("ownex.connections.portfolio_view")

_TRADE_TYPES = {"buy", "sell", "compra", "venta", "suscripcion-fci", "rescate-fci", "trade", "exchange_trade"}
_TRANSFER_TYPES = {"deposit", "withdrawal", "transfer", "deposito", "retiro", "transferencia"}
_FEE_TYPES = {"fee", "commission", "comision", "gas", "exchange_fee"}
_INCOME_TYPES = {
    "dividend", "dividendo", "interest", "interes", "yield", "rendimiento",
    "staking", "staking_reward", "airdrop", "recompensa", "reward", "coupon", "cupon",
}


def _norm_dir() -> Path:
    return get_config().data_dir / "connections" / "normalized"


def _load_all() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    norm_dir = _norm_dir()
    if norm_dir.exists():
        for path in sorted(norm_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            provider = data.get("provider") or path.stem
            out[provider] = data
    return out


def _classify_tx(tx: dict[str, Any]) -> str:
    t = str(tx.get("tx_type") or tx.get("type") or "").strip().lower()
    if t in _INCOME_TYPES:
        return "income"
    if t in _FEE_TYPES:
        return "fee"
    if t in _TRANSFER_TYPES:
        return "transfer"
    if t in _TRADE_TYPES:
        return "trade"
    desc = str(tx.get("extra", {}).get("description") or "").lower() if isinstance(tx.get("extra"), dict) else ""
    for kind, words in (
        ("income", ("dividendo", "rendimento", "interes", "staking", "airdrop")),
        ("fee", ("comision", "fee", "cargo")),
        ("transfer", ("deposito", "retiro", "transferencia")),
        ("trade", ("compra", "venta")),
    ):
        if any(w in desc for w in words):
            return kind
    return "unknown"


def external_positions() -> list[dict[str, Any]]:
    """All normalized positions across providers, tagged with provider."""
    positions: list[dict[str, Any]] = []
    for provider, data in _load_all().items():
        for pos in data.get("positions") or []:
            positions.append({"provider": provider, **pos})
    return positions


def external_transactions(limit: int = 500) -> list[dict[str, Any]]:
    """All normalized transactions merged, classified, newest first."""
    txs: list[dict[str, Any]] = []
    for provider, data in _load_all().items():
        for tx in data.get("transactions") or []:
            classified = {"provider": provider, "kind": _classify_tx(tx), **tx}
            txs.append(classified)
    txs.sort(key=lambda t: str(t.get("executed_at") or ""), reverse=True)
    return txs[:limit]


def income_candidates() -> list[dict[str, Any]]:
    """Only transactions classified as income — revenue ledger feed.

    Everything else (trades, transfers, fees, unknown) is excluded by
    construction: internal moves are never income.
    """
    return [t for t in external_transactions() if t["kind"] == "income"]


def portfolio_detail() -> dict[str, Any]:
    """Full read-model for capital/investment views."""
    providers = _load_all()
    return {
        "providers": {
            p: {
                "position_count": d.get("position_count", 0),
                "transaction_count": d.get("transaction_count", 0),
                "cash_by_currency": d.get("cash_by_currency", {}),
                "normalized_at": d.get("normalized_at"),
            }
            for p, d in providers.items()
        },
        "positions": external_positions(),
        "cash_by_currency": financial_normalizer.consolidated_portfolio().get("cash_by_currency", {}),
        "provider_count": len(providers),
        "generated_at": datetime.now(UTC).isoformat(),
    }
