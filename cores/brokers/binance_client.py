"""Binance read-only account sync via ccxt.

OWNEX configures the client for PRIVATE READ ONLY: fetch_balance and
account data. No order, trade, transfer or withdrawal endpoints are ever
called — ccxt is only used with read methods here.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ownex.brokers.binance")


class BinanceReadOnlyError(Exception):
    """Binance credentials rejected or API unreachable."""


def sync_binance_account(api_key: str, api_secret: str) -> dict[str, Any]:
    """Fetch spot balances (read-only). Returns a snapshot payload."""
    try:
        import ccxt
    except ImportError as exc:  # pragma: no cover - ccxt is an optional dep
        raise BinanceReadOnlyError("ccxt no está instalado") from exc

    exchange = ccxt.binance(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
    )
    try:
        balance = exchange.fetch_balance()
    except Exception as exc:
        raise BinanceReadOnlyError(f"Binance rechazó la consulta: {exc}") from exc

    total = balance.get("total") or {}
    free = balance.get("free") or {}
    used = balance.get("used") or {}

    nonzero_total = {k: v for k, v in total.items() if isinstance(v, (int, float)) and v != 0}
    nonzero_free = {k: v for k, v in free.items() if isinstance(v, (int, float)) and v != 0}
    nonzero_used = {k: v for k, v in used.items() if isinstance(v, (int, float)) and v != 0}

    return {
        "authenticated": True,
        "exchange": "binance",
        "permissions": "read_only",
        "quote_currency": balance.get("quoteCurrency"),
        "balances": {
            "total": nonzero_total,
            "free": nonzero_free,
            "used": nonzero_used,
        },
        "info_keys": sorted((balance.get("info") or {}).keys())[:20],
    }
