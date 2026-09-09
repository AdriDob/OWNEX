from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("orion.investment.models")


class StrategyType(StrEnum):
    CRYPTO_SPOT = "crypto_spot"
    CRYPTO_FUTURES = "crypto_futures"
    CRYPTO_DEFI = "crypto_defi"
    MEMECOIN = "memecoin"
    POLYMARKET = "polymarket"
    SPORTS_BETTING = "sports_betting"
    ARBITRAGE = "arbitrage"
    GLOBAL_ARBITRAGE = "global_arbitrage"
    STOCKS = "stocks"
    FOREX = "forex"
    STOCKS_OPTIONS = "stocks_options"
    DEFI_LENDING = "defi_lending"
    DEFI_YIELD = "defi_yield"
    DEFI_LIQUID_STAKING = "defi_liquid_staking"


class RiskLevel(StrEnum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"


class StrategyStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    DRAWDOWN = "drawdown"


@dataclass
class StrategyProfile:
    id: str
    name: str
    strategy_type: StrategyType
    risk_level: RiskLevel
    max_allocation_pct: float
    current_allocation_pct: float = 0.0
    status: StrategyStatus = StrategyStatus.ACTIVE
    expected_roi_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_target: float = 0.0
    win_rate_target: float = 0.0
    requires_api_keys: bool = False
    adapter_module: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class AllocationConfig:
    total_capital_usd: float = 0.0
    max_high_risk_pct: float = 25.0
    max_speculative_pct: float = 10.0
    emergency_reserve_pct: float = 5.0
    auto_rebalance: bool = True
    rebalance_threshold_pct: float = 5.0
    min_strategy_allocation_usd: float = 50.0

    def max_high_risk_amount(self) -> float:
        return self.total_capital_usd * (self.max_high_risk_pct / 100.0)

    def max_speculative_amount(self) -> float:
        return self.total_capital_usd * (self.max_speculative_pct / 100.0)

    def emergency_reserve_amount(self) -> float:
        return self.total_capital_usd * (self.emergency_reserve_pct / 100.0)

    def available_for_investment(self) -> float:
        return self.total_capital_usd - self.emergency_reserve_amount()


@dataclass
class RiskMetrics:
    strategy_id: str
    current_drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    current_streak: int = 0
    best_streak: int = 0
    worst_streak: int = 0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    var_95_pct: float = 0.0
    is_drawdown: bool = False
    consecutive_losses: int = 0

    @property
    def is_healthy(self) -> bool:
        return self.current_drawdown_pct < self.max_drawdown_pct * 0.8 if self.max_drawdown_pct > 0 else True

    @property
    def should_pause(self) -> bool:
        if self.max_drawdown_pct <= 0:
            return self.consecutive_losses >= 5
        return self.current_drawdown_pct >= self.max_drawdown_pct * 0.9 or self.consecutive_losses >= 5


@dataclass
class StrategyAllocation:
    strategy_id: str
    allocated_usd: float = 0.0
    deployed_usd: float = 0.0
    available_usd: float = 0.0
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    roi_pct: float = 0.0
    last_rebalanced: str = ""


@dataclass
class InvestmentSnapshot:
    total_capital: float = 0.0
    deployed: float = 0.0
    available: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    strategies: dict[str, StrategyAllocation] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_capital": round(self.total_capital, 2),
            "deployed": round(self.deployed, 2),
            "available": round(self.available, 2),
            "total_pnl": round(self.total_pnl, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "deployment_rate": round(self.deployed / max(self.total_capital, 1) * 100, 1),
            "strategies": {k: v.__dict__ for k, v in self.strategies.items()},
            "timestamp": self.timestamp,
        }


@dataclass
class InvestmentEvent:
    event_type: str
    strategy_id: str
    amount: float
    currency: str = "USD"
    description: str = ""
    pnl: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


STRATEGY_REGISTRY: list[StrategyProfile] = [
    StrategyProfile(
        id="ccxt_spot",
        name="CCXT Spot Trading",
        strategy_type=StrategyType.CRYPTO_SPOT,
        risk_level=RiskLevel.MODERATE,
        max_allocation_pct=40.0,
        expected_roi_pct=15.0,
        max_drawdown_pct=20.0,
        sharpe_target=1.0,
        win_rate_target=55.0,
        requires_api_keys=True,
        adapter_module="core.investment.adapters.ccxt_adapter",
        description="Unified spot trading across 100+ exchanges via CCXT. Grid, DCA, and momentum strategies.",
        tags=["crypto", "exchange", "spot"],
    ),
    StrategyProfile(
        id="polymarket",
        name="Polymarket Prediction Markets",
        strategy_type=StrategyType.POLYMARKET,
        risk_level=RiskLevel.SPECULATIVE,
        max_allocation_pct=25.0,
        expected_roi_pct=40.0,
        max_drawdown_pct=35.0,
        sharpe_target=0.8,
        win_rate_target=45.0,
        requires_api_keys=True,
        adapter_module="core.investment.adapters.polymarket_adapter",
        description="Prediction market arbitrage and sniping on Polymarket CLOB. Copy-trading + market-making bots.",
        tags=["prediction", "polymarket", "arbitrage"],
    ),
    StrategyProfile(
        id="global_arbitrage",
        name="Global Arbitrage Engine",
        strategy_type=StrategyType.GLOBAL_ARBITRAGE,
        risk_level=RiskLevel.MODERATE,
        max_allocation_pct=45.0,
        expected_roi_pct=25.0,
        max_drawdown_pct=15.0,
        sharpe_target=1.5,
        win_rate_target=60.0,
        requires_api_keys=False,
        adapter_module="core.investment.adapters.global_arbitrage_adapter",
        description="Cross-exchange crypto spot arbitrage via CCXT (8 exchanges). Nightly scan finds real price gaps (e.g. ZIL binance↔mexc ~8%).",
        tags=["arbitrage", "cross-border", "ecommerce"],
    ),
    StrategyProfile(
        id="sports_betting",
        name="Sports Betting Value",
        strategy_type=StrategyType.SPORTS_BETTING,
        risk_level=RiskLevel.AGGRESSIVE,
        max_allocation_pct=15.0,
        expected_roi_pct=20.0,
        max_drawdown_pct=25.0,
        sharpe_target=0.7,
        win_rate_target=50.0,
        requires_api_keys=True,
        adapter_module="core.investment.adapters.sports_betting_adapter",
        description="Value betting with ML models. Kelly Criterion sizing. Betfair via Flumine framework.",
        tags=["sports", "betting", "kelly"],
    ),
    StrategyProfile(
        id="memecoin",
        name="Memecoin Sniping",
        strategy_type=StrategyType.MEMECOIN,
        risk_level=RiskLevel.SPECULATIVE,
        max_allocation_pct=10.0,
        expected_roi_pct=100.0,
        max_drawdown_pct=50.0,
        sharpe_target=0.3,
        win_rate_target=30.0,
        requires_api_keys=True,
        adapter_module="core.investment.adapters.memecoin_adapter",
        description="Solana memecoin sniping on PumpFun/Raydium. High risk, high reward. Strict drawdown limits.",
        tags=["memecoin", "solana", "sniper"],
    ),
    StrategyProfile(
        id="futures",
        name="Crypto Futures",
        strategy_type=StrategyType.CRYPTO_FUTURES,
        risk_level=RiskLevel.AGGRESSIVE,
        max_allocation_pct=20.0,
        expected_roi_pct=35.0,
        max_drawdown_pct=30.0,
        sharpe_target=0.9,
        win_rate_target=50.0,
        requires_api_keys=True,
        adapter_module="core.investment.adapters.futures_adapter",
        description="Perpetual swap trading via CCXT. Cross/isolated margin, leverage management, position tracking.",
        tags=["crypto", "futures", "leverage"],
    ),
    StrategyProfile(
        id="forex",
        name="Forex Trading",
        strategy_type=StrategyType.FOREX,
        risk_level=RiskLevel.MODERATE,
        max_allocation_pct=15.0,
        expected_roi_pct=12.0,
        max_drawdown_pct=15.0,
        sharpe_target=1.2,
        win_rate_target=55.0,
        requires_api_keys=True,
        adapter_module="core.investment.adapters.forex_adapter",
        description="Currency pair trading via OANDA v20 API. SL/TP, position tracking, major pairs coverage.",
        tags=["forex", "currency", "oanda"],
    ),
    StrategyProfile(
        id="polymarket_btc_arb",
        name="Polymarket BTC Latency Arb",
        strategy_type=StrategyType.POLYMARKET,
        risk_level=RiskLevel.SPECULATIVE,
        max_allocation_pct=5.0,
        expected_roi_pct=60.0,
        max_drawdown_pct=20.0,
        sharpe_target=1.2,
        win_rate_target=55.0,
        requires_api_keys=False,
        adapter_module="core.polymarket.strategies",
        description="Binance→Polymarket BTC latency arbitrage. Detects 1s micro-moves on Binance, enters Polymarket 5m before price catches up. ClawdBot/AdiiX thesis.",
        tags=["polymarket", "btc", "arbitrage", "latency"],
    ),
    StrategyProfile(
        id="polymarket_smart_money",
        name="Polymarket Smart Money Copy",
        strategy_type=StrategyType.POLYMARKET,
        risk_level=RiskLevel.MODERATE,
        max_allocation_pct=10.0,
        expected_roi_pct=30.0,
        max_drawdown_pct=15.0,
        sharpe_target=1.0,
        win_rate_target=50.0,
        requires_api_keys=False,
        adapter_module="core.polymarket.strategies",
        description="Copy trade signals from top Polymarket traders filtered by PnL and win rate. Inspired by MrFadiAi and polybot.",
        tags=["polymarket", "copy-trading", "smart-money"],
    ),
    StrategyProfile(
        id="polymarket_complete_arb",
        name="Polymarket Complete-Set Arb",
        strategy_type=StrategyType.POLYMARKET,
        risk_level=RiskLevel.CONSERVATIVE,
        max_allocation_pct=15.0,
        expected_roi_pct=15.0,
        max_drawdown_pct=5.0,
        sharpe_target=2.0,
        win_rate_target=70.0,
        requires_api_keys=False,
        adapter_module="core.polymarket.strategies",
        description="Complete-set arbitrage: buy/sell complete sets when YES+NO prices diverge from 1.0. Low-risk, high-frequency. Based on polybot.",
        tags=["polymarket", "arbitrage", "complete-set"],
    ),
    StrategyProfile(
        id="polymarket_weather",
        name="Polymarket Weather Prediction",
        strategy_type=StrategyType.POLYMARKET,
        risk_level=RiskLevel.MODERATE,
        max_allocation_pct=10.0,
        expected_roi_pct=25.0,
        max_drawdown_pct=10.0,
        sharpe_target=1.5,
        win_rate_target=60.0,
        requires_api_keys=False,
        adapter_module="core.polymarket.strategies",
        description="Temperature settlement prediction using Open-Meteo + METAR data. Based on PolyWeather bot.",
        tags=["polymarket", "weather", "forecast"],
    ),
    StrategyProfile(
        id="polymarket_lp",
        name="Polymarket LP Market Making",
        strategy_type=StrategyType.POLYMARKET,
        risk_level=RiskLevel.CONSERVATIVE,
        max_allocation_pct=20.0,
        expected_roi_pct=10.0,
        max_drawdown_pct=5.0,
        sharpe_target=1.8,
        win_rate_target=65.0,
        requires_api_keys=True,
        adapter_module="core.polymarket.strategies",
        description="Passive market making for Polymarket liquidity rewards. Places limit orders at calculated spreads. Based on polymarket_lp_tool.",
        tags=["polymarket", "lp", "market-making"],
    ),
    StrategyProfile(
        id="alpaca_stocks",
        name="Alpaca Stock Trading",
        strategy_type=StrategyType.STOCKS,
        risk_level=RiskLevel.MODERATE,
        max_allocation_pct=30.0,
        expected_roi_pct=18.0,
        max_drawdown_pct=20.0,
        sharpe_target=1.2,
        win_rate_target=55.0,
        requires_api_keys=True,
        adapter_module="core.investment.adapters.stocks_adapter",
        description="US equity trading via Alpaca Markets API. Supports market, limit, and bracket orders with SL/TP.",
        tags=["stocks", "alpaca", "equities", "us"],
    ),
    StrategyProfile(
        id="alpaca_options",
        name="Alpaca Options Trading",
        strategy_type=StrategyType.STOCKS_OPTIONS,
        risk_level=RiskLevel.AGGRESSIVE,
        max_allocation_pct=15.0,
        expected_roi_pct=35.0,
        max_drawdown_pct=40.0,
        sharpe_target=0.8,
        win_rate_target=45.0,
        requires_api_keys=True,
        adapter_module="core.investment.adapters.stocks_adapter",
        description="Options trading via Alpaca. Supports covered calls, cash-secured puts, and vertical spreads with automated expiration management.",
        tags=["stocks", "options", "alpaca", "derivatives"],
    ),
    StrategyProfile(
        id="ibkr_stocks",
        name="IBKR Stock Trading",
        strategy_type=StrategyType.STOCKS,
        risk_level=RiskLevel.MODERATE,
        max_allocation_pct=30.0,
        expected_roi_pct=16.0,
        max_drawdown_pct=18.0,
        sharpe_target=1.1,
        win_rate_target=54.0,
        requires_api_keys=True,
        adapter_module="core.investment.adapters.stocks_adapter",
        description="US equity and options trading via Interactive Brokers (IBKR). Supports stocks, options, futures, and forex with full order types.",
        tags=["stocks", "ibkr", "equities", "derivatives"],
    ),
    StrategyProfile(
        id="aave_lending",
        name="Aave Lending",
        strategy_type=StrategyType.DEFI_LENDING,
        risk_level=RiskLevel.CONSERVATIVE,
        max_allocation_pct=25.0,
        expected_roi_pct=8.0,
        max_drawdown_pct=5.0,
        sharpe_target=2.0,
        win_rate_target=95.0,
        requires_api_keys=False,
        adapter_module="core.investment.adapters.defi_adapter",
        description="Supply assets on Aave V3 for lending APY. Supports USDC, USDT, WETH, WBTC, and 50+ assets across Ethereum, Polygon, Arbitrum, and Base.",
        tags=["defi", "aave", "lending", "yield"],
    ),
    StrategyProfile(
        id="morpho_optimizer",
        name="Morpho Yield Optimizer",
        strategy_type=StrategyType.DEFI_YIELD,
        risk_level=RiskLevel.MODERATE,
        max_allocation_pct=20.0,
        expected_roi_pct=12.0,
        max_drawdown_pct=8.0,
        sharpe_target=1.5,
        win_rate_target=90.0,
        requires_api_keys=False,
        adapter_module="core.investment.adapters.defi_adapter",
        description="Morpho optimizes Aave V3 yields through peer-to-peer matching. Delivers 10-30% higher APY than base Aave rates.",
        tags=["defi", "morpho", "yield", "optimizer"],
    ),
    StrategyProfile(
        id="pendle_yield",
        name="Pendle Yield Tokenization",
        strategy_type=StrategyType.DEFI_YIELD,
        risk_level=RiskLevel.MODERATE,
        max_allocation_pct=15.0,
        expected_roi_pct=20.0,
        max_drawdown_pct=10.0,
        sharpe_target=1.3,
        win_rate_target=85.0,
        requires_api_keys=False,
        adapter_module="core.investment.adapters.defi_adapter",
        description="Tokenize future yield as PT/YT tokens on Pendle. Buy PT at discount, sell YT for immediate yield. Cross-chain support.",
        tags=["defi", "pendle", "yield", "tokenization"],
    ),
    StrategyProfile(
        id="lido_staking",
        name="Lido Liquid Staking",
        strategy_type=StrategyType.DEFI_LIQUID_STAKING,
        risk_level=RiskLevel.CONSERVATIVE,
        max_allocation_pct=20.0,
        expected_roi_pct=6.0,
        max_drawdown_pct=3.0,
        sharpe_target=1.8,
        win_rate_target=98.0,
        requires_api_keys=False,
        adapter_module="core.investment.adapters.defi_adapter",
        description="Stake ETH via Lido for liquid staking yield (stETH). No lockup, no minimum, instant liquidity. Also supports MATIC and other assets.",
        tags=["defi", "lido", "staking", "liquid"],
    ),
]


def get_strategy(strategy_id: str) -> StrategyProfile | None:
    for s in STRATEGY_REGISTRY:
        if s.id == strategy_id:
            return s
    return None


def get_all_strategies() -> dict[str, StrategyProfile]:
    return {s.id: s for s in STRATEGY_REGISTRY}
