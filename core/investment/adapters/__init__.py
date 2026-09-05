"""Investment Adapters Package for OWNEX.

Unified interface for all investment, trading, and wealth management adapters.
"""

from __future__ import annotations

# AI Agent Factory
from core.investment.adapters.agent_factory_adapter import (
    AgentFactory,
    AgentInstance,
    AgentSpec,
    AgentStatus,
    AgentType,
    build_agent_factory,
)

# Core Exchange Adapters
from core.investment.adapters.ccxt_adapter import CCXTAdapter, build_ccxt_adapter

# DeFi Yield
from core.investment.adapters.defi_adapter import (
    AaveAdapter,
    LidoAdapter,
    MorphoAdapter,
    PendleAdapter,
    build_aave_adapter,
    build_lido_adapter,
    build_morpho_adapter,
    build_pendle_adapter,
)

# Arbitrage & Specialized
from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter, build_global_arbitrage_adapter

# Prediction Markets
from core.investment.adapters.polymarket_adapter import PolymarketAdapter, build_polymarket_adapter

# Registry
from core.investment.adapters.registry import (
    InvestmentAdapterRegistry,
    build_default_registry,
)

# Stocks & Options
from core.investment.adapters.stocks_adapter import (
    AlpacaAdapter,
    IBKRAdapter,
    build_alpaca_adapter,
    build_ibkr_adapter,
)

__all__ = [
    # Core Exchange
    "CCXTAdapter",
    "build_ccxt_adapter",
    # DeFi Yield
    "AaveAdapter",
    "build_aave_adapter",
    "MorphoAdapter",
    "build_morpho_adapter",
    "PendleAdapter",
    "build_pendle_adapter",
    "LidoAdapter",
    "build_lido_adapter",
    # Arbitrage & Specialized
    "GlobalArbitrageAdapter",
    "build_global_arbitrage_adapter",
    # Prediction Markets
    "PolymarketAdapter",
    "build_polymarket_adapter",
    # Stocks & Options
    "AlpacaAdapter",
    "build_alpaca_adapter",
    "IBKRAdapter",
    "build_ibkr_adapter",
    # AI Agent Factory
    "AgentFactory",
    "AgentType",
    "AgentStatus",
    "AgentSpec",
    "AgentInstance",
    "build_agent_factory",
    # Registry
    "InvestmentAdapterRegistry",
    "build_default_registry",
]
