"""Extra radars — Dip (mean-reversion) + Spread CEX/DEX, paper-first, seguro.

Ambos reusan el modelo de seguridad de pump_radar: lectura keyless, persistencia
en TradingStore, live solo con TRADING_MODE=real + kill sano + approval HMAC.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from cores.trading.strategies.memecoin_filters import FilterConfig, evaluate_pair

logger = logging.getLogger("ownex.extra_radars")

DEX_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search?q=solana"
RUGCHECK_URL = "https://api.rugcheck.xyz/v1/tokens/{mint}/report"
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"


@dataclass(frozen=True, slots=True)
class DipRadarConfig:
    min_liquidity_usd: float = 12_000.0
    min_volume_h24_usd: float = 25_000.0
    min_pump_h24_pct: float = 30.0  # tuvo que haber pumpeado
    min_retrace_m5_pct: float = 8.0  # caída 5m
    min_retrace_h1_pct: float = 12.0  # o caída 1h
    max_candidates: int = 15
    w_retrace: float = 0.5
    w_volume_ratio: float = 0.3
    w_pump_strength: float = 0.2
    store_key: str = "dip_radar_last"


@dataclass(slots=True)
class DipCandidate:
    mint: str
    symbol: str
    price_usd: float
    price_change_h24: float
    price_change_m5: float
    price_change_h1: float
    volume_h24: float
    liquidity_usd: float
    dip_score: float
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    passed_filters: bool = False


@dataclass(frozen=True, slots=True)
class SpreadRadarConfig:
    # Spread mínimo neto después de fees+slippage para señalar oportunidad
    min_spread_pct: float = 0.8
    amount_sol: float = 0.5  # nocional para estimar slippage con Jupiter
    store_key: str = "spread_radar_last"


def _num(v: Any) -> float | None:
    try:
        if v is None or isinstance(v, bool):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def dip_score(pair: dict[str, Any], cfg: DipRadarConfig) -> float:
    ch24 = _num((pair.get("priceChange") or {}).get("h24")) or 0.0
    m5 = _num((pair.get("priceChange") or {}).get("m5")) or 0.0
    h1 = _num((pair.get("priceChange") or {}).get("h1")) or 0.0
    vol = _num((pair.get("volume") or {}).get("h24")) or 0.0
    liq = _num((pair.get("liquidity") or {}).get("usd")) or 1.0

    retrace = max(0.0, -min(m5, h1))  # peor caída 5m/1h
    retrace_s = min(100.0, (retrace / 30.0) * 100.0)
    ratio = vol / max(1.0, liq)
    ratio_s = min(100.0, (ratio / 5.0) * 100.0)
    pump_s = min(100.0, max(0.0, ch24) / 300.0 * 100.0 * 1.2)

    raw = cfg.w_retrace * retrace_s + cfg.w_volume_ratio * ratio_s + cfg.w_pump_strength * pump_s
    return round(float(max(0.0, min(100.0, raw))), 1)


async def _fetch_search() -> list[dict[str, Any]]:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(DEX_SEARCH_URL)
            if r.status_code != 200:
                return []
            data = r.json()
            pairs = data.get("pairs") if isinstance(data, dict) else []
            if not isinstance(pairs, list):
                return []
            return [p for p in pairs if isinstance(p, dict) and p.get("chainId") == "solana"]
    except Exception as exc:
        logger.warning("dip search failed: %s", exc)
        return []


async def _rug(mint: str) -> dict[str, Any]:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=12) as c:
            r = await c.get(RUGCHECK_URL.format(mint=mint))
            if r.status_code != 200:
                return {"error": f"rugcheck {r.status_code}", "mint": mint}
            d = r.json()
            return {
                "holder_count": d.get("holderCount", 0),
                "top_10_pct": d.get("top10HolderPercent", 0),
                "liquidity_locked": d.get("liquidityLocked", False),
                "mint_disabled": d.get("mintDisabled", False),
                "freeze_disabled": d.get("freezeDisabled", False),
                "score": d.get("score", 0),
                "risks": d.get("risks", []),
            }
    except Exception as exc:
        return {"error": str(exc), "mint": mint}


async def scan_dip_candidates(
    cfg: DipRadarConfig | None = None,
    filter_cfg: FilterConfig | None = None,
    enrich_rug: bool = True,
) -> list[DipCandidate]:
    cfg = cfg or DipRadarConfig()
    filter_cfg = filter_cfg or FilterConfig()
    raw = await _fetch_search()
    pref: list[dict[str, Any]] = []
    for p in raw:
        liq = _num((p.get("liquidity") or {}).get("usd"))
        vol = _num((p.get("volume") or {}).get("h24"))
        ch24 = _num((p.get("priceChange") or {}).get("h24"))
        m5 = _num((p.get("priceChange") or {}).get("m5"))
        h1 = _num((p.get("priceChange") or {}).get("h1"))
        if liq is None or liq < cfg.min_liquidity_usd:
            continue
        if vol is None or vol < cfg.min_volume_h24_usd:
            continue
        if ch24 is None or ch24 < cfg.min_pump_h24_pct:
            continue
        # retrace condition: 5m OR 1h caída suficiente
        retrace_m5 = -(m5 or 0) if m5 is not None and m5 < 0 else 0
        retrace_h1 = -(h1 or 0) if h1 is not None and h1 < 0 else 0
        if retrace_m5 < cfg.min_retrace_m5_pct and retrace_h1 < cfg.min_retrace_h1_pct:
            continue
        pref.append(p)

    pref = pref[: cfg.max_candidates * 2]
    out: list[DipCandidate] = []
    import asyncio

    for pair in pref:
        mint = str((pair.get("baseToken") or {}).get("address") or "")
        if not mint:
            continue
        rug = await _rug(mint) if enrich_rug else None
        await asyncio.sleep(0.12)
        verdict = evaluate_pair(pair, rug if rug and not rug.get("error") else None, filter_cfg)
        score = dip_score(pair, cfg)
        ch24 = float(_num((pair.get("priceChange") or {}).get("h24")) or 0.0)
        m5 = float(_num((pair.get("priceChange") or {}).get("m5")) or 0.0)
        h1 = float(_num((pair.get("priceChange") or {}).get("h1")) or 0.0)
        out.append(
            DipCandidate(
                mint=mint,
                symbol=str((pair.get("baseToken") or {}).get("symbol") or "?"),
                price_usd=float(_num(pair.get("priceUsd")) or 0.0),
                price_change_h24=ch24,
                price_change_m5=m5,
                price_change_h1=h1,
                volume_h24=float(_num((pair.get("volume") or {}).get("h24")) or 0.0),
                liquidity_usd=float(_num((pair.get("liquidity") or {}).get("usd")) or 0.0),
                dip_score=score,
                reasons=verdict.reasons,
                warnings=verdict.warnings,
                passed_filters=verdict.passed,
            )
        )
    out.sort(key=lambda c: (c.passed_filters, c.dip_score), reverse=True)
    return out[: cfg.max_candidates]


# ── Spread CEX/DEX ────────────────────────────────────────────────────


async def _binance_sol_price() -> float | None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(BINANCE_PRICE_URL)
            if r.status_code != 200:
                return None
            return float(r.json().get("price") or 0) or None
    except Exception:
        return None


async def _jupiter_sol_price(amount_sol: float = 0.5) -> float | None:
    try:
        from cores.trading.dex.jupiter import SOL_MINT, USDC_MINT, JupiterClient

        client = JupiterClient()
        lamports = int(amount_sol * 1_000_000_000)
        quote = await __import__("asyncio").to_thread(client.quote, SOL_MINT, USDC_MINT, lamports, 100)
        if not quote:
            return None
        # price ~ outAmount (USDC 6 dec) / amount_sol
        return float(quote.out_amount) / 1_000_000.0 / max(amount_sol, 1e-9)
    except Exception as exc:
        logger.warning("jupiter price failed: %s", exc)
        return None


async def scan_spread(cfg: SpreadRadarConfig | None = None) -> dict[str, Any]:
    cfg = cfg or SpreadRadarConfig()
    import asyncio

    bin_price, jup_price = await asyncio.gather(_binance_sol_price(), _jupiter_sol_price(cfg.amount_sol))
    if bin_price is None or jup_price is None or bin_price == 0:
        return {
            "success": False,
            "reason": "price unavailable (binance or jupiter)",
            "binance": bin_price,
            "jupiter": jup_price,
        }
    spread_pct = (jup_price - bin_price) / bin_price * 100.0
    # Neto después de ~0.3% fee + 0.5% slippage por lado (conservador 0.8 ya en threshold)
    net = spread_pct - 0.6  # aprox ida
    opp = abs(spread_pct) >= cfg.min_spread_pct
    return {
        "success": True,
        "amount_sol": cfg.amount_sol,
        "binance_usd": round(bin_price, 4),
        "jupiter_usd": round(jup_price, 4),
        "spread_pct": round(spread_pct, 3),
        "spread_net_pct": round(net, 3),
        "opportunity": opp,
        "direction": "sell_dex_buy_cex" if spread_pct > 0 else "buy_dex_sell_cex",
        "threshold_pct": cfg.min_spread_pct,
    }


async def run_dip_radar_cycle(store: Any | None = None, cfg: DipRadarConfig | None = None) -> dict[str, Any]:
    cfg = cfg or DipRadarConfig()
    try:
        cands = await scan_dip_candidates(cfg)
        snap = {
            "scanned_at": time.time(),
            "count": len(cands),
            "candidates": [c.__dict__ for c in cands],
            "config": cfg.__dict__,
        }
        target = store or __import__("cores.trading.store", fromlist=["TradingStore"]).TradingStore()
        with __import__("contextlib").suppress(Exception):
            target.set(cfg.store_key, snap)
        return {"success": True, **snap}
    except Exception as exc:
        logger.warning("dip radar failed: %s", exc)
        return {"success": False, "error": str(exc), "count": 0, "candidates": []}


async def run_spread_radar_cycle(store: Any | None = None, cfg: SpreadRadarConfig | None = None) -> dict[str, Any]:
    cfg = cfg or SpreadRadarConfig()
    try:
        snap = await scan_spread(cfg)
        snap["scanned_at"] = time.time()
        snap["config"] = cfg.__dict__
        target = store or __import__("cores.trading.store", fromlist=["TradingStore"]).TradingStore()
        with __import__("contextlib").suppress(Exception):
            target.set(cfg.store_key, snap)
        return snap
    except Exception as exc:
        logger.warning("spread radar failed: %s", exc)
        return {"success": False, "error": str(exc)}


def run_dip_radar_cycle_sync(store: Any | None = None, cfg: DipRadarConfig | None = None) -> dict[str, Any]:
    import asyncio
    import threading

    try:
        return asyncio.run(run_dip_radar_cycle(store, cfg))
    except RuntimeError:
        res: dict[str, Any] = {}

        def _run() -> None:
            res.update(asyncio.run(run_dip_radar_cycle(store, cfg)))

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=60)
        return res if res else {"success": False, "error": "timeout", "count": 0, "candidates": []}


def run_spread_radar_cycle_sync(store: Any | None = None, cfg: SpreadRadarConfig | None = None) -> dict[str, Any]:
    import asyncio
    import threading

    try:
        return asyncio.run(run_spread_radar_cycle(store, cfg))
    except RuntimeError:
        res: dict[str, Any] = {}

        def _run() -> None:
            res.update(asyncio.run(run_spread_radar_cycle(store, cfg)))

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=60)
        return res if res else {"success": False, "error": "timeout"}
