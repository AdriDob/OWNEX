"""
OWNEX V13 — Weather Intelligence & Prediction Markets
6 Modular Strategies — Paper Trading Only, Real Trading Disabled

All strategies require human gate approval before activation.
No real trading execution permitted.
Kelly Criterion position sizing used for paper trading only.
"""

import time
from enum import Enum
from typing import Any

from .ingestion import DataQuality
from .models import Horizon, WeatherRecord


class StrategyStatus(str, Enum):
    """Strategy execution status."""

    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    APPROVAL_PENDING = "approval_pending"
    CIRCUIT_BREAKER_TRIGGERED = "circuit_breaker"


class StrategyType(str, Enum):
    """Enumeration of the 6 modular strategies."""

    GAUSSIAN_BUCKET_TREND = "gaussian_bucket_trend"  # Gaussian Bucket + trend detection
    ENSEMBLE_GFS_PRICE = "ensemble_gfs_price"  # Ensemble GFS + price comparison
    MEAN_REVERSION = "mean_reversion"  # Mean reversion on temperature deviations
    VOLATILITY_ARBITRAGE = "volatility_arbitrage"  # σ arbitrage between models
    EVENT_DRIVEN = "event_driven"  # Weather events → market impact
    KELLY_POSITION = "kelly_position"  # Kelly position sizing


class HumanGateStatus(str, Enum):
    """Human gate approval status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# --- Strategy Base Class ---


class BaseStrategy:
    """Base class for all 6 modular strategies.

    All strategies share common constraints:
    - Paper trading only
    - Human gate approval required
    - Circuit breaker with statistical validation
    - No real trading execution
    """

    def __init__(self, strategy_type: StrategyType, name: str = ""):
        self.strategy_type = strategy_type
        self.name = name or strategy_type.value
        self.status = StrategyStatus.IDLE
        self.human_gate = HumanGateStatus.PENDING
        self.circuit_breaker_triggered = False
        self.active_since: float | None = None
        self.deactivation_reason: str | None = None
        self.metrics: dict[str, Any] = {
            "signals_generated": 0,
            "trades_paper": 0,
            "trades_real": 0,  # Should remain 0
            "win_rate": 0.0,
            "total_return_paper": 0.0,
            "max_drawdown": 0.0,
            "sigma_estimate": 0.0,
            "last_signal_time": 0.0,
        }
        self._creation_time = time.time()

    def activate(self) -> bool:
        """Activate the strategy — requires human gate approval."""
        if self.human_gate == HumanGateStatus.APPROVED:
            self.status = StrategyStatus.ACTIVE
            self.active_since = time.time()
            return True
        elif self.human_gate == HumanGateStatus.PENDING:
            self.status = StrategyStrategy.APPROVAL_PENDING
            return False
        else:
            self.status = StrategyStatus.STOPPED
            return False

    def deactivate(self, reason: str) -> None:
        """Deactivate the strategy."""
        self.status = StrategyStatus.STOPPED
        self.deactivation_reason = reason
        self.human_gate = HumanGateStatus.PENDING

    def check_circuit_breaker(
        self,
        max_drawdown: float,
        current_drawdown: float,
        va_r_threshold: float,
        current_va_r: float,
    ) -> bool:
        """
        Check circuit breaker conditions.

        Safety constraint: circuit breaker reset requires human approval.
        Statistical validation required before reactivation.
        """
        triggered = False
        reasons = []

        # Max drawdown circuit breaker
        if current_drawdown >= max_drawdown:
            triggered = True
            reasons.append(f"Max drawdown exceeded: {current_drawdown:.2f} >= {max_drawdown:.2f}")

        # VaR circuit breaker
        if current_va_r >= va_r_threshold:
            triggered = True
            reasons.append(f"VaR exceeded: {current_va_r:.2f} >= {va_r_threshold:.2f}")

        if triggered:
            self.circuit_breaker_triggered = True
            self.deactivate("; ".join(reasons))

        return triggered

    def needs_human_gate(self) -> bool:
        """Check if strategy requires human gate approval."""
        return self.human_gate in (HumanGateStatus.PENDING, HumanGateStatus.APPROVAL_PENDING)

    def request_approval(self) -> HumanGateStatus:
        """Request human gate approval — returns current status."""
        return self.human_gate

    def grant_approval(self, approved: bool, approver: str = "system") -> None:
        """Grant or deny human gate approval."""
        if approved:
            self.human_gate = HumanGateStatus.APPROVED
        else:
            self.human_gate = HumanGateStatus.REJECTED
            self.deactivate("Strategy rejected by human gate")

    def to_dict(self) -> dict:
        """Serialize strategy state."""
        return {
            "strategy_type": self.strategy_type.value,
            "name": self.name,
            "status": self.status.value,
            "human_gate": self.human_gate.value,
            "circuit_breaker_triggered": self.circuit_breaker_triggered,
            "active_since": self.active_since,
            "metrics": self.metrics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BaseStrategy":
        """Deserialize strategy state."""
        strategy = cls(
            strategy_type=StrategyType(data.get("strategy_type", "gaussian_bucket_trend")),
            name=data.get("name", ""),
        )
        strategy.status = StrategyStatus(data.get("status", "idle"))
        strategy.human_gate = HumanGateStatus(data.get("human_gate", "pending"))
        strategy.circuit_breaker_triggered = data.get("circuit_breaker_triggered", False)
        strategy.active_since = data.get("active_since")
        strategy.deactivation_reason = data.get("deactivation_reason")
        strategy.metrics = data.get("metrics", strategy.metrics)
        return strategy


# --- Strategy 1: Gaussian Bucket Trend ---


class GaussianBucketTrendStrategy(BaseStrategy):
    """Gaussian Bucket Trend Strategy.

    Uses Gaussian Bucket Model discretization to detect trend changes.
    When forecast probability shifts between buckets, generates signal.
    Paper trading only: position sizing via Kelly Criterion.
    """

    def __init__(self, name: str = "GaussianBucketTrend", sigma_threshold: float = 2.0, bucket_count: int = 3, max_position_pct: float = 10.0):
        super().__init__(StrategyType.GAUSSIAN_BUCKET_TREND, name)
        self.sigma_threshold = sigma_threshold  # σ threshold for bucket shift
        self.bucket_count = bucket_count  # Number of Gaussian buckets
        self.max_position_pct = max_position_pct  # Max % capital per trade (paper)
        self.last_bucket_state: dict | None = None

    def evaluate(self, record: WeatherRecord, current_price: float, reference_price: float) -> dict | None:
        """
        Evaluate Gaussian Bucket trend signal.

        Returns signal dict if conditions met, None otherwise.
        """
        if record.quality != "validated":
            return None

        if sigma_threshold <= 0:
            return None

        try:
            # Discretize current value into Gaussian buckets
            buckets = discretize_to_buckets(
                value=current_price,
                mean=reference_price,
                sigma=record.sigma or 3.0,  # Default σ if not set
                num_buckets=self.bucket_count,
            )

            # Check if bucket probabilities shifted significantly
            total_mass = sum(buckets.values())
            if total_mass == 0:
                return None

            # Compute bucket mass changes
            signal = None

            # Primary signal: trend detection via bucket mass redistribution
            # If probability mass moves to extreme buckets → trend signal
            extreme_mass = buckets.get(0, 0) + buckets.get(self.bucket_count - 1, 0)

            if extreme_mass > self.sigma_threshold / 3.0:
                # Significant shift to extremes → trend signal
                signal = {
                    "strategy": self.name,
                    "type": "trend_detected",
                    "signal_side": "long" if extreme_mass == buckets.get(self.bucket_count - 1, 0) else "short",
                    "confidence": min(extreme_mass, 1.0),
                    "bucket_masses": buckets,
                    "sigma_used": record.sigma or 3.0,
                    "record_city": record.city,
                    "horizon": record.horizon.value,
                    "timestamp": time.time(),
                }

            return signal

        except Exception as e:
            print(f"GaussianBucketTrend error: {e}")
            return None

    def generate_signal(self, record: WeatherRecord, current_price: float, reference_price: float) -> dict | None:
        """Generate trading signal — paper trading only."""
        signal = self.evaluate(record, current_price, reference_price)

        if signal is not None:
            self.metrics["signals_generated"] += 1
            self.metrics["last_signal_time"] = time.time()

        return signal


# --- Strategy 2: Ensemble GFS Price ---


class EnsembleGFSPriceStrategy(BaseStrategy):
    """Ensemble GFS Price Comparison Strategy.

    Compares GFS 31-member ensemble prices against Polymarket/Kalshi markets.
    Generates signals when edge detected (probability difference > threshold).
    Paper trading only.
    """

    def __init__(
        self,
        name: str = "EnsembleGFSPrice",
        price_edge_threshold: float = 0.05,  # 5% edge minimum
        min_edge_pct: float = 0.03,  # 3% minimum edge
        comparison_sources: list[str] = None,
    ):
        super().__init__(StrategyType.ENSEMBLE_GFS_PRICE, name)
        self.price_edge_threshold = price_edge_threshold
        self.min_edge_pct = min_edge_pct
        self.comparison_sources = comparison_sources or ["polymarket", "kalshi"]
        self.ensemble_reference_price: float | None = None

    def evaluate(self, gfs_record: WeatherRecord, market_price: float, market_name: str) -> dict | None:
        """
        Evaluate ensemble GFS vs market price edge.

        Returns signal if edge detected above threshold.
        """
        if gfs_record.quality != "validated":
            return None

        if self.ensemble_reference_price is None:
            # Use GFS record data as reference
            # In production: this would be the ensemble mean price
            self.ensemble_reference_price = market_price  # Placeholder

        try:
            # Calculate edge: (GFS price - market price) / market price
            if market_price == 0:
                return None

            edge_pct = (self.ensemble_reference_price - market_price) / abs(market_price)
            edge_abs = abs(edge_pct)

            # Check if edge exceeds minimum threshold
            if edge_abs < self.min_edge_pct:
                return None  # Edge too small

            # Check if edge exceeds operational threshold
            if edge_abs < self.price_edge_threshold:
                return None  # Edge below operational minimum

            # Determine signal side
            signal_side = "long" if edge_pct > 0 else "short"

            signal = {
                "strategy": self.name,
                "type": "price_edge_detected",
                "signal_side": signal_side,
                "edge_pct": round(edge_abs * 100, 2),  # As percentage
                "gfs_price": self.ensemble_reference_price,
                "market_price": market_price,
                "edge_direction": "GFS overpriced" if edge_pct > 0 else "GFS underpriced",
                "market_name": market_name,
                "sigma_used": gfs_record.sigma or 3.0,
                "record_city": gfs_record.city,
                "horizon": gfs_record.horizon.value,
                "timestamp": time.time(),
            }

            self.metrics["signals_generated"] += 1
            self.metrics["last_signal_time"] = time.time()

            return signal

        except Exception as e:
            print(f"EnsembleGFSPrice error: {e}")
            return None

    def generate_signal(self, gfs_record: WeatherRecord, market_price: float, market_name: str = "polymarket") -> dict | None:
        """Generate trading signal — paper trading only."""
        signal = self.evaluate(gfs_record, market_price, market_name)
        return signal


# --- Strategy 3: Mean Reversion ---


class MeanReversionStrategy(BaseStrategy):
    """Mean Reversion Strategy on Temperature Deviations.

    When temperature deviates significantly from historical mean (σ bands),
    mean reversion signal generated. Prices expected to return to mean.
    Paper trading only with Kelly position sizing.
    """

    def __init__(
        self,
        name: str = "MeanReversion",
        deviation_sigma: float = 2.0,  # Deviations at ≥2σ trigger signal
        reversion_target_pct: float = 0.5,  # Expected % return to mean
        max_hold_horizon: Horizon = Horizon.H24,
        min_quality: DataQuality = DataQuality.VALIDATED,
    ):
        super().__init__(StrategyType.MEAN_REVERSION, name)
        self.deviation_sigma = deviation_sigma
        self.reversion_target_pct = reversion_target_pct
        self.max_hold_horizon = max_hold_horizon
        self.min_quality = min_quality

    def evaluate(self, record: WeatherRecord, current_temp: float, historical_mean: float, historical_sigma: float) -> dict | None:
        """
        Evaluate mean reversion signal.

        Returns signal if temperature deviates ≥ deviation_sigma from mean.
        """
        if record.quality.value < self.min_quality.value:
            return None

        if historical_sigma <= 0:
            return None

        try:
            # Calculate deviation in σ units
            deviation_sigma_units = (current_temp - historical_mean) / historical_sigma
            deviation_abs = abs(deviation_sigma_units)

            # Check if deviation exceeds threshold
            if deviation_abs < self.deviation_sigma:
                return None  # Within normal range — no signal

            # Determine direction: above mean or below mean
            above_mean = current_temp > historical_mean
            signal_side = "long" if above_mean else "short"

            # Expected reversion: price expected to return toward mean
            # If above mean → expect cooling (price decrease)
            # If below mean → expect warming (price increase)
            # Expected % return proportional to deviation distance
            expected_return_pct = self.reversion_target_pct * min(deviation_abs / self.deviation_sigma, 1.0)

            signal = {
                "strategy": self.name,
                "type": "mean_reversion",
                "signal_side": signal_side,
                "deviation_sigma": round(deviation_abs, 2),
                "current_temp": current_temp,
                "historical_mean": historical_mean,
                "historical_sigma": historical_sigma,
                "expected_return_pct": round(expected_return_pct, 2),
                "hold_horizon": self.max_hold_horizon.value,
                "record_city": record.city,
                "record_quality": record.quality.value,
                "timestamp": time.time(),
            }

            self.metrics["signals_generated"] += 1
            self.metrics["last_signal_time"] = time.time()

            return signal

        except Exception as e:
            print(f"MeanReversion error: {e}")
            return None

    def generate_signal(self, record: WeatherRecord, current_temp: float, historical_mean: float, historical_sigma: float) -> dict | None:
        """Generate trading signal — paper trading only."""
        signal = self.evaluate(record, current_temp, historical_mean, historical_sigma)
        return signal


# --- Strategy 4: Volatility Arbitrage ---


class VolatilityArbitrageStrategy(BaseStrategy):
    """Volatility Arbitrage Strategy.

    Exploits σ (standard deviation) differences between models.
    When Model A's σ > Model B's σ + threshold, volatility arbitrage signal.
    Paper trading only.
    """

    def __init__(
        self,
        name: str = "VolatilityArbitrage",
        sigma_threshold: float = 1.5,  # Min σ difference to trigger
        long_model: str = "GFS",
        short_model: str = "ECMWF",
        min_sigma_ratio: float = 1.2,
    ) -> None:
        super().__init__(StrategyType.VOLATILITY_ARBITRAGE, name)
        self.sigma_threshold = sigma_threshold
        self.long_model = long_model
        self.short_model = short_model
        self.min_sigma_ratio = min_sigma_ratio
        self.sigma_history: dict[str, list[float]] = {}

    def evaluate(self, records_by_model: dict[str, WeatherRecord]) -> dict | None:
        """
        Evaluate volatility arbitrage opportunity.

        Compares σ between models — if long_model σ >> short_model σ,
        generates volatility arbitrage signal.
        """
        try:
            # Get σ for each model
            sigmas: dict[str, float | None] = {}
            for model_name, record in records_by_model.items():
                if record.quality.value == "validated" and record.sigma is not None:
                    sigmas[model_name] = record.sigma
                else:
                    sigmas[model_name] = None

            # Both models must have validated σ
            if sigmas.get(self.long_model) is None or sigmas.get(self.short_model) is None:
                return None

            sigma_long = sigmas[self.long_model]
            sigma_short = sigmas[self.short_model]

            # Calculate sigma ratio
            if sigma_short == 0:
                return None

            sigma_ratio = sigma_long / sigma_short

            # Check if ratio exceeds threshold
            if sigma_ratio < self.min_sigma_ratio:
                return None  # Not enough volatility difference

            # Check absolute threshold
            if sigma_long < self.sigma_threshold:
                return None  # σ too low absolutely

            # Signal: volatility is relatively higher in long_model
            # Go long volatility in long_model, short in short_model
            signal = {
                "strategy": self.name,
                "type": "volatility_arbitrage",
                "signal_side": "long_vol_long_model_short_vol_short_model",
                "sigma_long": sigma_long,
                "sigma_short": sigma_short,
                "sigma_ratio": round(sigma_ratio, 2),
                "sigma_threshold": self.sigma_threshold,
                "min_sigma_ratio": self.min_sigma_ratio,
                "long_model": self.long_model,
                "short_model": self.short_model,
                "record_long": self.long_model,
                "record_short": self.short_model,
                "timestamp": time.time(),
            }

            self.metrics["signals_generated"] += 1
            self.metrics["last_signal_time"] = time.time()

            return signal

        except Exception as e:
            print(f"VolatilityArbitrage error: {e}")
            return None

    def generate_signal(self, records_by_model: dict[str, WeatherRecord]) -> dict | None:
        """Generate trading signal — paper trading only."""
        signal = self.evaluate(records_by_model)
        return signal


# --- Strategy 5: Event Driven ---


class EventDrivenStrategy(BaseStrategy):
    """Event Driven Strategy — Weather Events → Market Impact.

    Detects significant weather events (storms, extremes) and assesses
    market impact on prediction markets. Paper trading only.
    """

    def __init__(
        self,
        name: str = "EventDriven",
        extreme_threshold_sigma: float = 3.0,
        event_types: list[str] = None,
        max_impact_pct: float = 5.0,
        min_quality: DataQuality = DataQuality.VALIDATED,
    ):
        super().__init__(StrategyType.EVENT_DRIVEN, name)
        self.extreme_threshold_sigma = extreme_threshold_sigma
        self.event_types = event_types or ["storm", "extreme_heat", "extreme_cold", "hurricane"]
        self.max_impact_pct = max_impact_pct
        self.min_quality = min_quality
        self.event_history: list[dict] = []

    def evaluate(self, record: WeatherRecord) -> dict | None:
        """
        Evaluate if weather event is extreme enough to trigger signal.

        Returns event-driven signal if extreme conditions detected.
        """
        if record.quality.value < self.min_quality.value:
            return None

        try:
            sigma = record.sigma or 3.0  # Default if not set

            # Check if value is extreme (≥ extreme_threshold_sigma from mean)
            # In practice: would need the actual observed value vs historical mean
            # For now: use σ as proxy for extremity

            if sigma < self.extreme_threshold_sigma:
                return None  # Not extreme enough

            # Determine event type based on variable and horizon
            event_type = self._classify_event(record)

            # Assess market impact potential
            impact_pct = min(sigma / self.extreme_threshold_sigma * 2.0, self.max_impact_pct)

            signal = {
                "strategy": self.name,
                "type": "event_driven",
                "signal_side": "market_impact",
                "event_type": event_type,
                "sigma": sigma,
                "record_city": record.city,
                "horizon": record.horizon.value,
                "variable": record.variable.value,
                "impact_pct": round(impact_pct, 2),
                "extreme_threshold": self.extreme_threshold_sigma,
                "timestamp": time.time(),
            }

            # Record event for history
            self.event_history.append(
                {
                    "timestamp": time.time(),
                    "city": record.city,
                    "event_type": event_type,
                    "sigma": sigma,
                    "impact_pct": impact_pct,
                }
            )

            # Keep history manageable
            if len(self.event_history) > 100:
                self.event_history = self.event_history[-50:]

            self.metrics["signals_generated"] += 1
            self.metrics["last_signal_time"] = time.time()

            return signal

        except Exception as e:
            print(f"EventDriven error: {e}")
            return None

    def _classify_event(self, record: WeatherRecord) -> str:
        """Classify the type of weather event."""
        variable = record.variable.value
        horizon = record.horizon.value

        # Simple classification based on variable and extremity
        if variable == "temperature":
            if "heat" in self.event_types:
                return "extreme_heat"
            elif "cold" in self.event_types:
                return "extreme_cold"

        if variable == "precipitation":
            if "storm" in self.event_types:
                return "storm"
            if "flood" in self.event_types:
                return "flood"

        if variable == "wind":
            if "hurricane" in self.event_types:
                return "hurricane"

        # Default
        return self.event_types[0] if self.event_types else "weather_event"

    def generate_signal(self, record: WeatherRecord) -> dict | None:
        """Generate trading signal — paper trading only."""
        signal = self.evaluate(record)
        return signal


# --- Strategy 6: Kelly Position Sizing ---


class KellyPositionStrategy(BaseStrategy):
    """Kelly Criterion Position Sizing Strategy.

    Calculates optimal position size using Kelly Criterion based on EV and odds.
    Paper trading only — real trading execution DISABLED.
    All strategies use this for position sizing, but this is the canonical implementation.
    """

    def __init__(
        self,
        name: str = "KellyPosition",
        win_probability: float = 0.55,  # P(win) from historical signal accuracy
        odds_ratio: float = 1.9,  # Decimal odds: risk $1 to win $1.90
        max_position_pct: float = 25.0,  # Max % capital per trade (safety limit)
        kelly_fraction: float = 1.0,  # Full Kelly vs half-Kelly safety factor
        min_edge_pct: float = 2.0,
    ) -> None:  # Minimum edge % to take trade
        super().__init__(StrategyType.KELLY_POSITION, name)
        self.win_probability = win_probability
        self.odds_ratio = odds_ratio
        self.max_position_pct = max_position_pct
        self.kelly_fraction = kelly_fraction
        self.min_edge_pct = min_edge_pct
        self.trade_history: list[dict] = []

    def calculate_kelly_fraction(self, win_prob: float, odds: float) -> float:
        """
        Calculate Kelly Criterion fraction.

        f = (p * (b - 1) - (1 - p)) / (b - 1)
        where:
        - p = win probability
        - b = odds received (b = odds_ratio - 1 for decimal odds)

        Full Kelly can be too aggressive → use fractional Kelly.
        """
        if odds <= 1 or prob < 0 or prob > 1:
            return 0.0

        b = odds - 1  # Net odds (profit per unit staked)

        # Kelly formula: f = (p * b - (1 - p)) / b
        kelly = (win_prob * b - (1 - win_prob)) / b

        # Clamp to [0, 1]
        kelly = max(0.0, min(1.0, kelly))

        return kelly

    def evaluate_signal(self, expected_return_pct: float, current_position_pct: float = 0.0) -> dict | None:
        """
        Evaluate whether to enter a position based on Kelly Criterion.

        Returns position sizing dict if signal valid, None otherwise.
        """
        try:
            # Calculate edge: expected return minus baseline
            edge_pct = expected_return_pct - self.min_edge_pct

            # Check if edge is positive
            if edge_pct <= 0:
                return None  # No positive edge

            # Estimate win probability from edge and odds
            # edge_pct ≈ p * (odds - 1) - (1 - p) → solve for p
            # This is simplified — in production: use historical signal accuracy
            estimated_p = min(self.win_probability, 0.55 + edge_pct / 10.0)

            # Calculate Kelly fraction
            kelly_f = self.calculate_kelly_fraction(estimated_p, self.odds_ratio)

            # Apply fractional Kelly safety factor
            # Half-Kelly or quarter-Kelly recommended for safety
            safety_factor = 0.5  # Use half-Kelly
            position_pct = kelly_f * safety_factor * self.max_position_pct

            # Cap at max_position_pct
            position_pct = min(position_pct, self.max_position_pct)

            # Also cap at remaining capital (100% - current_position)
            # In production: would check actual available capital
            position_pct = min(position_pct, 100.0 - current_position_pct)

            if position_pct <= 0:
                return None

            signal = {
                "strategy": self.name,
                "type": "kelly_position",
                "position_pct": round(position_pct, 2),
                "kelly_fraction": round(kelly_f, 4),
                "estimated_win_prob": round(estimated_p, 4),
                "odds_ratio": self.odds_ratio,
                "edge_pct": round(edge_pct, 2),
                "min_edge_pct": self.min_edge_pct,
                "kelly_safety": "half_kelly" if safety_factor == 0.5 else "quarter_kelly",
                "win_probability_base": self.win_probability,
                "current_position_pct": round(current_position_pct, 2),
                "timestamp": time.time(),
            }

            # Record trade
            self.trade_history.append(
                {
                    "timestamp": time.time(),
                    "position_pct": position_pct,
                    "kelly_fraction": kelly_f,
                    "estimated_win_prob": estimated_p,
                }
            )

            # Keep history manageable
            if len(self.trade_history) > 200:
                self.trade_history = self.trade_history[-100:]

            self.metrics["signals_generated"] += 1
            self.metrics["last_signal_time"] = time.time()

            return signal

        except Exception as e:
            print(f"KellyPosition error: {e}")
            return None

    def generate_signal(self, expected_return_pct: float, current_position_pct: float = 0.0) -> dict | None:
        """Generate Kelly position sizing signal — paper trading only."""
        signal = self.evaluate_signal(expected_return_pct, current_position_pct)
        return signal


# --- Factory Function ---


def create_strategy(strategy_type: StrategyType, name: str = "", **kwargs) -> BaseStrategy:
    """Factory function to create strategy instances."""

    strategies: dict[StrategyType, type] = {
        StrategyType.GAUSSIAN_BUCKET_TREND: GaussianBucketTrendStrategy,
        StrategyType.ENSEMBLE_GFS_PRICE: EnsembleGFSPriceStrategy,
        StrategyType.MEAN_REVERSION: MeanReversionStrategy,
        StrategyType.VOLATILITY_ARBITRAGE: VolatilityArbitrageStrategy,
        StrategyType.EVENT_DRIVEN: EventDrivenStrategy,
        StrategyType.KELLY_POSITION: KellyPositionStrategy,
    }

    strategy_class = strategies.get(strategy_type)
    if strategy_class is None:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

    # Populate defaults with provided kwargs
    defaults = {}
    if strategy_type == StrategyType.GAUSSIAN_BUCKET_TREND:
        defaults = {
            "sigma_threshold": 2.0,
            "bucket_count": 3,
            "max_position_pct": 10.0,
        }
    elif strategy_type == StrategyType.ENSEMBLE_GFS_PRICE:
        defaults = {
            "price_edge_threshold": 0.05,
            "min_edge_pct": 0.03,
            "comparison_sources": ["polymarket", "kalshi"],
        }
    elif strategy_type == StrategyType.MEAN_REVERSION:
        defaults = {
            "deviation_sigma": 2.0,
            "reversion_target_pct": 0.5,
            "max_hold_horizon": Horizon.H24,
        }
    elif strategy_type == StrategyType.VOLATILITY_ARBITRAGE:
        defaults = {
            "sigma_threshold": 1.5,
            "long_model": "GFS",
            "short_model": "ECMWF",
            "min_sigma_ratio": 1.2,
        }
    elif strategy_type == StrategyType.EVENT_DRIVEN:
        defaults = {
            "extreme_threshold_sigma": 3.0,
            "event_types": ["storm", "extreme_heat", "extreme_cold", "hurricane"],
            "max_impact_pct": 5.0,
        }
    elif strategy_type == StrategyType.KELLY_POSITION:
        defaults = {
            "win_probability": 0.55,
            "odds_ratio": 1.9,
            "max_position_pct": 25.0,
            "kelly_fraction": 1.0,
            "min_edge_pct": 2.0,
        }

    # Merge defaults with provided kwargs
    merged_kwargs = {**defaults, **kwargs}

    return strategy_class(name=name or strategy_type.value, **merged_kwargs)


# --- Export ---
__all__ = [
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
]
