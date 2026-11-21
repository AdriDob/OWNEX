"""Coinbase / Kraken / Bybit — read-only connector via ccxt.

Ownership boundary: this module is the ONLY place that talks to these three
exchanges, and it only ever calls public market data endpoints plus
``fetch_balance``. No order, cancel, transfer or withdrawal method is invoked
here — write access does not exist in this connector, independently of what
permission mode a connection may have.

Two capabilities:

- ``verify_public(provider)`` — hits the real public REST API with no
  credentials and returns evidence (reachability, latency, markets count,
  last traded price + its timestamp). Used to prove a connector works before a
  user hands over keys.
- ``sync_cex_account(provider, api_key, api_secret)`` — read-only balances
  (``fetch_balance``) plus public quotes for the held assets.

Failures raise typed errors so the API layer can answer 401 vs 502 honestly
instead of a generic 500.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.brokers.cex")

CEX_PROVIDERS: frozenset[str] = frozenset({"coinbase", "kraken", "bybit"})

# Reviewable metadata per exchange: default public symbol, docs, credential shape.
CEX_EXCHANGES: dict[str, dict[str, Any]] = {
    "coinbase": {
        "name": "Coinbase Advanced Trade",
        "public_symbol": "BTC/USD",
        "docs_url": "https://docs.cdp.coinbase.com",
        "ws": True,
        "secret_label": "private key (CDP API key)",
    },
    "kraken": {
        "name": "Kraken",
        "public_symbol": "BTC/USD",
        "docs_url": "https://docs.kraken.com/api",
        "ws": True,
        "secret_label": "private key",
    },
    "bybit": {
        "name": "Bybit",
        "public_symbol": "BTC/USDT",
        "docs_url": "https://bybit-exchange.github.io/docs/v5/intro",
        "ws": True,
        "secret_label": "API secret",
    },
}

# Assets treated as cash equivalents when quoting holdings (never converted).
_QUOTE_ASSETS = ("USDT", "USDC", "USD", "EUR", "BRL")


class CEXConnectorError(Exception):
    """Base error for the CEX connector."""


class CEXAuthError(CEXConnectorError):
    """Credentials rejected by the exchange (401/403 from the private API)."""


class CEXUnavailableError(CEXConnectorError):
    """Exchange unreachable, rate limited or returning an unexpected payload."""


def _exchange(provider: str, api_key: str = "", api_secret: str = "", password: str = "") -> Any:
    """Build a ccxt exchange instance (public if no credentials given)."""
    if provider not in CEX_PROVIDERS:
        raise CEXUnavailableError(f"Exchange no soportado: {provider}")
    try:
        import ccxt
    except ImportError as exc:  # pragma: no cover - ccxt is an optional dep
        raise CEXUnavailableError("ccxt no está instalado") from exc

    exchange_class = getattr(ccxt, provider, None)
    if exchange_class is None:  # pragma: no cover - depends on ccxt version
        raise CEXUnavailableError(f"ccxt no expone '{provider}' en esta versión")

    config: dict[str, Any] = {"enableRateLimit": True}
    if api_key and api_secret:
        config["apiKey"] = api_key
        config["secret"] = api_secret
        if password:
            config["password"] = password
    return exchange_class(config)


def _iso(ms: Any) -> str | None:
    if not isinstance(ms, (int, float)):
        return None
    return datetime.fromtimestamp(float(ms) / 1000, tz=UTC).isoformat()


def verify_public(provider: str, symbol: str | None = None) -> dict[str, Any]:
    """Prove the connector works against the exchange's real public API.

    No credentials involved. Returns evidence, never a claim: if the call fails
    the payload says ``reachable: False`` with the underlying error.
    """
    meta = CEX_EXCHANGES.get(provider)
    if meta is None:
        raise CEXUnavailableError(f"Exchange no soportado: {provider}")
    target = symbol or str(meta["public_symbol"])

    started = time.perf_counter()
    exchange: Any = None
    try:
        exchange = _exchange(provider)
        markets = exchange.load_markets()
        ticker = exchange.fetch_ticker(target)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        last = ticker.get("last")
        if last is None and isinstance(ticker.get("close"), (int, float)):
            last = ticker.get("close")
        # Kraken y Bybit no publican timestamp en su ticker (verificado live), así
        # que se declara la ausencia en vez de presentar la cotización como fresca.
        ticker_time = _iso(ticker.get("timestamp"))
        return {
            "provider": provider,
            "exchange_name": meta["name"],
            "verification": "public_api",
            "reachable": True,
            "authenticated": False,
            "symbol": ticker.get("symbol") or target,
            "last_price": last,
            "quote_volume": ticker.get("quoteVolume") or ticker.get("baseVolume"),
            "ticker_time": ticker_time,
            "ticker_time_source": "exchange" if ticker_time else "unavailable",
            "markets_count": len(markets or {}),
            "latency_ms": latency_ms,
            "checked_at": datetime.now(UTC).isoformat(),
            "docs_url": meta["docs_url"],
            "websocket": meta["ws"],
            "error": None,
        }
    except CEXConnectorError:
        raise
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        logger.warning("Public verification failed for %s: %s", provider, exc)
        return {
            "provider": provider,
            "exchange_name": meta["name"],
            "verification": "public_api",
            "reachable": False,
            "authenticated": False,
            "symbol": target,
            "last_price": None,
            "quote_volume": None,
            "ticker_time": None,
            "ticker_time_source": "unavailable",
            "markets_count": 0,
            "latency_ms": latency_ms,
            "checked_at": datetime.now(UTC).isoformat(),
            "docs_url": meta["docs_url"],
            "websocket": meta["ws"],
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        close = getattr(exchange, "close", None)
        if callable(close):
            try:
                close()
            except Exception:  # pragma: no cover - best-effort cleanup
                logger.debug("ccxt close() failed for %s", provider, exc_info=True)


def _nonzero(balances: Any) -> dict[str, float]:
    out: dict[str, float] = {}
    for asset, amount in (balances or {}).items():
        try:
            value = float(amount or 0)
        except (TypeError, ValueError):
            continue
        if value != 0:
            out[str(asset)] = value
    return out


def _auth_failure(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(word in text for word in ("authentication", "unauthorized", "invalid api", "permission", "signature"))


def sync_cex_account(
    provider: str,
    api_key: str,
    api_secret: str,
    password: str = "",
) -> dict[str, Any]:
    """Read-only account snapshot: balances + public quotes for held assets.

    Only ``load_markets``, ``fetch_balance`` and ``fetch_ticker`` are called.
    """
    if provider not in CEX_PROVIDERS:
        raise CEXUnavailableError(f"Exchange no soportado: {provider}")
    if not api_key or not api_secret:
        raise CEXAuthError("Faltan API key + secret (solo lectura)")

    exchange: Any = None
    try:
        exchange = _exchange(provider, api_key, api_secret, password)
        markets = exchange.load_markets()
        balance = exchange.fetch_balance()
    except CEXConnectorError:
        raise
    except Exception as exc:
        if _auth_failure(exc):
            raise CEXAuthError(f"{provider} rechazó las credenciales: {exc}") from exc
        raise CEXUnavailableError(f"Error consultando {provider}: {exc}") from exc
    finally:
        close = getattr(exchange, "close", None)
        if callable(close):
            try:
                close()
            except Exception:  # pragma: no cover - best-effort cleanup
                logger.debug("ccxt close() failed for %s", provider, exc_info=True)

    total = _nonzero(balance.get("total"))
    free = _nonzero(balance.get("free"))
    used = _nonzero(balance.get("used"))

    quotes: dict[str, Any] = {}
    for asset in sorted(total):
        if asset in _QUOTE_ASSETS:
            continue
        for quote in ("USDT", "USD"):
            symbol = f"{asset}/{quote}"
            if symbol not in (markets or {}):
                continue
            try:
                probe = _exchange(provider)
                ticker = probe.fetch_ticker(symbol)
                close_probe = getattr(probe, "close", None)
                if callable(close_probe):
                    close_probe()
                quotes[asset] = {
                    "symbol": symbol,
                    "last": ticker.get("last"),
                    "timestamp": ticker.get("timestamp"),
                }
            except Exception as exc:
                logger.info("Quote failed for %s %s: %s", provider, symbol, exc)
            break

    return {
        "authenticated": True,
        "exchange": provider,
        "permissions": "read_only",
        "balances": {"total": total, "free": free, "used": used},
        "quotes": quotes,
        "markets_count": len(markets or {}),
        "fetched_at": datetime.now(UTC).isoformat(),
    }
