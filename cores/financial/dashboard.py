"""Unified financial dashboard — single source of truth for everything money.

Consolidates:
  - Truth layer (verified / pending / withdrawn balances)
  - Crypto wallets (BTC, ETH, SOL, TRX + tokens via CryptoManager)
  - Exchange balances (Binance, Coinbase, Kraken via CryptoManager)
  - Takenos virtual wallet
  - ATLAS portfolio (if loaded)
  - CoinGecko prices
  - Income / expense metrics
  - Goal tracking (Objetivo Libertad)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from cores.crypto.coingecko import get_coingecko_feed
from cores.crypto.sync_manager import get_crypto_sync_manager
from cores.financial.truth_layer import get_truth_layer
from cores.financial.withdrawal import get_summary as get_withdrawal_summary
from cores.ledger import compute_wallet, get_history

logger = logging.getLogger("ownex.financial.dashboard")

# Objetivo Libertad — meta personal
LIBERTAD_GOAL_USD = 30_000.0


def get_dashboard() -> dict:
    """Full unified dashboard — everything in one response."""
    truth = get_truth_layer()
    state = truth.get_state()
    wallet = compute_wallet()
    crypto_mgr = get_crypto_sync_manager()
    withdrawal_summary = get_withdrawal_summary()

    # ── Patrimonio total ─────────────────────────────
    total_crypto_usd = crypto_mgr.get_summary().get("total_usd", 0.0)
    total_platform_usd = state.real_balance
    takenos_balance = _get_takenos_balance()
    atlas_total = _get_atlas_total()

    patrimonio_total = round(
        total_crypto_usd + total_platform_usd + takenos_balance + atlas_total, 2
    )

    # ── Breakdowns ───────────────────────────────────
    breakdown = {
        "plataformas_bounty": {
            "total": round(total_platform_usd, 2),
            "detalle": {
                pid: round(ps.verified_balance + ps.pending_balance, 2)
                for pid, ps in state.by_platform.items()
            },
        },
        "crypto": {
            "total": round(total_crypto_usd, 2),
            "detalle": _get_crypto_breakdown(crypto_mgr),
        },
        "takenos": {
            "total": round(takenos_balance, 2),
            "detalle": _get_takenos_detail(),
        },
        "atlas_inversiones": {
            "total": round(atlas_total, 2),
        },
    }

    # ── Liquidez ─────────────────────────────────────
    disponible = round(
        wallet.available_balance + total_crypto_usd * 0.9 + takenos_balance * 0.95, 2
    )
    congelado = round(wallet.locked_balance + (total_crypto_usd * 0.1), 2)
    pendiente = round(wallet.pending_balance + state.pending_balance, 2)

    # ── Income (últimos 30 días) ──────────────────────
    ingresos_mes = _compute_monthly_income(state)

    # ── Goal tracking ────────────────────────────────
    progreso_libertad = min(round((patrimonio_total / LIBERTAD_GOAL_USD) * 100, 1), 100.0)

    # ── Prices ───────────────────────────────────────
    feed = get_coingecko_feed()
    prices = feed.get_prices(["BTC", "ETH", "SOL", "USDC"])
    prices.update(_get_exchange_prices())

    # ── Alerts ───────────────────────────────────────
    alerts = _compute_alerts(state, withdrawal_summary, crypto_mgr)

    return {
        "patrimonio_total": patrimonio_total,
        "objetivo_libertad": {
            "meta_usd": LIBERTAD_GOAL_USD,
            "progreso": progreso_libertad,
            "restante": round(max(LIBERTAD_GOAL_USD - patrimonio_total, 0), 2),
        },
        "liquidez": {
            "disponible": disponible,
            "congelado": congelado,
            "pendiente": pendiente,
        },
        "breakdown": breakdown,
        "ingresos": ingresos_mes,
        "precios": prices,
        "alertas": alerts,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _get_takenos_balance() -> float:
    try:
        from cores.financial.takenos.connector import get_takenos_connector
        summary = get_takenos_connector().get_summary()
        return summary.get("balance_usd", 0.0)
    except Exception:
        return 0.0


def _get_takenos_detail() -> dict:
    try:
        from cores.financial.takenos.connector import get_takenos_connector
        return get_takenos_connector().get_state().get("balance", {})
    except Exception:
        return {}


def _get_atlas_total() -> float:
    try:
        from core.app_registry import get_app_registry
        app = get_app_registry().get("atlas")
        if app is None:
            logger.debug("Atlas app not registered, skipping portfolio")
            return 0.0
        import importlib
        mod = importlib.import_module("apps.atlas.engines.portfolio")
        engine = mod.PortfolioEngine()
        portfolio = engine.get_portfolio()
        if portfolio:
            return portfolio.total_value
        return 0.0
    except ImportError:
        logger.debug("Atlas portfolio engine not available (apps.atlas not loaded)")
        return 0.0
    except Exception:
        logger.debug("Failed to get atlas portfolio", exc_info=True)
        return 0.0


def _get_crypto_breakdown(crypto_mgr: Any) -> dict[str, float]:
    by_asset: dict[str, float] = {}
    for wid in crypto_mgr.connectors:
        snap = crypto_mgr.get_snapshot(wid)
        if snap and snap.balances:
            for bal in snap.balances:
                asset = bal.symbol or bal.asset
                by_asset[asset] = round(by_asset.get(asset, 0.0) + bal.usd_value, 2)
    return dict(sorted(by_asset.items(), key=lambda x: x[1], reverse=True)[:20])


def _get_exchange_prices() -> dict[str, float]:
    feed = get_coingecko_feed()
    major = ["BTC", "ETH", "SOL", "USDC", "USDT", "DAI", "BNB", "ADA", "DOT", "AVAX",
             "LINK", "UNI", "ATOM", "XRP", "DOGE", "TRX", "ARB", "OP", "APT", "SUI"]
    return feed.get_prices(major)


def _compute_monthly_income(state: Any) -> dict:
    thirty_days_ago = datetime.now(UTC).timestamp() - 30 * 86400
    entries = get_history(limit=5000)
    monthly = []
    total = 0.0
    by_platform: dict[str, float] = {}
    by_type: dict[str, float] = {}

    for e in entries:
        ts = e.get("timestamp", "")
        try:
            if isinstance(ts, (int, float)):
                if ts < thirty_days_ago:
                    continue
            elif isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if dt.timestamp() < thirty_days_ago:
                    continue
        except Exception:
            continue

        amount = float(e.get("amount", 0))
        if amount <= 0:
            continue
        platform = e.get("platform", "unknown")
        event = e.get("event", "unknown")
        total += amount
        by_platform[platform] = round(by_platform.get(platform, 0.0) + amount, 2)
        by_type[event] = round(by_type.get(event, 0.0) + amount, 2)
        monthly.append({
            "id": e.get("id", e.get("entry_id", "")),
            "amount": round(amount, 2),
            "platform": platform,
            "event": event,
            "date": ts,
        })

    return {
        "total_mes": round(total, 2),
        "por_plataforma": dict(sorted(by_platform.items(), key=lambda x: x[1], reverse=True)),
        "por_tipo": dict(sorted(by_type.items(), key=lambda x: x[1], reverse=True)),
        "transacciones": sorted(monthly, key=lambda x: x.get("date", ""), reverse=True)[:50],
    }


def _compute_alerts(state: Any, withdrawal_summary: dict, crypto_mgr: Any) -> list[dict]:
    alerts: list[dict] = []

    pending_wd = withdrawal_summary.get("total_pending", 0) + withdrawal_summary.get("total_initiated", 0)
    if pending_wd > 0:
        alerts.append({
            "tipo": "retiro_pendiente",
            "severidad": "info",
            "mensaje": f"{pending_wd} retiro(s) pendiente(s) de confirmación",
        })

    for pid, ps in state.by_platform.items():
        if ps.sync_state.consecutive_failures >= 3:
            alerts.append({
                "tipo": "sync_fallo",
                "severidad": "warning",
                "plataforma": pid,
                "mensaje": f"{pid}: {ps.sync_state.consecutive_failures} sincronizaciones fallidas consecutivas",
            })

    for wid in crypto_mgr.connectors:
        snap = crypto_mgr.get_snapshot(wid)
        if not snap:
            continue
        if snap.connection.value != "connected" and wid:
            alerts.append({
                "tipo": "wallet_desconectada",
                "severidad": "warning",
                "wallet": wid,
                "mensaje": f"Wallet {wid}: {snap.error or 'desconectada'}",
            })

    return alerts
