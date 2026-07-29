from __future__ import annotations

import logging
from typing import Any

from core.polymarket.strategies import (
    BTCArbitrageStrategy,
    CompleteSetArbitrage,
    PolymarketLPMarketMaker,
    SmartMoneyCopier,
    WeatherMarketStrategy,
)

logger = logging.getLogger("orion.polymarket.manager")

_STRATEGY_MAP: dict[str, type] = {
    "btc_arb": BTCArbitrageStrategy,
    "smart_money": SmartMoneyCopier,
    "complete_arb": CompleteSetArbitrage,
    "weather": WeatherMarketStrategy,
    "lp_mm": PolymarketLPMarketMaker,
}


def list_strategies() -> dict[str, str]:
    return {k: v.__doc__.split("\n")[0] if v.__doc__ else "" for k, v in _STRATEGY_MAP.items()}


def get_strategy(name: str, config: dict[str, Any] | None = None) -> Any:
    cls = _STRATEGY_MAP.get(name)
    if not cls:
        msg = f"Unknown strategy '{name}'. Available: {', '.join(_STRATEGY_MAP)}"
        raise ValueError(msg)
    return cls(config or {})


class PolymarketManager:
    """Unified frontend for all Polymarket strategies."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._strategies: dict[str, Any] = {}

    def get_strategy(self, name: str) -> Any:
        if name not in self._strategies:
            self._strategies[name] = get_strategy(name, self._config.get(name))
        return self._strategies[name]

    async def run_scan(self, strategy: str) -> dict[str, Any]:
        inst = self.get_strategy(strategy)
        if hasattr(inst, "scan_opportunity"):
            return await inst.scan_opportunity()
        if hasattr(inst, "scan_opportunities"):
            return {"opportunities": await inst.scan_opportunities()}
        if hasattr(inst, "generate_copy_signals"):
            return {"signals": await inst.generate_copy_signals()}
        if hasattr(inst, "fetch_temperature"):
            return {"weather": await inst.fetch_temperature()}
        return {"error": f"Strategy '{strategy}' has no scan method"}

    async def full_diagnostic(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for name in _STRATEGY_MAP:
            inst = self.get_strategy(name)
            if hasattr(inst, "check_setup"):
                results[name] = await inst.check_setup()
            elif name == "weather":
                results[name] = {"data": await inst.fetch_temperature()}
            elif name == "complete_arb":
                results[name] = {"opportunities": await inst.scan_opportunities(limit=20)}
            elif name == "smart_money":
                results[name] = {"traders": await inst.scan_top_traders(limit=5)}
            elif name == "lp_mm":
                results[name] = await inst.summary()
            else:
                results[name] = {"status": "available"}
        return results
