"""Engine Adapter Interface — Universal interface for all trading engines.

Every external engine (Freqtrade, Hummingbot, Jesse, etc.) must implement
this interface through an adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from core.trading.contracts import (
    BacktestResult,
    EngineHealth,
    EngineHealthStatus,
    EngineMetadata,
    ExperimentRecord,
    MarketData,
    OptimizationResult,
    Order,
    PaperTradingResult,
    PerformanceMetrics,
    Position,
    Signal,
    StrategyStatus,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class EngineConfig:
    """Configuration for engine adapter."""

    engine_id: str
    config: dict
    data_dir: str
    log_level: str = "INFO"
    dry_run: bool = True


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    healthy: bool
    latency_ms: float | None = None
    error: str | None = None
    details: dict | None = None


class EngineAdapter(ABC):
    """Abstract base class for all engine adapters.

    Every external trading engine must implement this interface.
    """

    # Class attributes that must be defined by subclasses
    ENGINE_ID: str = ""
    ENGINE_NAME: str = ""
    ENGINE_VERSION: str = ""
    SUPPORTED_CAPABILITIES: list = []
    SUPPORTED_EXCHANGES: list = []
    SUPPORTED_MARKETS: list = []  # spot, futures, dex
    DOCKER_IMAGE: str | None = None
    REQUIRED_CONFIG_KEYS: list[str] = []

    def __init__(self, config: EngineConfig):
        self.config = config
        self.engine_id = config.engine_id
        self.data_dir = config.data_dir
        self.dry_run = config.dry_run
        self._initialized = False
        self._health = EngineHealth.NOT_INSTALLED
        self._last_health_check = None
        self._active_strategies: dict[str, str] = {}  # strategy_id -> last_activity timestamp

    # ════════════════════════════════════════════════════════════════════════
    # LIFECYCLE METHODS (must be implemented)
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def install(self) -> bool:
        """Install the engine (download, compile, setup dependencies)."""
        pass

    @abstractmethod
    async def uninstall(self) -> bool:
        """Uninstall the engine and clean up."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the engine (create configs, directories, validate setup)."""
        pass

    @abstractmethod
    async def shutdown(self) -> bool:
        """Gracefully shutdown the engine."""
        pass

    # ════════════════════════════════════════════════════════════════════════
    # HEALTH & MONITORING
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """Check engine health. Must be fast (< 5s)."""
        pass

    async def get_health_status(self) -> EngineHealthStatus:
        """Get detailed health status."""
        from core.trading.contracts import EngineHealth, EngineHealthStatus

        result = await self.health_check()
        self._health = EngineHealth.ONLINE if result.healthy else EngineHealth.ERROR
        self._last_health_check = datetime.now(UTC).isoformat()

        return EngineHealthStatus(
            engine_id=self.engine_id,
            health=self._health,
            last_check=datetime.now(UTC).isoformat(),
            latency_ms=result.latency_ms,
            error=result.error,
            active_strategies=len(self._active_strategies),
        )

    # ════════════════════════════════════════════════════════════════════════
    # CAPABILITIES & METADATA
    # ═══════════════════════════════════════════════════════════════════════

    def get_metadata(self) -> EngineMetadata:
        """Get engine metadata."""
        from core.trading.contracts import EngineHealth, EngineMetadata

        return EngineMetadata(
            engine_id=self.ENGINE_ID,
            name=self.ENGINE_NAME,
            version=self.ENGINE_VERSION,
            description=self.__doc__ or "",
            classification=[],  # To be overridden
            capabilities=self.SUPPORTED_CAPABILITIES,
            supported_exchanges=self.SUPPORTED_EXCHANGES,
            supported_markets=self.SUPPORTED_MARKETS,
            docker_image=self.DOCKER_IMAGE,
            config_schema={},  # To be overridden
            documentation_url="",
            repository_url="",
            license="",
            maintainer="",
            health=EngineHealth.ONLINE if self._initialized else EngineHealth.NOT_INSTALLED,
        )

    def get_capabilities(self) -> list:
        """Get supported capabilities."""
        return self.SUPPORTED_CAPABILITIES

    # ════════════════════════════════════════════════════════════════════════
    # STRATEGY MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def load_strategy(self, strategy_id: str, strategy_config: dict) -> bool:
        """Load a strategy configuration into the engine."""
        pass

    @abstractmethod
    async def unload_strategy(self, strategy_id: str) -> bool:
        """Unload a strategy from the engine."""
        pass

    @abstractmethod
    async def get_strategy_status(self, strategy_id: str) -> StrategyStatus:
        """Get the status of a strategy in this engine."""
        pass

    @abstractmethod
    async def list_strategies(self) -> list[str]:
        """List all loaded strategies."""
        pass

    # ════════════════════════════════════════════════════════════════════════
    # VALIDATION PIPELINE
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def backtest(
        self,
        strategy_id: str,
        market_data: MarketData,
        parameters: dict,
        execution_config: dict,
    ) -> BacktestResult:
        """Run backtest for a strategy."""
        pass

    @abstractmethod
    async def optimize(
        self,
        strategy_id: str,
        param_space: dict,
        market_data: MarketData,
        optimization_metric: str = "sharpe",
        n_trials: int = 100,
    ) -> OptimizationResult:
        """Optimize strategy parameters."""
        pass

    @abstractmethod
    async def walk_forward(
        self,
        strategy_id: str,
        market_data: MarketData,
        windows: int = 12,
        step_size: int = 1,
    ) -> list[BacktestResult]:
        """Run walk-forward analysis."""
        pass

    @abstractmethod
    async def monte_carlo(
        self,
        strategy_id: str,
        backtest_result: BacktestResult,
        n_simulations: int = 1000,
    ) -> dict:
        """Run Monte Carlo simulation on backtest results."""
        pass

    @abstractmethod
    async def stress_test(
        self,
        strategy_id: str,
        market_data: MarketData,
        scenarios: list[dict],
    ) -> dict:
        """Run stress tests against specific market scenarios."""
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # PAPER & LIVE TRADING
    # ══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def start_paper_trading(self, strategy_id: str) -> bool:
        """Start paper trading for a strategy."""
        pass

    @abstractmethod
    async def stop_paper_trading(self, strategy_id: str) -> PaperTradingResult:
        """Stop paper trading and return results."""
        pass

    @abstractmethod
    async def get_paper_trading_status(self, strategy_id: str) -> dict:
        """Get current paper trading status."""
        pass

    @abstractmethod
    async def start_live_trading(self, strategy_id: str, capital_allocation: Decimal) -> bool:
        """Start live trading for a strategy (requires approvals)."""
        pass

    @abstractmethod
    async def stop_live_trading(self, strategy_id: str, reason: str = "user requested") -> bool:
        """Stop live trading for a strategy."""
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # REAL-TIME DATA
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def get_signals(self, strategy_id: str) -> list[Signal]:
        """Get current signals from a strategy."""
        pass

    @abstractmethod
    async def get_orders(self, strategy_id: str) -> list[Order]:
        """Get current orders for a strategy."""
        pass

    @abstractmethod
    async def get_positions(self, strategy_id: str) -> list[Position]:
        """Get current positions for a strategy."""
        pass

    @abstractmethod
    async def get_performance(self, strategy_id: str) -> PerformanceMetrics:
        """Get current performance metrics."""
        pass

    @abstractmethod
    async def get_logs(self, strategy_id: str, limit: int = 100) -> list[dict]:
        """Get recent logs for a strategy."""
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # EXPERIMENT TRACKING
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def record_experiment(self, experiment: ExperimentRecord) -> str:
        """Record an experiment for reproducibility."""
        pass

    @abstractmethod
    async def get_experiments(self, strategy_id: str) -> list[ExperimentRecord]:
        """Get all experiments for a strategy."""
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # UTILITY
    # ═══════════════════════════════════════════════════════════════════════

    def _update_activity(self, strategy_id: str, status: StrategyStatus) -> None:
        """Track active strategy."""
        from core.trading.contracts import StrategyStatus

        if status in (StrategyStatus.LIVE, StrategyStatus.PAPER, StrategyStatus.CANARY):
            self._active_strategies[strategy_id] = datetime.now(UTC).isoformat()
        else:
            self._active_strategies.pop(strategy_id, None)

    def is_healthy(self) -> bool:
        return self._health == EngineHealth.ONLINE

    def get_uptime(self) -> float | None:
        """Get engine uptime in seconds."""
        return None  # Override in subclass
