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
