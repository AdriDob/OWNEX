"""Investment Adapters — Registry of exchange and protocol adapters."""

from __future__ import annotations

from typing import Any

from cores.investment.adapters.agent_factory_adapter import (
    AgentFactory,
    AgentSpec,
    AgentInstance,
    AgentType,
    AgentStatus,
    build_agent_factory,
)
from cores.investment.adapters.ccxt_adapter import CCXTAdapter
from cores.investment.adapters.polymarket_adapter import PolymarketAdapter
from cores.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter
from cores.investment.adapters.futures_adapter import FuturesAdapter
from cores.investment.adapters.stocks_adapter import AlpacaAdapter
from cores.investment.adapters.defi_adapter import AaveAdapter
from cores.investment.adapters.memecoin_adapter import MemecoinAdapter


# Stub registry for backward compatibility
class InvestmentAdapterRegistry:
    """Registry of investment adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, Any] = {}

    def register(self, name: str, adapter: Any) -> None:
        self._adapters[name] = adapter

    def get(self, name: str) -> Any | None:
        return self._adapters.get(name)

    def list_adapters(self) -> list[str]:
        return list(self._adapters.keys())


def build_default_registry() -> InvestmentAdapterRegistry:
    """Build default adapter registry with all available adapters."""
    registry = InvestmentAdapterRegistry()
    return registry


def build_aave_adapter() -> AaveAdapter:
    return AaveAdapter()


def build_alpaca_adapter() -> AlpacaAdapter:
    return AlpacaAdapter()


def build_ibkr_adapter() -> Any:
    """Stub for IBKR adapter."""
    return None


def build_lido_adapter() -> Any:
    """Stub for Lido adapter."""
    return None


def build_morpho_adapter() -> Any:
    """Stub for Morpho adapter."""
    return None


def build_pendle_adapter() -> Any:
    """Stub for Pendle adapter."""
    return None


def build_polymarket_adapter() -> PolymarketAdapter:
    return PolymarketAdapter()


__all__ = [
    "AgentFactory",
    "AgentSpec",
    "AgentInstance",
    "AgentType",
    "AgentStatus",
    "build_agent_factory",
    "InvestmentAdapterRegistry",
    "build_default_registry",
    "build_aave_adapter",
    "build_alpaca_adapter",
    "build_ibkr_adapter",
    "build_lido_adapter",
    "CCXTAdapter",
    "PolymarketAdapter",
    "GlobalArbitrageAdapter",
    "FuturesAdapter",
    "AlpacaAdapter",
    "AaveAdapter",
    "MemecoinAdapter",
]
