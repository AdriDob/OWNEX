"""Investment revenue tasks — wired into the ORION scheduler.

Full-autonomy engines that scan markets and surface deployable edge without
risking real capital (dry-run/paper by default). The validated global
cross-exchange arbitrage engine runs periodically so the system finds and
records real price gaps on its own.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Baseline config for the autonomous scan: inherited adapter defaults are the
# revenue-maximising set (8 exchanges + $500k liquidity floor + sanity cap).
BY_DEFAULT: dict[str, Any] = {}


async def run_global_arbitrage_scan(max_opportunities: int = 10) -> dict[str, Any]:
    """Scan 8 exchanges for cross-exchange price gaps and record the top ones.

    Paper/dry-run only — no real capital is deployed. Returns a summary so the
    scheduler log + event bus expose what the engine found.
    """
    from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

    try:
        adapter = GlobalArbitrageAdapter(config=dict(BY_DEFAULT))
    except Exception as exc:  # pragma: no cover - env oddity
        logger.warning("[INVEST] Arb adapter init failed: %s", exc)
        return {"ok": False, "error": str(exc)}

    opportunities = await adapter.scan_opportunities()

    if not opportunities:
        return {"ok": True, "opportunities": 0, "summary": "Sin oportunidades (mercados eficientes hoy)"}

    opportunities.sort(key=lambda o: o["spread_pct"], reverse=True)
    top = opportunities[:max_opportunities]

    best = top[0]
    logger.info(
        "[INVEST] Arbitraje: %d oportunidades; top %s buy=%s sell=%s spread=%.2f%%",
        len(opportunities),
        best["symbol"],
        best["buy_on"],
        best["sell_on"],
        best["spread_pct"],
    )

    return {
        "ok": True,
        "opportunities": len(opportunities),
        "top": [
            {
                "symbol": o["symbol"],
                "buy_on": o["buy_on"],
                "sell_on": o["sell_on"],
                "spread_pct": o["spread_pct"],
            }
            for o in top
        ],
    }


__all__ = ["run_global_arbitrage_scan"]
