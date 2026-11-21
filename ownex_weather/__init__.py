"""
OWNEX V13 — Weather Intelligence & Prediction Markets

Unified module for weather forecasting and prediction market intelligence.
Paper trading only — real trading execution DISABLED.
Single canonical implementation — NOT 4 independent bots.
AGPL-3.0 PolyWeather consumed as external API only (black box).
MIT concepts from GFS/Hermes repos freely reusable with attribution.

All new code written from scratch — no copied implementations.

Version: __version__
"""

# Version
__version__ = "v13.0.0-alpha"

# Core models and schemas — imported from models.py
# Backtesting & walk-forward validation
from .backtest import (  # noqa: F401
    BacktestRunner,
    rolling_window_validation,
    walk_forward_validate,
)
from .backtest import (
    generate_risk_report as br,
)

# Data ingestion
from .ingestion import (  # noqa: F401
    DataQuality,
    GFSAdapter,
    IngestionPipeline,
    IngestionStatus,
    METARAdapter,
    NOAAAdapter,
    OpenMeteoAdapter,
    PolymarketAdapter,
)
from .models import (  # noqa: F401
    Horizon,
    Source,
    Unit,
    ValidationStatus,
    Variable,
    # WeatherRecord and related models
    WeatherRecord,
    WeatherRecordRepository,
    apply_bias_correction,
    discretize_to_buckets,
    # Core functions
    estimate_sigma,
)

# Risk management
from .risk_manager import (  # noqa: F401
    CircuitBreaker,
    CircuitBreakerStatus,
    PositionSizingMethod,
    RiskMetrics,
    calculate_position_size,
    generate_risk_report,
)

# Security & license compliance — AGPL guard
from .security import (  # noqa: F401
    AGPLGuard,
    ComplianceStatus,
    LicenseDocumentation,
    LicenseType,
)

# Strategies — 6 modular strategies, paper trading only
from .strategies import (  # noqa: F401
    BaseStrategy,
    EnsembleGFSPriceStrategy,
    EventDrivenStrategy,
    GaussianBucketTrendStrategy,
    HumanGateStatus,
    KellyPositionStrategy,
    MeanReversionStrategy,
    StrategyStatus,
    StrategyType,
    VolatilityArbitrageStrategy,
    create_strategy,
)

# Public API — what's exported when `from ownex_weather import *`
__all__ = [
    # Version
    "__version__",
    # Core models
    "WeatherRecord",
    "WeatherRecordRepository",
    "Source",
    "Variable",
    "Unit",
    "ValidationStatus",
    "Horizon",
    "estimate_sigma",
    "apply_bias_correction",
    "discretize_to_buckets",
    # Ingestion
    "IngestionPipeline",
    "GFSAdapter",
    "OpenMeteoAdapter",
    "METARAdapter",
    "NOAAAdapter",
    "PolymarketAdapter",
    "IngestionStatus",
    "DataQuality",
    # Strategies
    "StrategyStatus",
    "StrategyType",
    "HumanGateStatus",
    "BaseStrategy",
    "GaussianBucketTrendStrategy",
    "EnsembleGFSPriceStrategy",
    "MeanReversionStrategy",
    "VolatilityArbitrageStrategy",
    "EventDrivenStrategy",
    "KellyPositionStrategy",
    "create_strategy",
    # Risk management
    "CircuitBreaker",
    "RiskMetrics",
    "PositionSizingMethod",
    "calculate_position_size",
    "generate_risk_report",
    "CircuitBreakerStatus",
    # Security & license
    "LicenseType",
    "ComplianceStatus",
    "AGPLGuard",
    "LicenseDocumentation",
    # Backtesting
    "walk_forward_validate",
    "rolling_window_validation",
    "BacktestRunner",
    "generate_risk_report",
]

# Compliance initialization note
"""
OWNEX V13 Compliance Initialization:

⚠️ HARD CONSTRAINTS (NON-NEGOTIABLE):
1. NO AGPL-3.0 code reuse — PolyWeather consumed as external API (black box)
2. Paper trading ONLY — real trading execution DISABLED
3. Human gate approval required for all strategy activation and circuit breaker reset
4. No geoblocking bypass for Argentina access
5. All new code written from scratch — no copied implementations
6. MIT concepts from GFS/Hermes repos reusable with attribution
7. credentials.txt from Repo 4 — DO NOT OPEN OR USE SECRETS

All modules enforce these constraints via AGPLGuard verification.
"""
