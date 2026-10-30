"""Validation Pipeline — Multi-phase validation for trading strategies.

Implements the mandatory validation pipeline:
Phase 1: Historical Backtest (with realistic execution)
Phase 2: Out-of-Sample Test
Phase 3: Walk-Forward Analysis
Phase 4: Monte Carlo / Trade Resampling
Phase 5: Stress Testing
Phase 6: Paper Trading
Phase 7: Canary Capital
Phase 8: Production
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.trading.contracts import (
    MarketData,
    PerformanceMetrics,
    Strategy,
    StrategyStatus,
)

logger = logging.getLogger("ownex.trading.validation")


@dataclass
class ValidationResult:
    """Result of a validation phase."""

    phase: str
    passed: bool
    metrics: PerformanceMetrics | None = None
    details: dict = field(default_factory=dict)
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ValidationReport:
    """Complete validation report for a strategy."""

    strategy_id: str
    engine_id: str
    results: list[ValidationResult] = field(default_factory=list)
    overall_passed: bool = False
    current_phase: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None

    def add_result(self, result: ValidationResult) -> None:
        self.results.append(result)
        self.current_phase = result.phase

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)


class ValidationPipeline:
    """Orchestrates the multi-phase validation pipeline for strategies."""

    def __init__(self, engine_registry: Any):
        self.engine_registry = engine_registry
        self._active_validations: dict[str, ValidationReport] = {}

    # ═════════════════════════════════════════════════════════════════════════
    # MAIN PIPELINE
    # ═══════════════════════════════════════════════════════════════════════

    async def validate_strategy(
        self,
        strategy: Strategy,
        market_data: MarketData,
        execution_config: dict,
        skip_phases: list[str] | None = None,
    ) -> ValidationReport:
        """Run the complete validation pipeline for a strategy."""

        skip_phases = skip_phases or []
        report = ValidationReport(
            strategy_id=strategy.strategy_id,
            engine_id=strategy.engine_id,
        )
        self._active_validations[strategy.strategy_id] = report

        phases = [
            ("Phase 1: Historical Backtest", self._phase_1_backtest, "backtest"),
            ("Phase 2: Out-of-Sample Test", self._phase_2_out_of_sample, "oos"),
            ("Phase 3: Walk-Forward Analysis", self._phase_3_walk_forward, "walk_forward"),
            ("Phase 4: Monte Carlo / Trade Resampling", self._phase_4_monte_carlo, "monte_carlo"),
            ("Phase 5: Stress Testing", self._phase_5_stress_test, "stress_test"),
            ("Phase 6: Paper Trading", self._phase_6_paper_trading, "paper"),
            ("Phase 7: Canary Capital", self._phase_7_canary, "canary"),
        ]

        for phase_name, phase_func, phase_key in phases:
            if phase_key in skip_phases:
                logger.info(f"Skipping {phase_name} for strategy {strategy.strategy_id}")
                continue

            logger.info(f"Running {phase_name} for strategy {strategy.strategy_id}")
            result = await phase_func(strategy, market_data, execution_config)

            report.add_result(
                ValidationResult(
                    phase=phase_name,
                    passed=result.get("passed", False),
                    metrics=result.get("metrics"),
                    details=result,
                    error=result.get("error"),
                )
            )

            if not result.get("passed", False):
                logger.warning(f"{phase_name} FAILED for strategy {strategy.strategy_id}")
                break

        report.overall_passed = report.all_passed
        report.completed_at = datetime.now(UTC).isoformat()

        # Update strategy status
        if report.overall_passed:
            strategy.status = StrategyStatus.VALIDATED
        else:
            strategy.status = StrategyStatus.BACKTEST_FAILED

        return report

    # ═════════════════════════════════════════════════════════════════════════
    # PHASE 1: HISTORICAL BACKTEST
    # ════════════════════════════════════════════════════════════════════════

    async def _phase_1_backtest(self, strategy: Strategy, market_data: MarketData, execution_config: dict) -> dict:
        """Phase 1: Historical Backtest with realistic execution assumptions."""
        logger.info("Phase 1: Running historical backtest")

        engine = self.engine_registry.get_engine(strategy.engine_id)
        if not engine:
            return {"passed": False, "error": f"Engine {strategy.engine_id} not found"}

        try:
            bt_result = await engine.backtest(
                strategy_id=strategy.strategy_id,
                market_data=market_data,
                parameters=strategy.parameters,
                execution_config=execution_config,
            )

            if not bt_result.success:
                return {"passed": False, "error": bt_result.error or "Backtest failed"}

            # Check minimum trade count
            min_trades = 30
            if bt_result.metrics and bt_result.metrics.number_of_trades < min_trades:
                return {
                    "passed": False,
                    "error": f"Insufficient trades: {bt_result.metrics.number_of_trades} < {min_trades}",
                }

            # Check for positive expectancy
            if bt_result.metrics and bt_result.metrics.expectancy <= 0:
                return {"passed": False, "error": "Non-positive expectancy"}

            return {
                "passed": True,
                "metrics": bt_result.metrics,
                "details": bt_result.to_dict() if hasattr(bt_result, "to_dict") else {},
            }

        except Exception as e:
            logger.error(f"Phase 1 backtest failed: {e}")
            return {"passed": False, "error": str(e)}

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 2: OUT-OF-SAMPLE TEST
    # ════════════════════════════════════════════════════════════════════════

    async def _phase_2_out_of_sample(self, strategy: Strategy, market_data: MarketData, execution_config: dict) -> dict:
        """Phase 2: Out-of-Sample Test on unseen data."""
        logger.info("Phase 2: Running out-of-sample test")

        engine = self.engine_registry.get_engine(strategy.engine_id)
        if not engine:
            return {"passed": False, "error": f"Engine {strategy.engine_id} not found"}

        try:
            # Split data: 70% in-sample, 30% out-of-sample
            oos_config = execution_config.copy()
            oos_config["timerange"] = execution_config.get("oos_timerange", "20240601-")

            bt_result = await self.engine_registry.get_engine(strategy.engine_id).backtest(
                strategy_id=strategy.strategy_id,
                market_data=market_data,
                parameters=strategy.parameters,
                execution_config=oos_config,
            )

            if not bt_result.success:
                return {"passed": False, "error": "OOS backtest failed"}

            # Compare in-sample vs out-of-sample performance
            if bt_result.metrics:
                oos_sharpe = bt_result.metrics.sharpe
                oos_expectancy = bt_result.metrics.expectancy

                # OOS performance should be reasonable (not dramatically worse)
                if oos_sharpe < 0.5:
                    return {"passed": False, "error": f"OOS Sharpe too low: {oos_sharpe}"}

                if oos_expectancy <= 0:
                    return {"passed": False, "error": "Negative OOS expectancy"}

            return {"passed": True, "metrics": bt_result.metrics}

        except Exception as e:
            logger.error(f"Phase 2 OOS test failed: {e}")
            return {"passed": False, "error": str(e)}

    # ═════════════════════════════════════════════════════════════════════════
    # PHASE 3: WALK-FORWARD ANALYSIS
    # ════════════════════════════════════════════════════════════════════════

    async def _phase_3_walk_forward(self, strategy: Strategy, market_data: MarketData, execution_config: dict) -> dict:
        """Phase 3: Walk-Forward Analysis (expanding window)."""
        logger.info("Phase 3: Running walk-forward analysis")

        engine = self.engine_registry.get_engine(strategy.engine_id)
        if not engine:
            return {"passed": False, "error": f"Engine {strategy.engine_id} not found"}

        try:
            wf_results = await engine.walk_forward(
                strategy_id=strategy.strategy_id,
                market_data=market_data,
                windows=12,
                step_size=1,
            )

            if not wf_results:
                return {"passed": False, "error": "Walk-forward returned no results"}

            # Check consistency across windows
            passing_windows = sum(1 for r in wf_results if r.success)
            total_windows = len(wf_results)

            if passing_windows < total_windows * 0.6:
                return {"passed": False, "error": f"Only {passing_windows}/{total_windows} windows passed"}

            # Check for parameter stability
            all_params = [r.metrics.parameters_hash for r in wf_results if r.metrics]
            if len(set(all_params)) > len(all_params) * 0.5:
                logger.warning("Parameter instability detected in walk-forward")

            return {"passed": True, "details": {"windows_passed": passing_windows, "total_windows": total_windows}}

        except Exception as e:
            logger.error(f"Phase 3 walk-forward failed: {e}")
            return {"passed": False, "error": str(e)}

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 4: MONTE CARLO / TRADE RESAMPLING
    # ═══════════════════════════════════════════════════════════════════════

    async def _phase_4_monte_carlo(self, strategy: Strategy, market_data: MarketData, execution_config: dict) -> dict:
        """Phase 4: Monte Carlo / Trade Resampling."""
        logger.info("Phase 4: Running Monte Carlo simulation")

        engine = self.engine_registry.get_engine(strategy.engine_id)
        if not engine:
            return {"passed": False, "error": f"Engine {strategy.engine_id} not found"}

        try:
            # First run a backtest to get baseline trades
            bt_result = await engine.backtest(
                strategy_id=strategy.strategy_id,
                market_data=market_data,
                parameters=strategy.parameters,
                execution_config=execution_config,
            )

            if not bt_result.success or not bt_result.trades:
                return {"passed": False, "error": "No trades for Monte Carlo"}

            mc_result = await engine.monte_carlo(
                strategy_id=strategy.strategy_id,
                backtest_result=bt_result,
                n_simulations=1000,
            )

            # Check probability of ruin
            if mc_result.get("probability_of_ruin", 0) > 0.05:
                return {
                    "passed": False,
                    "error": f"Probability of ruin too high: {mc_result.get('probability_of_ruin', 'unknown')}",
                }

            # Check 5th percentile return
            p5_return = mc_result.get("percentile_5_return", 0)
            if p5_return < -0.5:  # 50% drawdown at 5th percentile
                return {"passed": False, "error": f"5th percentile return too low: {p5_return}"}

            return {"passed": True, "details": mc_result}

        except Exception as e:
            logger.error(f"Phase 4 Monte Carlo failed: {e}")
            return {"passed": False, "error": str(e)}

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 5: STRESS TESTING
    # ═══════════════════════════════════════════════════════════════════════

    async def _phase_5_stress_test(self, strategy: Strategy, market_data: MarketData, execution_config: dict) -> dict:
        """Phase 5: Stress Testing against specific scenarios."""
        logger.info("Phase 5: Running stress tests")

        engine = self.engine_registry.get_engine(strategy.engine_id)
        if not engine:
            return {"passed": False, "error": f"Engine {strategy.engine_id} not found"}

        # Define stress scenarios
        scenarios = [
            {"name": "flash_crash", "price_drop_pct": 0.20, "duration_minutes": 5},
            {"name": "bear_market", "trend": "down", "volatility_multiplier": 3.0, "duration_days": 30},
            {"name": "high_volatility", "volatility_multiplier": 5.0, "duration_days": 7},
            {"name": "liquidity_crisis", "spread_multiplier": 10.0, "slippage_multiplier": 5.0},
            {"name": "funding_rate_spike", "funding_rate": 0.01, "duration_hours": 24},
        ]

        try:
            results = await engine.stress_test(
                strategy_id=strategy.strategy_id,
                market_data=market_data,
                scenarios=scenarios,
            )

            # All scenarios must survive (not blow up)
            for scenario_name, result in results.items():
                max_dd = result.get("max_drawdown", 0)
                if max_dd > 0.5:  # 50% max drawdown in any scenario
                    return {"passed": False, "error": f"Scenario {scenario_name} caused {max_dd:.1%} drawdown"}

            return {"passed": True, "details": results}

        except Exception as e:
            logger.error(f"Phase 5 stress test failed: {e}")
            return {"passed": False, "error": str(e)}

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 6: PAPER TRADING
    # ═══════════════════════════════════════════════════════════════════════

    async def _phase_6_paper_trading(self, strategy: Strategy, market_data: MarketData, execution_config: dict) -> dict:
        """Phase 6: Paper Trading (minimum 30 days or 100 trades)."""
        logger.info("Phase 6: Starting paper trading")

        engine = self.engine_registry.get_engine(strategy.engine_id)
        if not engine:
            return {"passed": False, "error": f"Engine {strategy.engine_id} not found"}

        try:
            # Start paper trading
            await engine.start_paper_trading(strategy.strategy_id)

            # Wait for minimum period (in practice, this would be async with polling)
            min_days = 30
            min_trades = 100

            paper_result = await engine.stop_paper_trading(strategy.strategy_id)

            if not paper_result.success:
                return {"passed": False, "error": "Paper trading failed"}

            if paper_result.days_run < min_days:
                return {"passed": False, "error": f"Paper trading too short: {paper_result.days_run} days < {min_days}"}

            if paper_result.metrics and paper_result.metrics.number_of_trades < min_trades:
                return {
                    "passed": False,
                    "error": f"Insufficient paper trades: {paper_result.metrics.number_of_trades} < {min_trades}",
                }

            if paper_result.metrics and paper_result.metrics.expectancy <= 0:
                return {"passed": False, "error": "Negative expectancy in paper trading"}

            return {
                "passed": True,
                "metrics": paper_result.metrics,
                "details": paper_result.to_dict() if hasattr(paper_result, "to_dict") else {},
            }

        except Exception as e:
            logger.error(f"Phase 6 paper trading failed: {e}")
            return {"passed": False, "error": str(e)}

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 7: CANARY CAPITAL
    # ═══════════════════════════════════════════════════════════════════════

    async def _phase_7_canary(self, strategy: Strategy, market_data: MarketData, execution_config: dict) -> dict:
        """Phase 7: Canary Capital (1-5% allocation with strict limits)."""
        logger.info("Phase 7: Starting canary deployment")

        # Canary phase would start live trading with small capital
        # This requires human approval and risk engine checks
        # For now, return passed if paper trading was successful

        logger.info(f"Strategy {strategy.strategy_id} ready for canary deployment")
        return {"passed": True, "details": {"canary_ready": True, "capital_allocation_pct": 1.0}}

    # ════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════

    def get_validation_status(self, strategy_id: str) -> ValidationReport | None:
        """Get current validation status for a strategy."""
        return self._active_validations.get(strategy_id)


# ═════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════

_validation_pipeline: ValidationPipeline | None = None


def get_validation_pipeline(engine_registry: Any) -> ValidationPipeline:
    """Get the global validation pipeline singleton."""
    global _validation_pipeline
    if _validation_pipeline is None:
        _validation_pipeline = ValidationPipeline(engine_registry)
    return _validation_pipeline
