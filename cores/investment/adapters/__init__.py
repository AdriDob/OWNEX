"""Investment Adapters — Registry of exchange and protocol adapters."""

from __future__ import annotations

from typing import Any

from cores.investment.adapters.agent_factory_adapter import (
    AgentFactory,
    AgentInstance,
    AgentSpec,
    AgentStatus,
    AgentType,
    build_agent_factory,
)
from cores.investment.adapters.ccxt_adapter import CCXTAdapter
from cores.investment.adapters.defi_adapter import AaveAdapter
from cores.investment.adapters.futures_adapter import FuturesAdapter
from cores.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter
from cores.investment.adapters.memecoin_adapter import MemecoinAdapter
from cores.investment.adapters.polymarket_adapter import PolymarketAdapter

# Canonical registry lives in .registry (SSOT, 17+ adapters, lazy imports).
# This package only re-exports it: the stub defined here used to shadow the
# real one, so /api/investment/* got an empty registry (500s).
from cores.investment.adapters.registry import InvestmentAdapterRegistry, build_default_registry
from cores.investment.adapters.stocks_adapter import AlpacaAdapter


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
