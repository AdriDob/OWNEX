"""Los hard filters de pump/dip NUNCA pasaban. Ahora sí.

Por qué existe (auditoría 2026-10-05):

`evaluate_pair()` leía claves PLANAS del par:

    liq     = _num(pair.get("liquidity_usd"))
    vol     = _num(pair.get("volume_h24"))
    created = _num(pair.get("pair_created_at"))

Pero `pump_radar` y `extra_radars` le pasaban el dict **crudo** de
DexScreener, que es ANIDADO:

    {"liquidity": {"usd": 30000}, "volume": {"h24": 120000},
     "pairCreatedAt": 1700000000000, "baseToken": {...}}

Las tres reglas duras leían `None` → "unknown (fail closed)" → `passed=False`
**en el 100% de los candidatos, siempre**. El radar corría cada 5 minutos
contra DexScreener, rankeaba por `pump_score` (que sí leía anidado), y
devolvía una lista donde NADA era apto.

`memecoin_adapter` normalizaba antes de llamar, por eso ese path sí
funcionaba — y por eso el bug pasó desapercibido: un test con dict plano
pasaba mientras el radar real fallaba. `rg "passed_filters" tests/` → 0.

Estos tests usan las formas REALES de ambas APIs.
"""

from __future__ import annotations

import time

from cores.trading.strategies.memecoin_filters import (
    FilterConfig,
    evaluate_pair,
    normalize_pair,
)

# Forma REAL de DexScreener (anidado)
DEXSCREENER_GOOD = {
    "baseToken": {"address": "So11111111111111111111111111111111111111112", "symbol": "GOOD"},
    "liquidity": {"usd": 30_000},
    "volume": {"h24": 120_000},
    "priceChange": {"h24": 88.5},
    "pairCreatedAt": int((time.time() - 3600) * 1000),
    "boosts": {"active": 0},
    "dexId": "pumpswap",
}

# Forma REAL que devuelve _fetch_rugcheck (ya normalizada)
RUGCHECK_GOOD = {
    "holder_count": 450,
    "top_10_pct": 18.0,
    "liquidity_locked": True,
    "mint_disabled": True,
    "freeze_disabled": True,
    "score": 20,
    "risks": [],
}


def _now_ms() -> int:
    return int(time.time() * 1000)


class TestNormalizePair:
    def test_aplana_liquidity_y_volume_anidados(self) -> None:
        out = normalize_pair(DEXSCREENER_GOOD)
        assert out["liquidity_usd"] == 30_000
        assert out["volume_h24"] == 120_000
        assert out["price_change_h24"] == 88.5
        assert out["pair_created_at"] == DEXSCREENER_GOOD["pairCreatedAt"]
        assert out["mint"] == "So11111111111111111111111111111111111111112"
        assert out["symbol"] == "GOOD"

    def test_no_rompe_un_dict_ya_plano(self) -> None:
        """memecoin_adapter ya pasaba plano; no debe romperse."""
        plano = {
            "liquidity_usd": 30_000,
            "volume_h24": 120_000,
            "pair_created_at": DEXSCREENER_GOOD["pairCreatedAt"],
            "mint": "M",
            "symbol": "S",
        }
        out = normalize_pair(plano)
        assert out["liquidity_usd"] == 30_000
        assert out["volume_h24"] == 120_000
        assert out["symbol"] == "S"

    def test_no_inventa_valores_si_falta_el_anidado(self) -> None:
        out = normalize_pair({"baseToken": {"address": "M"}})
        assert "liquidity_usd" not in out
        assert "volume_h24" not in out

    def test_copia_el_rug_dict_en_lugar_de_aliasearlo(self) -> None:
        """asdict debe COPIAR; si compartiera el dict, mutar uno muta el otro."""
        out = normalize_pair(DEXSCREENER_GOOD)
        assert out is not DEXSCREENER_GOOD


class TestHardFiltersCanPass:
    def test_un_par_bueno_crudo_pasa_los_filtros(self) -> None:
        """El bug: esto daba False SIEMPRE."""
        v = evaluate_pair(DEXSCREENER_GOOD, RUGCHECK_GOOD, FilterConfig(), now_ms=_now_ms())
        assert v.passed is True, f"debería pasar; reasons={v.reasons}"

    def test_liquidez_baja_lo_rechaza(self) -> None:
        par = {**DEXSCREENER_GOOD, "liquidity": {"usd": 500}}
        v = evaluate_pair(par, RUGCHECK_GOOD, FilterConfig(), now_ms=_now_ms())
        assert v.passed is False
        assert any("liquidity" in r and "500" in r for r in v.reasons), v.reasons

    def test_volumen_bajo_lo_rechaza(self) -> None:
        par = {**DEXSCREENER_GOOD, "volume": {"h24": 100}}
        v = evaluate_pair(par, RUGCHECK_GOOD, FilterConfig(), now_ms=_now_ms())
        assert v.passed is False
        assert any("volume" in r for r in v.reasons), v.reasons

    def test_sin_rugcheck_rechaza_fail_closed(self) -> None:
        """Fail-closed se mantiene: sin datos de rug NO se aprueba."""
        v = evaluate_pair(DEXSCREENER_GOOD, None, FilterConfig(), now_ms=_now_ms())
        assert v.passed is False
        assert any("RugCheck" in r for r in v.reasons)

    def test_rug_danger_rechaza(self) -> None:
        rug = {**RUGCHECK_GOOD, "risks": [{"level": "danger", "name": "Mint authority enabled"}]}
        v = evaluate_pair(DEXSCREENER_GOOD, rug, FilterConfig(), now_ms=_now_ms())
        assert v.passed is False
        assert any("rug danger" in r for r in v.reasons)

    def test_top10_concentrado_rechaza(self) -> None:
        rug = {**RUGCHECK_GOOD, "top_10_pct": 85.0}
        v = evaluate_pair(DEXSCREENER_GOOD, rug, FilterConfig(), now_ms=_now_ms())
        assert v.passed is False
        assert any("top-10" in r for r in v.reasons)

    def test_sniper_window_rechaza(self) -> None:
        """Un par de 1 minuto es snipe-risk."""
        par = {**DEXSCREENER_GOOD, "pairCreatedAt": int((time.time() - 30) * 1000)}
        v = evaluate_pair(par, RUGCHECK_GOOD, FilterConfig(), now_ms=_now_ms())
        assert v.passed is False
        assert any("snipe-risk" in r for r in v.reasons), v.reasons

    def test_dict_plano_tambien_pasa(self) -> None:
        """El path de memecoin_adapter sigue funcionando."""
        plano = {
            "liquidity_usd": 30_000,
            "volume_h24": 120_000,
            "pair_created_at": int((time.time() - 3600) * 1000),
        }
        v = evaluate_pair(plano, RUGCHECK_GOOD, FilterConfig(), now_ms=_now_ms())
        assert v.passed is True, f"el path plano también debe pasar; reasons={v.reasons}"
