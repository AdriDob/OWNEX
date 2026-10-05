"""Hard entry filters for Solana memecoins (v1).

Pure functions over DexScreener pair stats + RugCheck metrics. A pair must
pass EVERY hard rule; soft signals only add warnings. Unknown/missing critical
fields FAIL CLOSED (no data = no trade), except informational fields.

Deliberately NOT used: RugCheck numeric `score` as a threshold (its scale
semantics are undocumented upstream) — it travels as info only. Danger-level
named risks fail; warn-level risks warn.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class FilterConfig:
    min_liquidity_usd: float = 10_000.0
    min_volume_h24_usd: float = 10_000.0
    min_holder_count: int = 50
    max_top10_pct: float = 30.0
    min_pair_age_minutes: float = 5.0
    max_price_impact_pct: float = 5.0
    require_liquidity_locked: bool = True
    require_mint_disabled: bool = True
    require_freeze_disabled: bool = True


@dataclass(frozen=True, slots=True)
class FilterVerdict:
    passed: bool
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    info: dict[str, Any] = field(default_factory=dict)


def _num(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_pair(pair: dict[str, Any]) -> dict[str, Any]:
    """Aplana un par de DexScreener a las claves que lee `evaluate_pair`.

    DexScreener devuelve anidado:
        {"liquidity": {"usd": 30000}, "volume": {"h24": 120000},
         "priceChange": {"h24": 88.5}, "pairCreatedAt": 1700000000000}

    `evaluate_pair` leía `pair["liquidity_usd"]` (plano), así que los radares
    —que le pasaban el dict CRUDO—leansaban `None` en las tres reglas duras y
    `passed_filters` era False SIEMPRE. El bug: los filtros nunca pasaban, y
    ningún test lo cubría (`rg passed_filters tests/` → 0).

    `memecoin_adapter` ya normalizaba antes de llamar, por eso ese path sí
    funcionaba y el radar no. Ahora ambos formatos son válidos.
    """
    out: dict[str, Any] = dict(pair)

    liq = _num((pair.get("liquidity") or {}).get("usd"))
    if liq is not None:
        out["liquidity_usd"] = liq

    vol = _num((pair.get("volume") or {}).get("h24"))
    if vol is not None:
        out["volume_h24"] = vol

    # DexScreener: pairCreatedAt en ms epoch
    created = pair.get("pairCreatedAt")
    if created is not None:
        out["pair_created_at"] = created

    chg = _num((pair.get("priceChange") or {}).get("h24"))
    if chg is not None:
        out["price_change_h24"] = chg

    base = pair.get("baseToken") or {}
    if isinstance(base, dict):
        if base.get("address"):
            out["mint"] = base["address"]
        if base.get("symbol"):
            out["symbol"] = base["symbol"]

    # Si ya venían planas (memecoin_adapter), no romperlas.
    return out


def evaluate_pair(
    pair: dict[str, Any],
    rug: dict[str, Any] | None,
    config: FilterConfig | None = None,
    now_ms: int | None = None,
) -> FilterVerdict:
    """Evaluate one DexScreener pair (+ optional RugCheck) against hard rules.

    Acepta tanto el dict CRUDO de DexScreener (anidado) como el plano que ya
    produce `memecoin_adapter`. Ver `normalize_pair`.
    """
    pair = normalize_pair(pair)
    cfg = config or FilterConfig()
    reasons: list[str] = []
    warnings: list[str] = []
    info: dict[str, Any] = {}

    liq = _num(pair.get("liquidity_usd"))
    if liq is None:
        reasons.append("liquidity unknown (fail closed)")
    elif liq < cfg.min_liquidity_usd:
        reasons.append(f"liquidity ${liq:,.0f} < floor ${cfg.min_liquidity_usd:,.0f}")

    vol = _num(pair.get("volume_h24"))
    if vol is None:
        reasons.append("h24 volume unknown (fail closed)")
    elif vol < cfg.min_volume_h24_usd:
        reasons.append(f"h24 volume ${vol:,.0f} < floor ${cfg.min_volume_h24_usd:,.0f}")

    created = _num(pair.get("pair_created_at"))
    if created is not None and now_ms is not None:
        age_min = (now_ms - created) / 60_000.0
        info["pair_age_minutes"] = round(age_min, 1)
        if age_min < cfg.min_pair_age_minutes:
            reasons.append(f"pair age {age_min:.1f}m < {cfg.min_pair_age_minutes:.0f}m (snipe-risk window)")

    if rug is None:
        reasons.append("no RugCheck report (fail closed)")
        return FilterVerdict(False, tuple(reasons), tuple(warnings), info)
    if rug.get("error"):
        reasons.append(f"RugCheck error: {rug.get('error')}")
        return FilterVerdict(False, tuple(reasons), tuple(warnings), info)

    holders = _num(rug.get("holder_count"))
    if holders is None:
        reasons.append("holder count unknown (fail closed)")
    elif holders < cfg.min_holder_count:
        reasons.append(f"holders {holders:.0f} < {cfg.min_holder_count}")

    top10 = _num(rug.get("top_10_pct"))
    if top10 is None:
        reasons.append("top-10 concentration unknown (fail closed)")
    elif top10 > cfg.max_top10_pct:
        reasons.append(f"top-10 holds {top10:.1f}% > {cfg.max_top10_pct:.0f}%")

    if cfg.require_liquidity_locked and rug.get("liquidity_locked") is not True:
        reasons.append("liquidity not locked")
    if cfg.require_mint_disabled and rug.get("mint_disabled") is not True:
        reasons.append("mint authority still enabled")
    if cfg.require_freeze_disabled and rug.get("freeze_disabled") is not True:
        reasons.append("freeze authority still enabled")

    for risk in rug.get("risks") or []:
        if not isinstance(risk, dict):
            continue
        level = str(risk.get("level", "")).lower()
        name = str(risk.get("name", "unnamed risk"))
        if level == "danger":
            reasons.append(f"rug danger: {name}")
        elif level in ("warn", "warning"):
            warnings.append(f"rug warn: {name}")

    info["rug_score"] = rug.get("score")
    info["boosts_active"] = pair.get("boosts_active", 0)

    return FilterVerdict(not reasons, tuple(reasons), tuple(warnings), info)
