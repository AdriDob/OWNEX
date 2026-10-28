"""Pump Radar — radar real y automático de pumps, seguro por diseño.

Detecta pumps en curso en Solana (DexScreener → filtros duros → scoring)
y registra candidates rankeados. Ejecución real siempre requiere Human Gate
y TradingConfig REAL + kill-switch sano.

Modo por defecto: lectura + paper (jamás mueve fondos). Live exige:
  TradingConfig(mode=REAL) + KillSwitch inactivo + approval HMAC single-use
  + límites de riesgo (posición, drawdown, liquidez). Falla cerrado.
"""

from __future__ import annotations

import dataclasses
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from cores.trading.strategies.memecoin_filters import FilterConfig, evaluate_pair

logger = logging.getLogger("ownex.pump_radar")

DEXSCREENER_BASE = "https://api.dexscreener.com"
# DexScreener search/boosted + tokens — keyless, 60 req/min aproximado
DEX_SEARCH_URL = DEXSCREENER_BASE + "/latest/dex/search?q=solana"
DEX_TOKENS_URL = DEXSCREENER_BASE + "/tokens/v1/solana/{mints}"
RUGCHECK_URL = "https://api.rugcheck.xyz/v1/tokens/{mint}/report"


@dataclass(frozen=True, slots=True)
class PumpRadarConfig:
    # Qué es un pump candidato (antes de filtros hard)
    min_liquidity_usd: float = 10_000.0
    min_volume_h24_usd: float = 20_000.0
    min_price_change_h24_pct: float = 20.0  # suba mínima 24h para considerar pump
    max_candidates: int = 20
    # Scoring (pesos suman 1.0)
    w_change_h24: float = 0.45
    w_volume_ratio: float = 0.35  # volume / liquidity
    w_boost: float = 0.20
    # Persistencia
    store_key: str = "pump_radar_last"


@dataclass(slots=True)
class PumpCandidate:
    mint: str
    symbol: str
    name: str
    price_usd: float
    price_change_h24: float
    volume_h24: float
    liquidity_usd: float
    dex: str
    url: str
    pump_score: float
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    passed_filters: bool = False
    rug: dict[str, Any] = field(default_factory=dict)


def _num(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def pump_score(pair: dict[str, Any], cfg: PumpRadarConfig) -> float:
    """Score 0-100 de intensidad de pump desde métricas DexScreener. Puro."""
    ch24 = _num((pair.get("priceChange") or {}).get("h24"))
    vol = _num((pair.get("volume") or {}).get("h24"))
    liq = _num((pair.get("liquidity") or {}).get("usd"))
    boosts = int(((pair.get("boosts") or {}).get("active")) or 0)

    # Cada componente 0-100, luego ponderado
    change_s = 0.0
    if ch24 is not None and cfg.min_price_change_h24_pct > 0:
        # 20% → ~30, 100% → 70, 300%+ → 100 (log-ish cap)
        norm = max(0.0, min(300.0, ch24))
        change_s = min(100.0, (norm / 300.0) * 100.0 * 1.2)
        if ch24 < 0:
            change_s = 0.0

    ratio_s = 0.0
    if vol is not None and liq is not None and liq > 0:
        ratio = vol / liq  # >1 = rotación alta
        ratio_s = min(100.0, (ratio / 5.0) * 100.0)

    boost_s = min(100.0, boosts * 25.0)  # 4 boosts = 100

    raw = cfg.w_change_h24 * change_s + cfg.w_volume_ratio * ratio_s + cfg.w_boost * boost_s
    return round(float(max(0.0, min(100.0, raw))), 1)


def _pair_to_candidate(
    pair: dict[str, Any],
    rug: dict[str, Any] | None,
    score: float,
    passed: bool,
    reasons: tuple[str, ...],
    warnings: tuple[str, ...],
) -> PumpCandidate:
    base = pair.get("baseToken") or {}
    return PumpCandidate(
        mint=str(base.get("address") or ""),
        symbol=str(base.get("symbol") or "?"),
        name=str(base.get("name") or ""),
        price_usd=float(_num(pair.get("priceUsd")) or 0.0),
        price_change_h24=float(_num((pair.get("priceChange") or {}).get("h24")) or 0.0),
        volume_h24=float(_num((pair.get("volume") or {}).get("h24")) or 0.0),
        liquidity_usd=float(_num((pair.get("liquidity") or {}).get("usd")) or 0.0),
        dex=str(pair.get("dexId") or ""),
        url=str(pair.get("url") or ""),
        pump_score=score,
        reasons=reasons,
        warnings=warnings,
        passed_filters=passed,
        rug=rug or {},
    )


async def _fetch_dexsearch_candidates() -> list[dict[str, Any]]:
    """DexScreener search (solana) → lista cruda de pairs. [] si falla."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(DEX_SEARCH_URL)
            if resp.status_code != 200:
                logger.warning("DexScreener search HTTP %s", resp.status_code)
                return []
            data = resp.json()
            pairs = data.get("pairs") if isinstance(data, dict) else []
            if not isinstance(pairs, list):
                return []
            # Solo Solana
            sol = [p for p in pairs if isinstance(p, dict) and p.get("chainId") == "solana"]
            return sol
    except Exception as exc:
        logger.warning("DexScreener search failed: %s", exc)
        return []


async def _fetch_rugcheck(mint: str) -> dict[str, Any]:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(RUGCHECK_URL.format(mint=mint))
            if resp.status_code != 200:
                return {"error": f"rugcheck {resp.status_code}", "mint": mint}
            data = resp.json()
            return {
                "holder_count": data.get("holderCount", 0),
                "top_10_pct": data.get("top10HolderPercent", 0),
                "liquidity_locked": data.get("liquidityLocked", False),
                "mint_disabled": data.get("mintDisabled", False),
                "freeze_disabled": data.get("freezeDisabled", False),
                "score": data.get("score", 0),
                "risks": data.get("risks", []),
            }
    except Exception as exc:
        return {"error": str(exc), "mint": mint}


async def scan_pump_candidates(
    cfg: PumpRadarConfig | None = None,
    filter_cfg: FilterConfig | None = None,
    enrich_rug: bool = True,
) -> list[PumpCandidate]:
    """Scan completo: DexScreener → pre-filtro pump → RugCheck → filtros hard → ranking.

    Nunca raisea ni inventa: [] si offline. Cada candidate expone passed_filters
    + reasons/warnings para auditoría.
    """
    cfg = cfg or PumpRadarConfig()
    filter_cfg = filter_cfg or FilterConfig()
    raw_pairs = await _fetch_dexsearch_candidates()
    if not raw_pairs:
        return []

    # Pre-filtro barato de pump (antes de RugCheck que es 1 req por mint)
    pref = []
    for p in raw_pairs:
        liq = _num((p.get("liquidity") or {}).get("usd"))
        vol = _num((p.get("volume") or {}).get("h24"))
        ch = _num((p.get("priceChange") or {}).get("h24"))
        if liq is None or liq < cfg.min_liquidity_usd:
            continue
        if vol is None or vol < cfg.min_volume_h24_usd:
            continue
        if ch is None or ch < cfg.min_price_change_h24_pct:
            continue
        pref.append(p)

    # Rug + filtros hard + scoring, luego ranking por pump_score
    import asyncio

    # Limitar RugCheck para no spamear (20 max, secuencial con throttle leve)
    pref = pref[: cfg.max_candidates * 2]  # sobremuestreo antes de filtros
    candidates: list[PumpCandidate] = []
    for pair in pref:
        base = pair.get("baseToken") or {}
        mint = str(base.get("address") or "")
        if not mint:
            continue
        rug = await _fetch_rugcheck(mint) if enrich_rug else None
        # Throttle gentil (DexScreener + RugCheck comparten infra)
        await asyncio.sleep(0.12)

        verdict = evaluate_pair(pair, rug if rug and not rug.get("error") else None, filter_cfg)
        score = pump_score(pair, cfg)
        cand = _pair_to_candidate(pair, rug or {}, score, verdict.passed, verdict.reasons, verdict.warnings)
        candidates.append(cand)

    # Ranking: primero los que pasan filtros, luego por score desc
    candidates.sort(key=lambda c: (c.passed_filters, c.pump_score), reverse=True)
    return candidates[: cfg.max_candidates]


def _persist(store: Any, key: str, payload: Any) -> None:
    try:
        if store is None:
            return
        store.set(key, payload)
    except Exception:
        pass


async def run_pump_radar_cycle(
    store: Any | None = None,
    cfg: PumpRadarConfig | None = None,
    filter_cfg: FilterConfig | None = None,
) -> dict[str, Any]:
    """Ciclo scheduled: scan → persist. Nunca mueve fondos. Nunca raisea.

    Guarda en TradingStore bajo `pump_radar_last` el snapshot rankeado.
    """
    cfg = cfg or PumpRadarConfig()
    try:
        candidates = await scan_pump_candidates(cfg, filter_cfg)
        # Fresh pump.fun launches alongside (pre-graduation feed, best-effort)
        fresh_launches: list[dict[str, Any]] = []
        try:
            from cores.trading.pumpfun_launch import get_sol_price_usd, scan_pumpfun_launches

            fresh_launches = await scan_pumpfun_launches(sol_price_usd=get_sol_price_usd())
        except Exception:
            pass
        snapshot = {
            "scanned_at": time.time(),
            "count": len(candidates),
            "candidates": [dataclasses.asdict(c) for c in candidates],
            "fresh_launches": fresh_launches[:10],
            "fresh_launches_count": len(fresh_launches),
            "config": dataclasses.asdict(cfg),
        }
        if store is not None:
            _persist(store, cfg.store_key, snapshot)
        else:
            from cores.trading.store import TradingStore

            _persist(TradingStore(), cfg.store_key, snapshot)
        return {"success": True, **snapshot}
    except Exception as exc:
        logger.warning("pump radar cycle failed: %s", exc)
        return {"success": False, "error": str(exc), "count": 0, "candidates": []}


def run_pump_radar_cycle_sync(
    store: Any | None = None,
    cfg: PumpRadarConfig | None = None,
    filter_cfg: FilterConfig | None = None,
) -> dict[str, Any]:
    """Entry sync para scheduler (thread-safe, nunca raisea)."""
    import asyncio

    try:
        return asyncio.run(run_pump_radar_cycle(store=store, cfg=cfg, filter_cfg=filter_cfg))
    except RuntimeError:
        # Ya hay loop (tests): crear uno nuevo en thread
        import threading

        result: dict[str, Any] = {}

        def _run() -> None:
            result.update(asyncio.run(run_pump_radar_cycle(store=store, cfg=cfg, filter_cfg=filter_cfg)))

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=60)
        return result if result else {"success": False, "error": "timeout", "count": 0, "candidates": []}
