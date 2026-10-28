"""Pump.fun launch discovery — automatic fresh-launch radar, read-only.

Pump.fun bonding-curve launches move too fast for the DexScreener search path
(which sees them late, post-hype). This module watches the public launch feed
(frontend-api-v3, keyless) and filters for tradeable youth:

- fresh (age ≤ max_age_minutes), pre-graduation (mcap < $69k Raydium line)
- not nsfw/banned/complete, dust floor, social/activity signals as reasons

Design rules: pure filters (no network in verdicts), fetch never raises,
no funds move here — entries only reach the DRY_RUN paper loop, and live
execution stays behind TradingConfig REAL + Human Gate + kill-switch.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.pumpfun_launch")

PUMP_COINS_URL = (
    "https://frontend-api-v3.pump.fun/coins?offset=0&limit={limit}&sort=created_timestamp&order=DESC&includeNsfw=false"
)
# Raydium migration line: bonding curve completes near $69k market cap.
GRADUATION_MC_USD = 69_000.0
SOL_DECIMALS = 9
TOKEN_DECIMALS_DEFAULT = 6

_sol_price_cache: dict[str, Any] = {"price": None, "at": 0.0}
SOL_PRICE_TTL_S = 60.0


@dataclass(frozen=True, slots=True)
class LaunchFilterConfig:
    max_age_minutes: float = 30.0
    min_mcap_usd: float = 3_000.0  # dust floor (instant-rug noise)
    max_mcap_usd: float = GRADUATION_MC_USD  # pre-graduation only
    block_nsfw: bool = True
    max_launches: int = 25


@dataclass(slots=True)
class LaunchVerdict:
    passed: bool
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _num(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def graduation_proximity(mcap_usd: float | None) -> float | None:
    """0..1+ how close to the Raydium line. Closer = hotter but later. Never a buy signal alone."""
    if mcap_usd is None or mcap_usd <= 0:
        return None
    return round(mcap_usd / GRADUATION_MC_USD, 3)


def evaluate_launch(
    raw: dict[str, Any],
    cfg: LaunchFilterConfig | None = None,
    now_ms: int | None = None,
) -> LaunchVerdict:
    """Pure verdict over one launch object. Fail-closed, never raises."""
    cfg = cfg or LaunchFilterConfig()
    try:
        if not isinstance(raw, dict):
            return LaunchVerdict(False, (), ("not-a-launch",))
        if raw.get("complete") is True:
            return LaunchVerdict(False, (), ("already-graduated",))
        if raw.get("is_banned") is True:
            return LaunchVerdict(False, (), ("banned",))
        if cfg.block_nsfw and raw.get("nsfw") is True:
            return LaunchVerdict(False, (), ("nsfw",))
        mint = str(raw.get("mint") or "")
        if not mint:
            return LaunchVerdict(False, (), ("no-mint",))

        now = now_ms if now_ms is not None else int(time.time() * 1000)
        created = _num(raw.get("created_timestamp"))
        age_min = (now - created) / 60_000.0 if created else None
        if age_min is None or age_min < 0:
            return LaunchVerdict(False, (), ("no-age",))
        if age_min > cfg.max_age_minutes:
            return LaunchVerdict(False, (), (f"stale-{age_min:.0f}m",))

        mcap = _num(raw.get("usd_market_cap"))
        if mcap is None:
            return LaunchVerdict(False, (), ("no-mcap",))
        if mcap < cfg.min_mcap_usd:
            return LaunchVerdict(False, (), (f"dust-${mcap:.0f}",))
        if mcap > cfg.max_mcap_usd:
            return LaunchVerdict(False, (), (f"post-line-${mcap:.0f}",))

        reasons = [f"fresh-{age_min:.0f}m", f"mcap-${mcap:.0f}"]
        prox = graduation_proximity(mcap)
        if prox is not None and prox >= 0.5:
            reasons.append(f"near-line-{prox:.0%}")
        warnings: list[str] = []
        if raw.get("twitter") or raw.get("website"):
            reasons.append("has-socials")
        else:
            warnings.append("no-socials")
        replies = _num(raw.get("reply_count")) or 0
        if replies >= 10:
            reasons.append(f"active-{int(replies)}-replies")
        creator = str(raw.get("creator") or "")
        if creator:
            warnings.append(f"creator-{creator[:8]}-unvetted")
        return LaunchVerdict(True, tuple(reasons), tuple(warnings))
    except Exception as exc:
        return LaunchVerdict(False, (), (f"verdict-error:{type(exc).__name__}",))


async def fetch_new_launches(limit: int = 50) -> list[dict[str, Any]]:
    """Fresh pump.fun launches, newest first. [] when offline. Never raises."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(PUMP_COINS_URL.format(limit=max(1, min(limit, 100))))
            if resp.status_code != 200:
                logger.warning("pump.fun feed HTTP %s", resp.status_code)
                return []
            data = resp.json()
            return [c for c in data] if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("pump.fun feed failed: %s", exc)
        return []


def get_sol_price_usd() -> float | None:
    """SOL USD, 60s cached, Jupiter lite keyless. None when unknown. Never raises."""
    import httpx

    now = time.time()
    if now - float(_sol_price_cache.get("at") or 0) < SOL_PRICE_TTL_S:
        return _sol_price_cache.get("price")
    try:
        resp = httpx.get(
            "https://lite-api.jup.ag/price/v3?ids=So11111111111111111111111111111111111111112",
            timeout=10,
        )
        price = float(resp.json()["So11111111111111111111111111111111111111112"]["usdPrice"])
        _sol_price_cache.update(price=price, at=now)
        return price
    except Exception:
        return _sol_price_cache.get("price")


def launch_to_token(raw: dict[str, Any], sol_price_usd: float | None = None) -> dict[str, Any]:
    """Map a launch to the paper-loop token shape. Pure (price needs SOL or mcap math)."""
    decimals = int(_num(raw.get("base_decimals")) or TOKEN_DECIMALS_DEFAULT)
    supply = (_num(raw.get("total_supply")) or 0) / (10**decimals)
    mcap = _num(raw.get("usd_market_cap")) or 0.0
    price = (mcap / supply) if supply > 0 else 0.0
    curve_sol = (_num(raw.get("real_sol_reserves")) or 0.0) / (10**SOL_DECIMALS)
    curve_usd = curve_sol * (sol_price_usd or 0.0)
    created = _num(raw.get("created_timestamp")) or 0
    return {
        "mint": str(raw.get("mint") or ""),
        "symbol": str(raw.get("symbol") or "?"),
        "name": str(raw.get("name") or ""),
        "price_usd": price,
        "market_cap_usd": mcap,
        "liquidity_usd": curve_usd,  # bonding-curve value, NOT locked LP
        "curve_sol": curve_sol,
        "age_min": (time.time() * 1000 - created) / 60_000.0 if created else None,
        "graduation_proximity": graduation_proximity(mcap),
        "has_socials": bool(raw.get("twitter") or raw.get("website")),
        "reply_count": int(_num(raw.get("reply_count")) or 0),
        "source": "pumpfun",
        "url": f"https://pump.fun/coin/{raw.get('mint')}",
    }


async def scan_pumpfun_launches(
    cfg: LaunchFilterConfig | None = None,
    sol_price_usd: float | None = None,
) -> list[dict[str, Any]]:
    """Fetch → verdict → map. Entry-ready launch tokens. Never raises."""
    cfg = cfg or LaunchFilterConfig()
    out: list[dict[str, Any]] = []
    try:
        launches = await fetch_new_launches(limit=cfg.max_launches * 2)
    except Exception:
        return []
    for raw in launches[: cfg.max_launches * 2]:
        verdict = evaluate_launch(raw, cfg)
        if not verdict.passed:
            continue
        tok = launch_to_token(raw, sol_price_usd)
        if not tok["mint"] or not tok["price_usd"]:
            continue
        tok["filter_reasons"] = list(verdict.reasons)
        tok["filter_warnings"] = list(verdict.warnings)
        out.append(tok)
        if len(out) >= cfg.max_launches:
            break
    return out
