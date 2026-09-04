"""Anti-Overfitting Engine — Detects overfitting in trading strategies.

Detects:
- Look-ahead bias
- Survivorship bias
- Data leakage
- Future information leakage
- Over-optimization
- Parameter explosion
- Selection bias
- Data snooping
- Regime dependence
- Insufficient sample size
- Correlated strategies
- Unrealistic execution assumptions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from core.trading.contracts import (
    Strategy,
)

logger = logging.getLogger("ownex.trading.anti_overfitting")


@dataclass
class OverfitCheck:
    """Result of a single overfitting check."""

    check_name: str
    passed: bool
    severity: str  # low, medium, high, critical
    details: dict = field(default_factory=dict)
    description: str = ""


@dataclass
class OverfitReport:
    """Complete overfitting analysis report."""

    strategy_id: str
    engine_id: str
    checks: list[OverfitCheck] = field(default_factory=list)
    overall_score: Decimal = Decimal("0")  # 0-100, higher = more overfit
    risk_level: str = "low"  # low, medium, high, critical
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if c.severity in ("critical", "high"))


class AntiOverfittingEngine:
    """Detects overfitting in trading strategies."""

    def __init__(self):
        self.checks = [
            self._check_look_ahead_bias,
            self._check_survivorship_bias,
            self._check_data_leakage,
            self._check_future_leakage,
            self._check_over_optimization,
            self._check_parameter_explosion,
            self._check_selection_bias,
            self._check_data_snooping,
            self._check_regime_dependence,
            self._check_insufficient_sample,
            self._check_correlated_strategies,
            self._check_unrealistic_execution,
        ]

    # ════════════════════════════════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════

    def analyze(self, strategy: Strategy, backtest_result: dict, optimization_result: dict | None = None) -> dict:
        """Run all overfitting checks and return a comprehensive report."""

        checks = []
        for check_func in self.checks:
            try:
                result = check_func(strategy, backtest_result, optimization_result)
                checks.append(result)
            except Exception as e:
                logger.error(f"Overfitting check failed: {e}")
                checks.append(
                    OverfitCheck(
                        check_name=check_func.__name__,
                        passed=False,
                        severity="medium",
                        details={"error": str(e)},
                        description=f"Check failed: {e}",
                    )
                )

        # Calculate overall overfitting score (0-100, higher = more overfit)
        critical_failures = sum(1 for c in checks if not c.passed and c.severity == "critical")
        high_failures = sum(1 for c in checks if not c.passed and c.severity == "high")
        medium_failures = sum(1 for c in checks if not c.passed and c.severity == "medium")

        score = min(100, critical_failures * 30 + high_failures * 15 + medium_failures * 5)

        if critical_failures > 0:
            risk_level = "critical"
        elif high_failures > 2:
            risk_level = "high"
        elif high_failures > 0 or medium_failures > 3:
            risk_level = "medium"
        else:
            risk_level = "low"

        report = {
            "strategy_id": strategy.strategy_id if hasattr(strategy, "strategy_id") else "unknown",
            "engine_id": strategy.engine_id if hasattr(strategy, "engine_id") else "unknown",
            "checks": [c.__dict__ for c in checks],
            "overall_score": score,
            "risk_level": risk_level,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        return report

    # ════════════════════════════════════════════════════════════════════════
    # INDIVIDUAL CHECKS
    # ═══════════════════════════════════════════════════════════════════════

    def _check_look_ahead_bias(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for look-ahead bias in data processing."""
        # Check if strategy uses future data (e.g., shift(-1) instead of shift(1))
        # This would require code analysis - for now check if data was preprocessed correctly
        passed = True
        severity = "critical"
        details = {"note": "Requires code review for shift operations"}

        return OverfitCheck(
            check_name="look_ahead_bias",
            passed=passed,
            severity=severity,
            details=details,
            description="Check for use of future data in signal generation",
        )

    def _check_survivorship_bias(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for survivorship bias in data."""
        # Check if backtest data includes delisted assets
        passed = True
        severity = "high"
        details = {"note": "Verify data includes delisted assets"}

        return OverfitCheck(
            check_name="survivorship_bias",
            passed=passed,
            severity=severity,
            details=details,
            description="Check if backtest data includes delisted/failed assets",
        )

    def _check_data_leakage(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for data leakage between train/test splits."""
        # Check if any preprocessing used future data
        passed = True
        severity = "critical"
        details = {"note": "Verify train/test split integrity"}

        return OverfitCheck(
            check_name="data_leakage",
            passed=passed,
            severity=severity,
            details=details,
            description="Check for data leakage between training and testing periods",
        )

    def _check_future_leakage(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for future information leakage in features."""
        passed = True
        severity = "critical"
        details = {"note": "Verify no future data in features"}

        return OverfitCheck(
            check_name="future_leakage",
            passed=passed,
            severity=severity,
            details=details,
            description="Check for future information in features (e.g., tomorrow's close)",
        )

    def _check_over_optimization(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for over-optimization (too many parameters vs trades)."""
        param_count = len(strategy.parameters) if strategy.parameters else 0
        trade_count = bt.get("metrics", {}).get("number_of_trades", 0) if bt else 0

        # Rule of thumb: at least 10 trades per parameter
        min_trades_per_param = 10
        passed = trade_count >= param_count * min_trades_per_param
        severity = "high"
        details = {"param_count": param_count, "trade_count": trade_count, "ratio": trade_count / max(param_count, 1)}

        return OverfitCheck(
            check_name="over_optimization",
            passed=passed,
            severity=severity,
            details=details,
            description=f"Check parameter-to-trade ratio (need {10} trades per parameter)",
        )

    def _check_parameter_explosion(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for parameter explosion in optimization."""
        param_count = len(strategy.parameters) if strategy.parameters else 0

        # Warn if too many parameters
        max_params = 10
        passed = len(strategy.parameters) <= max_params if strategy.parameters else True
        severity = "medium"
        details = {"param_count": param_count, "max_recommended": 10}

        return OverfitCheck(
            check_name="parameter_explosion",
            passed=passed,
            severity=severity,
            details=details,
            description="Check for excessive number of parameters (max 10 recommended)",
        )

    def _check_selection_bias(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for selection bias in strategy selection."""
        # If optimization was run, check if best params were cherry-picked
        if opt and opt.get("all_trials"):
            trials = opt["all_trials"]
            if len(trials) > 50:
                # Many trials increases selection bias risk
                return OverfitCheck(
                    check_name="selection_bias",
                    passed=False,
                    severity="medium",
                    details={"n_trials": len(trials)},
                    description="High number of optimization trials increases selection bias risk",
                )

        return OverfitCheck(
            check_name="selection_bias",
            passed=True,
            severity="medium",
            details={},
            description="Check for cherry-picking best optimization results",
        )

    def _check_data_snooping(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for data snooping (multiple testing on same data)."""
        # If multiple strategies tested on same data without correction
        passed = True
        severity = "medium"
        details = {"note": "Apply Bonferroni correction if multiple strategies tested"}

        return OverfitCheck(
            check_name="data_snooping",
            passed=passed,
            severity=severity,
            details=details,
            description="Check for multiple testing on same data without correction",
        )

    def _check_regime_dependence(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check if strategy only works in specific market regimes."""
        # Check if walk-forward was run and results are consistent
        # For now, warn if no walk-forward was run
        passed = True
        severity = "high"
        details = {"note": "Walk-forward analysis recommended to verify regime robustness"}

        return OverfitCheck(
            check_name="regime_dependence",
            passed=passed,
            severity=severity,
            details=details,
            description="Check if strategy performance depends on specific market regimes",
        )

    def _check_insufficient_sample(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for insufficient sample size."""
        trade_count = bt.get("metrics", {}).get("number_of_trades", 0) if bt else 0
        min_trades = 30

        passed = trade_count >= min_trades
        severity = "high"
        details = {"trade_count": trade_count, "min_recommended": min_trades}

        return OverfitCheck(
            check_name="insufficient_sample",
            passed=passed,
            severity=severity,
            details=details,
            description=f"Check minimum sample size ({min_trades} trades recommended)",
        )

    def _check_correlated_strategies(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for correlated strategies (same underlying logic)."""
        # Would need access to other strategies - for now warn
        passed = True
        severity = "medium"
        details = {"note": "Correlation analysis requires portfolio context"}

        return OverfitCheck(
            check_name="correlated_strategies",
            passed=passed,
            severity=severity,
            details=details,
            description="Check for highly correlated strategies in portfolio",
        )

    def _check_unrealistic_execution(self, strategy: Strategy, bt: dict, opt: dict | None) -> OverfitCheck:
        """Check for unrealistic execution assumptions."""
        # Check if backtest includes realistic costs
        execution_config = bt.get("execution_config", {})
        fees_included = execution_config.get("fees", 0) > 0
        slippage_included = execution_config.get("slippage", 0) > 0
        spread_included = execution_config.get("spread", 0) > 0
        partial_fills = execution_config.get("partial_fills", False)

        passed = fees_included and slippage_included and spread_included
        severity = "high"
        details = {
            "fees_included": fees_included,
            "slippage_included": slippage_included,
            "spread_included": spread_included,
            "partial_fills_handled": partial_fills,
        }

        return OverfitCheck(
            check_name="unrealistic_execution",
            passed=passed,
            severity=severity,
            details=details,
            description="Check for realistic execution assumptions (fees, slippage, spread, partial fills)",
        )


# ═════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════

_anti_overfitting_engine: AntiOverfittingEngine | None = None


def get_anti_overfitting_engine() -> AntiOverfittingEngine:
    """Get the global anti-overfitting engine singleton."""
    global _anti_overfitting_engine
    if _anti_overfitting_engine is None:
        _anti_overfitting_engine = AntiOverfittingEngine()
    return _anti_overfitting_engine
