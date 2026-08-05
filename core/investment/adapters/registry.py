"""Investment Adapters Registry for OWNEX.

Central registry connecting all investment adapters to the InvestmentManager
and strategic agents. Provides unified interface for all investment operations.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

logger = logging.getLogger("orion.investment.adapters.registry")


class InvestmentAdapterRegistry:
    """Registry for all investment adapters.

    Manages lifecycle, configuration, and unified access to all
    investment adapters (exchanges, analytics, strategies, etc.).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._adapters: dict[str, Any] = {}
        self._adapter_configs: dict[str, dict[str, Any]] = {}
        self._initialized = False

    def register_adapter(
        self,
        name: str,
        adapter_class_path: str,
        config: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> None:
        """Register an adapter class with configuration."""
        self._adapter_configs[name] = {
            "class_path": adapter_class_path,
            "config": config or {},
            "enabled": enabled,
        }
        logger.debug("Registered adapter: %s (enabled=%s)", name, enabled)

    def _import_class(self, class_path: str) -> type | None:
        """Dynamically import a class from its path."""
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except Exception as e:
            logger.error("Failed to import %s: %s", class_path, e)
            return None

    async def initialize_all(self) -> dict[str, bool]:
        """Initialize all registered and enabled adapters."""
        results = {}

        for name, info in self._adapter_configs.items():
            if not info["enabled"]:
                results[name] = False
                continue

            try:
                adapter_class = self._import_class(info["class_path"])
                if adapter_class is None:
                    results[name] = False
                    continue

                adapter = adapter_class(info["config"])
                if hasattr(adapter, "initialize"):
                    success = await adapter.initialize()
                else:
                    success = True

                if success:
                    self._adapters[name] = adapter
                    logger.info("Initialized adapter: %s", name)
                else:
                    logger.warning("Adapter initialization failed: %s", name)

                results[name] = success
            except Exception as e:
                logger.error("Failed to initialize adapter %s: %s", name, e)
                results[name] = False

        self._initialized = True
        return results

    def get_adapter(self, name: str) -> Any | None:
        """Get an initialized adapter by name."""
        return self._adapters.get(name)

    def get_all_adapters(self) -> dict[str, Any]:
        """Get all initialized adapters."""
        return self._adapters.copy()

    def list_adapters(self) -> list[dict[str, Any]]:
        """List all registered adapters with status."""
        return [
            {
                "name": name,
                "enabled": info["enabled"],
                "initialized": name in self._adapters,
                "class_path": info["class_path"],
            }
            for name, info in self._adapter_configs.items()
        ]

    async def shutdown_all(self) -> None:
        """Shutdown all adapters gracefully."""
        for name, adapter in self._adapters.items():
            try:
                if hasattr(adapter, "close"):
                    await adapter.close()
                elif hasattr(adapter, "disconnect"):
                    await adapter.disconnect()
                elif hasattr(adapter, "stop_all"):
                    await adapter.stop_all()
                logger.debug("Shutdown adapter: %s", name)
            except Exception as e:
                logger.warning("Error shutting down adapter %s: %s", name, e)

    # Convenience methods for common operations
    async def get_market_data(
        self,
        symbols: list[str],
        source: str = "ccxt",
    ) -> dict[str, Any]:
        """Get market data from specified source."""
        adapter = self._adapters.get(source)
        if not adapter:
            return {"error": f"Adapter {source} not available"}

        if hasattr(adapter, "get_ticker"):
            results = {}
            for symbol in symbols:
                results[symbol] = await adapter.get_ticker(symbol)
            return results
        return {"error": "Adapter does not support market data"}

    async def run_backtest(
        self,
        strategy: str,
        engine: str = "vectorbt",
        **kwargs,
    ) -> dict[str, Any]:
        """Run backtest using specified engine."""
        adapter = self._adapters.get(engine)
        if not adapter:
            return {"error": f"Backtest engine {engine} not available"}

        if hasattr(adapter, "run_backtest"):
            return await adapter.run_backtest(strategy, **kwargs)
        return {"error": "Adapter does not support backtesting"}

    async def scan_opportunities(
        self,
        scanner: str = "memecoin",
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Scan for opportunities using specified scanner."""
        adapter = self._adapters.get(scanner)
        if not adapter:
            return []

        if hasattr(adapter, "scan_opportunities"):
            return await adapter.scan_opportunities(**kwargs)
        elif hasattr(adapter, "get_new_pairs"):
            return await adapter.get_new_pairs(**kwargs)
        return []

    async def analyze_wallet(
        self,
        address: str,
        chain: str = "ethereum",
    ) -> dict[str, Any]:
        """Analyze wallet using on-chain analytics."""
        adapter = self._adapters.get("onchain_analytics")
        if not adapter:
            return {"error": "On-chain analytics not available"}

        if hasattr(adapter, "analyze_wallet"):
            return await adapter.analyze_wallet(address, chain)
        return {"error": "Wallet analysis not supported"}

    async def get_quant_analysis(
        self,
        symbols: list[str],
        analysis_type: str = "indicators",
    ) -> dict[str, Any]:
        """Get quantitative analysis."""
        adapter = self._adapters.get("quant_research")
        if not adapter:
            return {"error": "Quant research not available"}

        if analysis_type == "indicators" and hasattr(adapter, "compute_indicators"):
            return {"error": "Need price data first"}
        return {"error": "Analysis type not supported"}


def build_default_registry(config: dict[str, Any] | None = None) -> InvestmentAdapterRegistry:
    """Build the default investment adapter registry with all adapters."""

    registry = InvestmentAdapterRegistry(config)

    # Core exchange adapters
    registry.register_adapter(
        "ccxt",
        "core.investment.adapters.ccxt_adapter.CCXTAdapter",
        config=config.get("ccxt", {}) if config else {},
        enabled=True,
    )

    registry.register_adapter(
        "freqtrade",
        "core.investment.adapters.freqtrade_adapter.FreqtradeAdapter",
        config=config.get("freqtrade", {}) if config else {},
        enabled=True,
    )

    registry.register_adapter(
        "hummingbot",
        "core.investment.adapters.hummingbot_adapter.HummingbotAdapter",
        config=config.get("hummingbot", {}) if config else {},
        enabled=True,
    )

    # Prediction markets
    registry.register_adapter(
        "polymarket_clob",
        "core.investment.adapters.polymarket_clob_adapter.PolymarketCLOBAdapter",
        config=config.get("polymarket_clob", {}) if config else {},
        enabled=True,
    )

    registry.register_adapter(
        "polymarket",
        "core.investment.adapters.polymarket_adapter.PolymarketAdapter",
        config=config.get("polymarket", {}) if config else {},
        enabled=True,
    )

    # Quant research
    registry.register_adapter(
        "quant_research",
        "core.investment.adapters.quant_research_adapter.VectorBTAdapter",
        config=config.get("vectorbt", {}) if config else {},
        enabled=True,
    )

    registry.register_adapter(
        "backtrader",
        "core.investment.adapters.quant_research_adapter.BacktraderAdapter",
        config=config.get("backtrader", {}) if config else {},
        enabled=True,
    )

    # Scanners
    registry.register_adapter(
        "memecoin_scanner",
        "core.investment.adapters.memecoin_scanner_adapter.MemecoinScannerAdapter",
        config=config.get("memecoin_scanner", {}) if config else {},
        enabled=True,
    )

    # Analytics
    registry.register_adapter(
        "onchain_analytics",
        "core.investment.adapters.onchain_analytics_adapter.OnChainAnalyticsAdapter",
        config=config.get("onchain_analytics", {}) if config else {},
        enabled=True,
    )

    registry.register_adapter(
        "sentiment",
        "core.investment.adapters.sentiment_adapter.SentimentAnalyzerAdapter",
        config=config.get("sentiment", {}) if config else {},
        enabled=True,
    )

    # Existing adapters
    registry.register_adapter(
        "forex",
        "core.investment.adapters.forex_adapter.ForexAdapter",
        config=config.get("forex", {}) if config else {},
        enabled=True,
    )

    registry.register_adapter(
        "futures",
        "core.investment.adapters.futures_adapter.FuturesAdapter",
        config=config.get("futures", {}) if config else {},
        enabled=True,
    )

    registry.register_adapter(
        "global_arbitrage",
        "core.investment.adapters.global_arbitrage_adapter.GlobalArbitrageAdapter",
        config=config.get("global_arbitrage", {}) if config else {},
        enabled=True,
    )

    registry.register_adapter(
        "sports_betting",
        "core.investment.adapters.sports_betting_adapter.SportsBettingAdapter",
        config=config.get("sports_betting", {}) if config else {},
        enabled=True,
    )

    return registry


def build_default_registry(config: dict[str, Any] | None = None) -> InvestmentAdapterRegistry:
    """Build a default InvestmentAdapterRegistry with common adapters registered."""
    registry = InvestmentAdapterRegistry(config=config)

    # Register core adapters
    registry.register_adapter(
        "ccxt",
        "core.investment.adapters.ccxt_adapter.CCXTAdapter",
        config.get("ccxt", {}) if config else {},
    )
    registry.register_adapter(
        "forex",
        "core.investment.adapters.forex_adapter.ForexAdapter",
        config.get("forex", {}) if config else {},
    )
    registry.register_adapter(
        "futures",
        "core.investment.adapters.futures_adapter.FuturesAdapter",
        config.get("futures", {}) if config else {},
    )
    registry.register_adapter(
        "polymarket",
        "core.investment.adapters.polymarket_adapter.PolymarketAdapter",
        config.get("polymarket", {}) if config else {},
    )
    registry.register_adapter(
        "polymarket_clob",
        "core.investment.adapters.polymarket_clob_adapter.PolymarketCLOBAdapter",
        config.get("polymarket_clob", {}) if config else {},
    )
    registry.register_adapter(
        "freqtrade",
        "core.investment.adapters.freqtrade_adapter.FreqtradeAdapter",
        config.get("freqtrade", {}) if config else {},
    )
    registry.register_adapter(
        "hummingbot",
        "core.investment.adapters.hummingbot_adapter.HummingbotAdapter",
        config.get("hummingbot", {}) if config else {},
    )
    registry.register_adapter(
        "vectorbt",
        "core.investment.adapters.quant_research_adapter.VectorBTAdapter",
        config.get("vectorbt", {}) if config else {},
    )
    registry.register_adapter(
        "backtrader",
        "core.investment.adapters.quant_research_adapter.BacktraderAdapter",
        config.get("backtrader", {}) if config else {},
    )
    registry.register_adapter(
        "memecoin",
        "core.investment.adapters.memecoin_adapter.MemecoinAdapter",
        config.get("memecoin", {}) if config else {},
    )
    registry.register_adapter(
        "memecoin_scanner",
        "core.investment.adapters.memecoin_scanner_adapter.MemecoinScannerAdapter",
        config.get("memecoin_scanner", {}) if config else {},
    )
    registry.register_adapter(
        "onchain_analytics",
        "core.investment.adapters.onchain_analytics_adapter.OnChainAnalyticsAdapter",
        config.get("onchain_analytics", {}) if config else {},
    )
    registry.register_adapter(
        "sentiment",
        "core.investment.adapters.sentiment_adapter.SentimentAnalyzerAdapter",
        config.get("sentiment", {}) if config else {},
    )
    registry.register_adapter(
        "global_arbitrage",
        "core.investment.adapters.global_arbitrage_adapter.GlobalArbitrageAdapter",
        config.get("global_arbitrage", {}) if config else {},
    )
    registry.register_adapter(
        "sports_betting",
        "core.investment.adapters.sports_betting_adapter.SportsBettingAdapter",
        config.get("sports_betting", {}) if config else {},
    )
    registry.register_adapter(
        "agent_factory",
        "core.investment.adapters.agent_factory_adapter.AgentFactory",
        config.get("agent_factory", {}) if config else {},
    )

    return registry
