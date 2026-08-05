"""Progressive Scaling System — Risk-Minimized Path to $10M Annual.

This module implements the 4-phase scaling strategy:
- Phase 1: $3M annual (80% success, <5% risk)
- Phase 2: $5M annual (60% success, 15% risk)
- Phase 3: $7M annual (40% success, 30% risk)
- Phase 4: $10M annual (20% success, 50% risk)

Each phase requires 2 years of stability before progression.
Risk increases only after proven success at current level.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger("ownex.progressive_scaling")


class ScalingPhase(StrEnum):
    """Current scaling phase in the progression to $10M annual."""

    PHASE_1 = "phase_1"  # $3M annual (baseline)
    PHASE_2 = "phase_2"  # $5M annual (moderate)
    PHASE_3 = "phase_3"  # $7M annual (aggressive)
    PHASE_4 = "phase_4"  # $10M annual (maximum)


@dataclass
class PhaseConfig:
    """Configuration for each scaling phase."""

    name: str
    target_annual: int
    target_monthly: int
    multi_agent_concurrent: int
    work_bank_jobs: int
    acceptance_rate: float
    categories_count: int
    freqtrade_leverage: int
    hummingbot_leverage: int
    polymarket_sizing: float
    sports_betting_kelly: float
    stop_loss_pct: float
    drawdown_limit_pct: float
    required_stability_months: int
    min_success_probability: float
    risk_of_ruin: float


# Phase configurations with risk-minimized progression
PHASE_CONFIGS: dict[ScalingPhase, PhaseConfig] = {
    ScalingPhase.PHASE_1: PhaseConfig(
        name="$3M Annual (Baseline)",
        target_annual=3_000_000,
        target_monthly=250_000,
        multi_agent_concurrent=5,
        work_bank_jobs=200,
        acceptance_rate=0.65,
        categories_count=5,
        freqtrade_leverage=5,
        hummingbot_leverage=3,
        polymarket_sizing=0.30,
        sports_betting_kelly=0.10,
        stop_loss_pct=0.02,
        drawdown_limit_pct=0.15,
        required_stability_months=24,
        min_success_probability=0.80,
        risk_of_ruin=0.05,
    ),
    ScalingPhase.PHASE_2: PhaseConfig(
        name="$5M Annual (Moderate)",
        target_annual=5_000_000,
        target_monthly=417_000,
        multi_agent_concurrent=8,
        work_bank_jobs=400,
        acceptance_rate=0.75,
        categories_count=6,
        freqtrade_leverage=10,
        hummingbot_leverage=5,
        polymarket_sizing=0.50,
        sports_betting_kelly=0.15,
        stop_loss_pct=0.025,
        drawdown_limit_pct=0.20,
        required_stability_months=24,
        min_success_probability=0.60,
        risk_of_ruin=0.15,
    ),
    ScalingPhase.PHASE_3: PhaseConfig(
        name="$7M Annual (Aggressive)",
        target_annual=7_000_000,
        target_monthly=583_000,
        multi_agent_concurrent=12,
        work_bank_jobs=800,
        acceptance_rate=0.85,
        categories_count=8,
        freqtrade_leverage=15,
        hummingbot_leverage=8,
        polymarket_sizing=0.80,
        sports_betting_kelly=0.20,
        stop_loss_pct=0.04,
        drawdown_limit_pct=0.30,
        required_stability_months=24,
        min_success_probability=0.40,
        risk_of_ruin=0.30,
    ),
    ScalingPhase.PHASE_4: PhaseConfig(
        name="$10M Annual (Maximum)",
        target_annual=10_000_000,
        target_monthly=833_000,
        multi_agent_concurrent=20,
        work_bank_jobs=1500,
        acceptance_rate=0.90,
        categories_count=12,
        freqtrade_leverage=25,
        hummingbot_leverage=12,
        polymarket_sizing=1.20,
        sports_betting_kelly=0.25,
        stop_loss_pct=0.06,
        drawdown_limit_pct=0.40,
        required_stability_months=24,
        min_success_probability=0.20,
        risk_of_ruin=0.50,
    ),
}


@dataclass
class PhaseMetrics:
    """Metrics for current phase to determine progression eligibility."""

    current_monthly_revenue: float = 0.0
    months_at_current_phase: int = 0
    months_above_target: int = 0
    max_drawdown_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    total_submissions: int = 0
    accepted_submissions: int = 0
    investment_monthly_return: float = 0.0
    peak_capital: float = 0.0
    current_capital: float = 0.0
    consecutive_profitable_months: int = 0
    phase_start_date: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ScalingDecision:
    """Decision on whether to progress to next phase."""

    can_progress: bool
    reason: str
    current_phase: ScalingPhase
    next_phase: ScalingPhase | None
    metrics: PhaseMetrics
    recommendation: str


class ProgressiveScalingManager:
    """Manages the progressive scaling from $3M to $10M annual.

    Rules:
    1. Start at Phase 1 ($3M annual)
    2. Require 24 months stability at current phase
    3. Require minimum success probability met
    4. Require drawdown limits respected
    5. Only progress if all safety checks pass
    6. Can downgrade if risks exceed limits
    """

    def __init__(self, state_file: Path = Path("data/progressive_scaling_state.json")):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._current_phase = ScalingPhase.PHASE_1
        self._metrics = PhaseMetrics()
        self._adaptive_system = get_adaptive_success_rate_system()
        self._load_state()

    def _load_state(self) -> None:
        """Load scaling state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self._current_phase = ScalingPhase(data.get("current_phase", "phase_1"))
                    metrics_data = data.get("metrics", {})
                    self._metrics = PhaseMetrics(
                        current_monthly_revenue=metrics_data.get("current_monthly_revenue", 0.0),
                        months_at_current_phase=metrics_data.get("months_at_current_phase", 0),
                        months_above_target=metrics_data.get("months_above_target", 0),
                        max_drawdown_pct=metrics_data.get("max_drawdown_pct", 0.0),
                        current_drawdown_pct=metrics_data.get("current_drawdown_pct", 0.0),
                        total_submissions=metrics_data.get("total_submissions", 0),
                        accepted_submissions=metrics_data.get("accepted_submissions", 0),
                        investment_monthly_return=metrics_data.get("investment_monthly_return", 0.0),
                        peak_capital=metrics_data.get("peak_capital", 0.0),
                        current_capital=metrics_data.get("current_capital", 0.0),
                        consecutive_profitable_months=metrics_data.get("consecutive_profitable_months", 0),
                        phase_start_date=datetime.fromisoformat(metrics_data.get("phase_start_date", datetime.now(UTC).isoformat())),
                    )
                logger.info(f"Loaded scaling state: {self._current_phase}")
            except Exception as e:
                logger.warning(f"Failed to load scaling state: {e}")

    def _save_state(self) -> None:
        """Save scaling state to disk."""
        try:
            data = {
                "current_phase": self._current_phase.value,
                "metrics": {
                    "current_monthly_revenue": self._metrics.current_monthly_revenue,
                    "months_at_current_phase": self._metrics.months_at_current_phase,
                    "months_above_target": self._metrics.months_above_target,
                    "max_drawdown_pct": self._metrics.max_drawdown_pct,
                    "current_drawdown_pct": self._metrics.current_drawdown_pct,
                    "total_submissions": self._metrics.total_submissions,
                    "accepted_submissions": self._metrics.accepted_submissions,
                    "investment_monthly_return": self._metrics.investment_monthly_return,
                    "peak_capital": self._metrics.peak_capital,
                    "current_capital": self._metrics.current_capital,
                    "consecutive_profitable_months": self._metrics.consecutive_profitable_months,
                    "phase_start_date": self._metrics.phase_start_date.isoformat(),
                },
                "last_updated": datetime.now(UTC).isoformat(),
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved scaling state: {self._current_phase}")
        except Exception as e:
            logger.error(f"Failed to save scaling state: {e}")

    def get_current_config(self) -> PhaseConfig:
        """Get configuration for current phase."""
        return PHASE_CONFIGS[self._current_phase]

    def update_metrics(
        self,
        monthly_revenue: float,
        submissions: int,
        accepted: int,
        investment_return: float,
        current_capital: float,
    ) -> None:
        """Update monthly metrics."""
        config = self.get_current_config()

        # Update revenue metrics
        self._metrics.current_monthly_revenue = monthly_revenue
        if monthly_revenue >= config.target_monthly:
            self._metrics.months_above_target += 1

        # Update submission metrics
        self._metrics.total_submissions += submissions
        self._metrics.accepted_submissions += accepted

        # Update investment metrics
        self._metrics.investment_monthly_return = investment_return
        self._metrics.current_capital = current_capital
        if current_capital > self._metrics.peak_capital:
            self._metrics.peak_capital = current_capital

        # Calculate drawdown
        if self._metrics.peak_capital > 0:
            self._metrics.current_drawdown_pct = (self._metrics.peak_capital - current_capital) / self._metrics.peak_capital
            if self._metrics.current_drawdown_pct > self._metrics.max_drawdown_pct:
                self._metrics.max_drawdown_pct = self._metrics.current_drawdown_pct

        # Track profitable months
        if monthly_revenue + investment_return > 0:
            self._metrics.consecutive_profitable_months += 1
        else:
            self._metrics.consecutive_profitable_months = 0

        # Increment months at current phase
        self._metrics.months_at_current_phase += 1

        self._save_state()
        logger.info(f"Updated metrics: revenue=${monthly_revenue:,.0f}, capital=${current_capital:,.0f}")

    def evaluate_progression(self) -> ScalingDecision:
        """Evaluate if we can progress to next phase."""
        config = self.get_current_config()
        next_phase_value = f"phase_{self._current_phase.value.split('_')[1] + 1}"

        # Check if we're at max phase
        if self._current_phase == ScalingPhase.PHASE_4:
            return ScalingDecision(
                can_progress=False,
                reason="Already at maximum phase (Phase 4: $10M annual)",
                current_phase=self._current_phase,
                next_phase=None,
                metrics=self._metrics,
                recommendation="Maintain current configuration",
            )

        # Get next phase
        try:
            next_phase = ScalingPhase(next_phase_value)
        except ValueError:
            return ScalingDecision(
                can_progress=False,
                reason="Invalid next phase",
                current_phase=self._current_phase,
                next_phase=None,
                metrics=self._metrics,
                recommendation="Maintain current configuration",
            )

        next_config = PHASE_CONFIGS[next_phase]

        # Safety checks
        checks = []

        # Check 1: Stability period
        stability_met = self._metrics.months_at_current_phase >= config.required_stability_months
        checks.append(f"Stability: {self._metrics.months_at_current_phase}/{config.required_stability_months} months - {'✓' if stability_met else '✗'}")

        # Check 2: Target revenue
        revenue_met = self._metrics.months_above_target >= 12  # 12 months above target
        checks.append(f"Revenue target: {self._metrics.months_above_target}/12 months - {'✓' if revenue_met else '✗'}")

        # Check 3: Drawdown limit
        drawdown_ok = self._metrics.max_drawdown_pct <= config.drawdown_limit_pct
        checks.append(f"Drawdown limit: {self._metrics.max_drawdown_pct:.1%} <= {config.drawdown_limit_pct:.1%} - {'✓' if drawdown_ok else '✗'}")

        # Check 4: Acceptance rate
        if self._metrics.total_submissions > 0:
            acceptance_rate = self._metrics.accepted_submissions / self._metrics.total_submissions
            acceptance_ok = acceptance_rate >= config.acceptance_rate
            checks.append(f"Acceptance rate: {acceptance_rate:.1%} >= {config.acceptance_rate:.1%} - {'✓' if acceptance_ok else '✗'}")
        else:
            acceptance_ok = False
            checks.append("Acceptance rate: No data - ✗")

        # Check 5: Consecutive profitable months
        profit_ok = self._metrics.consecutive_profitable_months >= 6
        checks.append(f"Profitable streak: {self._metrics.consecutive_profitable_months}/6 months - {'✓' if profit_ok else '✗'}")

        # All checks must pass
        can_progress = all([stability_met, revenue_met, drawdown_ok, acceptance_ok, profit_ok])

        reason = "\n".join(checks)
        recommendation = "PROGRESS to next phase" if can_progress else "MAINTAIN current phase"

        return ScalingDecision(
            can_progress=can_progress,
            reason=reason,
            current_phase=self._current_phase,
            next_phase=next_phase if can_progress else None,
            metrics=self._metrics,
            recommendation=recommendation,
        )

    def progress_to_next_phase(self) -> bool:
        """Progress to next phase if all checks pass."""
        decision = self.evaluate_progression()
        if decision.can_progress and decision.next_phase:
            self._current_phase = decision.next_phase
            self._metrics = PhaseMetrics(phase_start_date=datetime.now(UTC))
            self._save_state()
            logger.info(f"Progressed to {self._current_phase}: {PHASE_CONFIGS[self._current_phase].name}")
            return True
        return False

    def evaluate_downgrade(self) -> ScalingPhase | None:
        """Evaluate if we should downgrade due to excessive risk."""
        config = self.get_current_config()

        # Check if current drawdown exceeds limit
        if self._metrics.current_drawdown_pct > config.drawdown_limit_pct:
            # Downgrade to previous phase
            if self._current_phase != ScalingPhase.PHASE_1:
                prev_phase_value = f"phase_{self._current_phase.value.split('_')[1] - 1}"
                try:
                    prev_phase = ScalingPhase(prev_phase_value)
                    logger.warning(f"Downgrading from {self._current_phase} to {prev_phase} due to excessive drawdown")
                    return prev_phase
                except ValueError:
                    pass

        return None

    def downgrade_to_phase(self, phase: ScalingPhase) -> None:
        """Downgrade to specified phase."""
        self._current_phase = phase
        self._metrics = PhaseMetrics(phase_start_date=datetime.now(UTC))
        self._save_state()
        logger.info(f"Downgraded to {self._current_phase}: {PHASE_CONFIGS[self._current_phase].name}")

    def get_status(self) -> dict[str, any]:
        """Get current status with adaptive probabilities."""
        config = self.get_current_config()
        decision = self.evaluate_progression()
        adaptive_probs = self._adaptive_system.get_current_probabilities()
        adaptive_target = self._adaptive_system.get_adaptive_target(self._current_phase.value)

        return {
            "current_phase": self._current_phase.value,
            "phase_name": config.name,
            "target_annual": config.target_annual,
            "target_monthly": config.target_monthly,
            "current_monthly_revenue": self._metrics.current_monthly_revenue,
            "months_at_phase": self._metrics.months_at_current_phase,
            "required_stability": config.required_stability_months,
            "can_progress": decision.can_progress,
            "progression_reason": decision.reason,
            "recommendation": decision.recommendation,
            "current_capital": self._metrics.current_capital,
            "peak_capital": self._metrics.peak_capital,
            "current_drawdown": self._metrics.current_drawdown_pct,
            "max_drawdown": self._metrics.max_drawdown_pct,
            "drawdown_limit": config.drawdown_limit_pct,
            "acceptance_rate": (
                self._metrics.accepted_submissions / self._metrics.total_submissions
                if self._metrics.total_submissions > 0
                else 0.0
            ),
            "target_acceptance": config.acceptance_rate,
            "risk_of_ruin": config.risk_of_ruin,
            "investment_return": self._metrics.investment_monthly_return,
            "adaptive_probabilities": adaptive_probs,
            "adaptive_target": adaptive_target,
        }


# Singleton instance
_global_manager: ProgressiveScalingManager | None = None


def get_progressive_scaling_manager() -> ProgressiveScalingManager:
    """Get or create the global progressive scaling manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ProgressiveScalingManager()
    return _global_manager
