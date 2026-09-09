"""Universal Trading Contracts — Canonical interfaces for all engines.

Every engine must speak these contracts. No exceptions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════


class EngineClassification(StrEnum):
    """Categories of trading engines."""

    TREND_FOLLOWING = "trend_following"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    GRID = "grid"
    DCA = "dca"
    ARBITRAGE = "arbitrage"
    MARKET_MAKING = "market_making"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    PORTFOLIO_ALLOCATION = "portfolio_allocation"
    ML = "ml"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    ON_CHAIN = "on_chain"
    DEFI = "defi"
    FUTURES = "futures"
    SPOT = "spot"
    MULTI_ASSET = "multi_asset"
    RESEARCH_BACKTESTING = "research_backtesting"
    HIGH_FREQUENCY = "high_frequency"


class EngineCapability(StrEnum):
    """Capabilities an engine may support."""

    BACKTEST = "backtest"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    OPTIMIZATION = "optimization"
    MACHINE_LEARNING = "machine_learning"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    DEX_SUPPORT = "dex_support"
    FUTURES_SUPPORT = "futures_support"
    SPOT_SUPPORT = "spot_support"
    MULTI_EXCHANGE = "multi_exchange"
    PORTFOLIO_MANAGEMENT = "portfolio_management"
    RISK_MANAGEMENT = "risk_management"
    STRATEGY_API = "strategy_api"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"
    REST_API = "rest_api"
    CONTENT_GENERATION = "content_generation"
    SCHEDULING = "scheduling"
    ANALYTICS = "analytics"
    MONETIZATION = "monetization"


class EngineHealth(StrEnum):
    """Health status of an engine."""

    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    ERROR = "error"
    NOT_INSTALLED = "not_installed"
    UPDATING = "updating"
    UNSUPPORTED = "unsupported"


class StrategyStatus(StrEnum):
    """Lifecycle states of a strategy."""

    DISCOVERED = "discovered"
    INSTALLED = "installed"
    BACKTESTING = "backtesting"
    BACKTEST_FAILED = "backtest_failed"
    VALIDATING = "validating"
    VALIDATED = "validated"
    PAPER = "paper"
    CANARY = "canary"
    LIVE = "live"
    PAUSED = "paused"
    RETIRED = "retired"


class SignalSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(StrEnum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class ValidationPhase(StrEnum):
    PHASE_1_BACKTEST = "phase_1_backtest"
    PHASE_2_OUT_OF_SAMPLE = "phase_2_out_of_sample"
    PHASE_3_WALK_FORWARD = "phase_3_walk_forward"
    PHASE_4_MONTE_CARLO = "phase_4_monte_carlo"
    PHASE_5_STRESS_TEST = "phase_5_stress_test"
    PHASE_6_PAPER = "phase_6_paper"
    PHASE_7_CANARY = "phase_7_canary"
    PHASE_8_PRODUCTION = "phase_8_production"


class MarketRegime(StrEnum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRASH = "crash"
    RECOVERY = "recovery"
    LIQUID = "liquid"
    ILLIQUID = "illiquid"


class AllocationMode(StrEnum):
    EQUAL = "equal"
    RISK_PARITY = "risk_parity"
    VOLATILITY_TARGET = "volatility_target"
    SHARPE_WEIGHTED = "sharpe_weighted"
    CORRELATION_AWARE = "correlation_aware"
    MANUAL = "manual"


class KillSwitchLevel(StrEnum):
    GLOBAL = "global"
    STRATEGY = "strategy"
    EXCHANGE = "exchange"
    ASSET = "asset"


# ════════════════════════════════════════════════════════════════════════════
# CORE DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


@dataclass(slots=True)
class EngineMetadata:
    """Metadata for a trading engine."""

    engine_id: str
    name: str
    version: str
    description: str
    classification: list[EngineClassification]
    capabilities: list[EngineCapability]
    supported_exchanges: list[str]
    supported_markets: list[str]  # spot, futures, dex
    docker_image: str | None = None
    config_schema: dict[str, Any] = field(default_factory=dict)
    documentation_url: str = ""
    repository_url: str = ""
    license: str = ""
    maintainer: str = ""
    last_updated: str = field(default_factory=_now_iso)
    health: EngineHealth = EngineHealth.NOT_INSTALLED
    installed_path: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Strategy:
    """Canonical strategy definition."""

    strategy_id: str = field(default_factory=lambda: _new_id("strat_"))
    engine_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    classification: list[EngineClassification] = field(default_factory=list)
    market: str = ""  # spot, futures, dex
    exchange: str = ""
    timeframe: str = "1h"
    symbols: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    risk_profile: dict[str, Any] = field(default_factory=dict)
    capital_required: Decimal = Decimal("0")
    status: StrategyStatus = StrategyStatus.DISCOVERED
    validation_status: dict[ValidationPhase, bool] = field(default_factory=dict)
    paper_started_at: str | None = None
    canary_started_at: str | None = None
    live_started_at: str | None = None
    capital_allocation: Decimal = Decimal("0")
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Signal:
    """Trading signal from a strategy."""

    signal_id: str = field(default_factory=lambda: _new_id("sig_"))
    strategy_id: str = ""
    timestamp: str = field(default_factory=_now_iso)
    symbol: str = ""
    side: SignalSide = SignalSide.BUY
    confidence: Decimal = Decimal("0")  # 0-1
    entry_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    expected_return: Decimal | None = None
    expected_risk: Decimal | None = None
    source: str = ""  # engine-specific identifier
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Order:
    """Order with full lifecycle tracking."""

    order_id: str = field(default_factory=lambda: _new_id("ord_"))
    idempotency_key: str = field(default_factory=lambda: _new_id("idem_"))
    strategy_id: str = ""
    signal_id: str | None = None
    symbol: str = ""
    side: SignalSide = SignalSide.BUY
    quantity: Decimal = Decimal("0")
    price: Decimal | None = None
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    fees: Decimal = Decimal("0")
    exchange: str = ""
    exchange_order_id: str | None = None
    timestamp: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Position:
    """Open position with risk metrics."""

    position_id: str = field(default_factory=lambda: _new_id("pos_"))
    strategy_id: str = ""
    symbol: str = ""
    side: PositionSide = PositionSide.FLAT
    entry_price: Decimal = Decimal("0")
    current_price: Decimal = Decimal("0")
    size: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    max_adverse_excursion: Decimal = Decimal("0")
    max_favorable_excursion: Decimal = Decimal("0")
    leverage: Decimal = Decimal("1")
    margin_used: Decimal = Decimal("0")
    exchange: str = ""
    opened_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PerformanceMetrics:
    """Normalized performance metrics — all phases identified."""

    # Required fields first (no defaults)
    strategy_id: str
    phase: ValidationPhase

    # Returns
    total_return: Decimal = Decimal("0")
    cagr: Decimal = Decimal("0")
    monthly_return: Decimal = Decimal("0")
    daily_return: Decimal = Decimal("0")

    # Risk-adjusted
    sharpe: Decimal = Decimal("0")
    sortino: Decimal = Decimal("0")
    calmar: Decimal = Decimal("0")

    # Drawdown
    max_drawdown: Decimal = Decimal("0")
    max_drawdown_duration: int = 0
    recovery_factor: Decimal = Decimal("0")

    # Trade stats
    profit_factor: Decimal = Decimal("0")
    win_rate: Decimal = Decimal("0")
    loss_rate: Decimal = Decimal("0")
    average_win: Decimal = Decimal("0")
    average_loss: Decimal = Decimal("0")
    expectancy: Decimal = Decimal("0")
    number_of_trades: int = 0

    # Costs
    turnover: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")

    # Exposure
    exposure: Decimal = Decimal("0")
    time_in_market: Decimal = Decimal("0")

    # Extremes
    best_trade: Decimal = Decimal("0")
    worst_trade: Decimal = Decimal("0")

    # Risk
    volatility: Decimal = Decimal("0")
    risk_of_ruin_estimate: Decimal = Decimal("0")

    # Metadata
    dataset_hash: str = ""
    parameters_hash: str = ""
    code_commit: str = ""
    random_seed: int = 0
    computed_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in self.__dict__.items()}


@dataclass(slots=True)
class EngineHealthStatus:
    """Real-time health of an engine."""

    engine_id: str
    health: EngineHealth
    last_check: str = field(default_factory=_now_iso)
    latency_ms: float | None = None
    error: str | None = None
    active_strategies: int = 0
    cpu_percent: float | None = None
    memory_mb: float | None = None
    api_connected: bool = False
    exchange_connected: dict[str, bool] = field(default_factory=dict)
    last_error: str | None = None


@dataclass(slots=True)
class BacktestResult:
    """Result of a backtest run."""

    backtest_id: str = field(default_factory=lambda: _new_id("bt_"))
    strategy_id: str = ""
    engine_id: str = ""
    phase: ValidationPhase = ValidationPhase.PHASE_1_BACKTEST
    metrics: PerformanceMetrics | None = None
    trades: list[dict] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)
    drawdown_curve: list[dict] = field(default_factory=list)
    dataset_hash: str = ""
    parameters_hash: str = ""
    code_commit: str = ""
    execution_config: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=_now_iso)
    completed_at: str | None = None
    success: bool = False
    error: str | None = None


@dataclass(slots=True)
class OptimizationResult:
    """Result of parameter optimization."""

    optimization_id: str = field(default_factory=lambda: _new_id("opt_"))
    strategy_id: str = ""
    engine_id: str = ""
    best_params: dict[str, Any] = field(default_factory=dict)
    best_metrics: PerformanceMetrics | None = None
    all_trials: list[dict] = field(default_factory=list)
    param_space: dict[str, Any] = field(default_factory=dict)
    optimization_metric: str = "sharpe"
    n_trials: int = 0
    started_at: str = field(default_factory=_now_iso)
    completed_at: str | None = None
    success: bool = False


@dataclass(slots=True)
class PaperTradingResult:
    """Result of paper trading period."""

    paper_id: str = field(default_factory=lambda: _new_id("paper_"))
    strategy_id: str = ""
    engine_id: str = ""
    metrics: PerformanceMetrics | None = None
    trades: list[dict] = field(default_factory=list)
    daily_pnl: list[dict] = field(default_factory=list)
    started_at: str = field(default_factory=_now_iso)
    completed_at: str | None = None
    days_run: int = 0
    success: bool = False
    stopped_reason: str | None = None


@dataclass(slots=True)
class KillSwitchEvent:
    """Record of a kill switch activation."""

    level: KillSwitchLevel
    trigger: str
    reason: str
    event_id: str = field(default_factory=lambda: _new_id("ks_"))
    affected: list[str] = field(default_factory=list)
    triggered_by: str = "system"
    timestamp: str = field(default_factory=_now_iso)
    resolved: bool = False
    resolved_at: str | None = None
    resolved_by: str | None = None


@dataclass(slots=True)
class ReconciliationEvent:
    """Reconciliation discrepancy event."""

    discrepancy_type: str
    expected: dict[str, Any]
    actual: dict[str, Any]
    difference: dict[str, Any]
    severity: str
    source: str
    event_id: str = field(default_factory=lambda: _new_id("rec_"))
    timestamp: str = field(default_factory=_now_iso)
    resolved: bool = False
    resolved_at: str | None = None


@dataclass(slots=True)
class ExperimentRecord:
    """Reproducible experiment record."""

    strategy_id: str
    engine_id: str
    phase: ValidationPhase
    dataset_hash: str
    parameters: dict[str, Any]
    parameters_hash: str
    experiment_id: str = field(default_factory=lambda: _new_id("exp_"))
    metrics: PerformanceMetrics | None = None
    code_commit: str = ""
    dataset_version: str = ""
    random_seed: int = 0
    execution_config: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    result: str = "pending"
    notes: str = ""
    created_at: str = field(default_factory=_now_iso)


@dataclass(slots=True)
class AllocationResult:
    """Result of capital allocation optimization."""

    mode: AllocationMode
    allocation_id: str = field(default_factory=lambda: _new_id("alloc_"))
    allocations: dict[str, Decimal] = field(default_factory=dict)
    total_allocated: Decimal = Decimal("0")
    cash_reserve: Decimal = Decimal("0")
    expected_return: Decimal = Decimal("0")
    expected_risk: Decimal = Decimal("0")
    sharpe: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    correlation_matrix: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    regime_exposure: dict[MarketRegime, Decimal] = field(default_factory=dict)
    constraints_satisfied: bool = True
    created_at: str = field(default_factory=_now_iso)


# ════════════════════════════════════════════════════════════════════════════
# PATRIMONIAL / NET WORTH CONTRACTS
# ════════════════════════════════════════════════════════════════════════════


class PatrimonialLevel(StrEnum):
    """Patrimonial ladder levels."""

    LEVEL_0_VALIDATION = "level_0_validation"  # $0 → $500
    LEVEL_1_OPERATIONAL = "level_1_operational"  # $500 → $2k
    LEVEL_2_DIVERSIFICATION = "level_2_diversification"  # $2k → $5k
    LEVEL_3_REPEATABILITY = "level_3_repeatability"  # $5k → $10k
    LEVEL_4_SPECIALIZATION = "level_4_specialization"  # $10k → $25k
    LEVEL_5_LEVERAGE = "level_5_leverage"  # $25k → $50k
    LEVEL_6_COMPOUNDING = "level_6_compounding"  # $50k → $100k
    LEVEL_7_ENTERPRISE = "level_7_enterprise"  # $100k+


@dataclass(slots=True)
class LadderLevel:
    """Patrimonial ladder level definition."""

    level: PatrimonialLevel
    name: str
    min_net_worth: Decimal
    max_net_worth: Decimal | None
    description: str
    # Gates to advance to next level
    min_drawdown_pct: Decimal = Decimal("0.15")  # Max drawdown allowed
    min_liquidity_usd: Decimal = Decimal("1000")  # Minimum liquidity
    min_monthly_revenue_usd: Decimal = Decimal("0")  # Minimum recurring revenue
    max_leverage: Decimal = Decimal("3.0")  # Max leverage allowed
    max_single_position_pct: Decimal = Decimal("0.20")  # Max 20% in one position
    required_months_at_level: int = 1  # Months before can advance


# Pre-defined ladder levels
LADDER_LEVELS: tuple[LadderLevel, ...] = (
    LadderLevel(
        level=PatrimonialLevel.LEVEL_0_VALIDATION,
        name="Validación Inicial",
        min_net_worth=Decimal("0"),
        max_net_worth=Decimal("500"),
        description="Primera validación de ingresos",
        min_drawdown_pct=Decimal("0.20"),
        min_liquidity_usd=Decimal("100"),
        min_monthly_revenue_usd=Decimal("0"),
        max_leverage=Decimal("1.0"),
        max_single_position_pct=Decimal("0.50"),
        required_months_at_level=0,
    ),
    LadderLevel(
        level=PatrimonialLevel.LEVEL_1_OPERATIONAL,
        name="Primer Capital Operativo",
        min_net_worth=Decimal("500"),
        max_net_worth=Decimal("2000"),
        description="Primer capital operativo",
        min_drawdown_pct=Decimal("0.20"),
        min_liquidity_usd=Decimal("500"),
        min_monthly_revenue_usd=Decimal("100"),
        max_leverage=Decimal("2.0"),
        max_single_position_pct=Decimal("0.30"),
        required_months_at_level=1,
    ),
    LadderLevel(
        level=PatrimonialLevel.LEVEL_2_DIVERSIFICATION,
        name="Diversificación",
        min_net_worth=Decimal("2000"),
        max_net_worth=Decimal("5000"),
        description="Diversificación de ingresos",
        min_drawdown_pct=Decimal("0.15"),
        min_liquidity_usd=Decimal("1000"),
        min_monthly_revenue_usd=Decimal("500"),
        max_leverage=Decimal("2.5"),
        max_single_position_pct=Decimal("0.25"),
        required_months_at_level=2,
    ),
    LadderLevel(
        level=PatrimonialLevel.LEVEL_3_REPEATABILITY,
        name="Repetibilidad",
        min_net_worth=Decimal("5000"),
        max_net_worth=Decimal("10000"),
        description="Repetibilidad de ingresos",
        min_drawdown_pct=Decimal("0.15"),
        min_liquidity_usd=Decimal("2500"),
        min_monthly_revenue_usd=Decimal("1000"),
        max_leverage=Decimal("3.0"),
        max_single_position_pct=Decimal("0.20"),
        required_months_at_level=3,
    ),
    LadderLevel(
        level=PatrimonialLevel.LEVEL_4_SPECIALIZATION,
        name="Especialización",
        min_net_worth=Decimal("10000"),
        max_net_worth=Decimal("25000"),
        description="Especialización + mejores oportunidades",
        min_drawdown_pct=Decimal("0.12"),
        min_liquidity_usd=Decimal("5000"),
        min_monthly_revenue_usd=Decimal("2500"),
        max_leverage=Decimal("3.0"),
        max_single_position_pct=Decimal("0.20"),
        required_months_at_level=4,
    ),
    LadderLevel(
        level=PatrimonialLevel.LEVEL_5_LEVERAGE,
        name="Apalancamiento",
        min_net_worth=Decimal("25000"),
        max_net_worth=Decimal("50000"),
        description="Apalancamiento controlado",
        min_drawdown_pct=Decimal("0.10"),
        min_liquidity_usd=Decimal("10000"),
        min_monthly_revenue_usd=Decimal("5000"),
        max_leverage=Decimal("4.0"),
        max_single_position_pct=Decimal("0.15"),
        required_months_at_level=6,
    ),
    LadderLevel(
        level=PatrimonialLevel.LEVEL_6_COMPOUNDING,
        name="Capital Trabajando",
        min_net_worth=Decimal("50000"),
        max_net_worth=Decimal("100000"),
        description="Capital empieza a trabajar solo",
        min_drawdown_pct=Decimal("0.10"),
        min_liquidity_usd=Decimal("25000"),
        min_monthly_revenue_usd=Decimal("10000"),
        max_leverage=Decimal("3.0"),
        max_single_position_pct=Decimal("0.15"),
        required_months_at_level=12,
    ),
    LadderLevel(
        level=PatrimonialLevel.LEVEL_7_ENTERPRISE,
        name="Escala Empresarial",
        min_net_worth=Decimal("100000"),
        max_net_worth=None,
        description="Escala empresarial / inversora",
        min_drawdown_pct=Decimal("0.08"),
        min_liquidity_usd=Decimal("50000"),
        min_monthly_revenue_usd=Decimal("25000"),
        max_leverage=Decimal("2.0"),
        max_single_position_pct=Decimal("0.10"),
        required_months_at_level=24,
    ),
)


@dataclass(slots=True)
class CapitalGates:
    """Capital gates for a patrimonial level."""

    level: PatrimonialLevel
    can_advance: bool
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_level: PatrimonialLevel | None = None
    progress_pct: Decimal = Decimal("0")


@dataclass(slots=True)
class NetWorthBreakdown:
    """Detailed net worth breakdown by category."""

    # Liquid / Immediately available
    liquid_capital: Decimal = Decimal("0")  # Efectivo disponible inmediato
    emergency_reserve: Decimal = Decimal("0")  # Reserva emergencia (3-6 meses)
    operating_capital: Decimal = Decimal("0")  # Capital operativo (trading/work)

    # Investments
    investments: Decimal = Decimal("0")  # Acciones, bonos, CEDEARs, ETFs
    crypto: Decimal = Decimal("0")  # Crypto (wallets + exchanges)
    business_assets: Decimal = Decimal("0")  # Activos negocio (content factory, etc)

    # Expected / Pending (NOT realized)
    expected_revenue: Decimal = Decimal("0")  # Expected Revenue (bounties pendientes, facturas)
    pending_bounties: Decimal = Decimal("0")  # Bounties enviados, no cobrados
    pending_invoices: Decimal = Decimal("0")  # Facturas emitidas, no cobradas

    # Unrealized / Speculative
    unrealized_value: Decimal = Decimal("0")  # Equity, options, unrealized P&L

    # Total
    total_net_worth: Decimal = Decimal("0")

    def to_dict(self) -> dict[str, Any]:
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in self.__dict__.items()}

    @property
    def realized_total(self) -> Decimal:
        """Total realized (excludes expected/pending/unrealized)."""
        return (
            self.liquid_capital
            + self.emergency_reserve
            + self.operating_capital
            + self.investments
            + self.crypto
            + self.business_assets
        )

    @property
    def expected_total(self) -> Decimal:
        """Total expected (not yet realized)."""
        return self.expected_revenue + self.pending_bounties + self.pending_invoices

    @property
    def unrealized_total(self) -> Decimal:
        """Total unrealized/speculative."""
        return self.unrealized_value


@dataclass(slots=True)
class NetWorthSnapshot:
    """Complete net worth snapshot at a point in time."""

    snapshot_id: str = field(default_factory=lambda: _new_id("nw_"))
    generated_at: str = field(default_factory=_now_iso)
    breakdown: NetWorthBreakdown = field(default_factory=NetWorthBreakdown)
    ladder_level: PatrimonialLevel = PatrimonialLevel.LEVEL_0_VALIDATION
    ladder_progress_pct: Decimal = Decimal("0")
    capital_gates: CapitalGates | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "generated_at": self.generated_at,
            "breakdown": self.breakdown.to_dict(),
            "ladder_level": self.ladder_level.value,
            "ladder_progress_pct": str(self.ladder_progress_pct),
            "capital_gates": self.capital_gates.__dict__ if self.capital_gates else None,
        }


@dataclass(slots=True)
class ExpectedRevenueRecord:
    """Expected revenue record (not yet realized)."""

    source: str  # "bug_bounty", "dev_bounty", "content_factory", "invoice", "other"
    source_id: str  # platform-specific ID (bounty ID, invoice ID, etc)
    platform: str
    expected_amount_usd: Decimal
    record_id: str = field(default_factory=lambda: _new_id("er_"))
    currency: str = "USD"
    expected_date: str | None = None  # Expected payment date
    status: str = "pending"  # pending, confirmed, paid, failed, cancelled
    probability_pct: Decimal = Decimal("50")  # Probability of collection
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    realized_at: str | None = None
    realized_amount_usd: Decimal | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in self.__dict__.items()}


@dataclass(slots=True)
class PatrimonyConfig:
    """Configuration for patrimony engine."""

    # Ladder settings
    auto_advance_levels: bool = False  # Require manual approval to advance
    require_human_approval_to_advance: bool = True
    min_months_at_level: bool = True  # Enforce minimum months at level

    # Alerts
    alert_on_level_progress_pct: Decimal = Decimal("80")  # Alert at 80% progress
    alert_on_drawdown_breach: bool = True
    alert_on_level_gate_breach: bool = True

    # Expected revenue
    default_bounty_probability_pct: Decimal = Decimal("50")
    default_invoice_probability_pct: Decimal = Decimal("80")
    auto_expire_expected_days: int = 90  # Auto-expire expected revenue after N days


# ════════════════════════════════════════════════════════════════════════════
# TYPE ALIASES & HELPERS
# ════════════════════════════════════════════════════════════════════════════

EngineConfig = dict[str, Any]
StrategyConfig = dict[str, Any]
MarketData = dict[str, Any]  # OHLCV, orderbook, trades, funding, OI
DatasetSpec = dict[str, Any]  # exchange, symbols, timeframe, start, end, frequency


def validate_contract(obj: Any, required_fields: list[str]) -> bool:
    """Validate that an object has all required fields."""
    if hasattr(obj, "__dataclass_fields__"):
        return all(hasattr(obj, f) for f in required_fields)
    if isinstance(obj, dict):
        return all(f in obj for f in required_fields)
    return False
