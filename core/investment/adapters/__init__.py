"""Investment Adapters Package for OWNEX.

Unified interface for all investment, trading, and wealth management adapters.
"""

from __future__ import annotations

# Core Exchange Adapters
from core.investment.adapters.ccxt_adapter import CCXTAdapter, build_ccxt_adapter
from core.investment.adapters.forex_adapter import ForexAdapter, build_forex_adapter
from core.investment.adapters.futures_adapter import FuturesAdapter, build_futures_adapter

# Prediction Markets
from core.investment.adapters.polymarket_adapter import PolymarketAdapter, build_polymarket_adapter
from core.investment.adapters.polymarket_clob_adapter import PolymarketCLOBAdapter, build_polymarket_clob_adapter

# Quantitative Research & Backtesting
from core.investment.adapters.freqtrade_adapter import FreqtradeAdapter, build_freqtrade_adapter
from core.investment.adapters.hummingbot_adapter import HummingbotAdapter, build_hummingbot_adapter
from core.investment.adapters.quant_research_adapter import (
    VectorBTAdapter,
    BacktraderAdapter,
    build_vectorbt_adapter,
    build_backtrader_adapter,
)

# Scanners & Analytics
from core.investment.adapters.memecoin_adapter import MemecoinAdapter, build_memecoin_adapter
from core.investment.adapters.memecoin_scanner_adapter import MemecoinScannerAdapter, build_memecoin_scanner_adapter
from core.investment.adapters.onchain_analytics_adapter import OnChainAnalyticsAdapter, build_onchain_analytics_adapter
from core.investment.adapters.sentiment_adapter import SentimentAnalyzerAdapter, build_sentiment_adapter

# Arbitrage & Specialized
from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter, build_global_arbitrage_adapter
from core.investment.adapters.sports_betting_adapter import SportsBettingAdapter, build_sports_betting_adapter

# AI Agent Factory
from core.investment.adapters.agent_factory_adapter import (
    AgentFactory,
    AgentType,
    AgentStatus,
    AgentSpec,
    AgentInstance,
    build_agent_factory,
)

# Registry
from core.investment.adapters.registry import (
    InvestmentAdapterRegistry,
    build_default_registry,
)

__all__ = [
    # Core Exchange
    "CCXTAdapter",
    "build_ccxt_adapter",
    "ForexAdapter",
    "build_forex_adapter",
    "FuturesAdapter",
    "build_futures_adapter",
    # Prediction Markets
    "PolymarketAdapter",
    "build_polymarket_adapter",
    "PolymarketCLOBAdapter",
    "build_polymarket_clob_adapter",
    # Quant Research
    "FreqtradeAdapter",
    "build_freqtrade_adapter",
    "HummingbotAdapter",
    "build_hummingbot_adapter",
    "VectorBTAdapter",
    "build_vectorbt_adapter",
    "BacktraderAdapter",
    "build_backtrader_adapter",
    # Scanners & Analytics
    "MemecoinAdapter",
    "build_memecoin_adapter",
    "MemecoinScannerAdapter",
    "build_memecoin_scanner_adapter",
    "OnChainAnalyticsAdapter",
    "build_onchain_analytics_adapter",
    "SentimentAnalyzerAdapter",
    "build_sentiment_adapter",
    # Arbitrage & Specialized
    "GlobalArbitrageAdapter",
    "build_global_arbitrage_adapter",
    "SportsBettingAdapter",
    "build_sports_betting_adapter",
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
