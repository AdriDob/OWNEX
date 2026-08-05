"""Adaptive Success Rate System — Dynamic learning from real outcomes.

This system implements adaptive success probabilities that improve over time:
- Starts with conservative baseline estimates
- Collects real outcome data from all attempts
- Updates success probabilities using Bayesian learning
- Shows improvement trajectory in dashboard
- Adapts thresholds based on learned performance
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.adaptive_success_rate")


class OutcomeType(StrEnum):
    """Types of outcomes for learning."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class AttemptRecord:
    """Record of a single attempt with outcome."""

    id: str
    phase: str
    attempt_type: str  # bug_bounty, dev_bounty, investment, etc.
    timestamp: datetime
    target_value: float  # target revenue or return
    actual_value: float  # actual revenue or return
    outcome: OutcomeType
    confidence_before: float  # predicted success probability
    confidence_after: float  # updated success probability
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdaptiveProbabilities:
    """Adaptive success probabilities for each phase — can reach 100% with sufficient evidence."""

    phase_1_baseline: float = 0.80  # Conservative baseline
    phase_1_learned: float = 0.80  # Updated by learning
    phase_1_confidence: float = 0.5  # Confidence in learned value (0-1)

    phase_2_baseline: float = 0.60
    phase_2_learned: float = 0.60
    phase_2_confidence: float = 0.5

    phase_3_baseline: float = 0.40
    phase_3_learned: float = 0.40
    phase_3_confidence: float = 0.5

    phase_4_baseline: float = 0.20
    phase_4_learned: float = 0.20
    phase_4_confidence: float = 0.5

    def get_learned_probability(self, phase: str) -> float:
        """Get learned probability for a phase."""
        attr = f"{phase}_learned"
        return getattr(self, attr, 0.5)

    def get_baseline_probability(self, phase: str) -> float:
        """Get baseline probability for a phase."""
        attr = f"{phase}_baseline"
        return getattr(self, attr, 0.5)

    def get_confidence(self, phase: str) -> float:
        """Get confidence in learned value."""
        attr = f"{phase}_confidence"
        return getattr(self, attr, 0.5)


class AdaptiveSuccessRateSystem:
    """System for adaptive success rate learning and prediction.

    Uses Bayesian updating to improve success probability estimates
    based on real outcome data.
    """

    def __init__(self, state_file: Path = Path("data/adaptive_success_rate_state.json")):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._probabilities = AdaptiveProbabilities()
        self._attempts: list[AttemptRecord] = []
        self._load_state()

    def _load_state(self) -> None:
        """Load adaptive success rate state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    probs_data = data.get("probabilities", {})
                    self._probabilities = AdaptiveProbabilities(**probs_data)
                    attempts_data = data.get("attempts", [])
                    self._attempts = [
                        AttemptRecord(
                            id=a["id"],
                            phase=a["phase"],
                            attempt_type=a["attempt_type"],
                            timestamp=datetime.fromisoformat(a["timestamp"]),
                            target_value=a["target_value"],
                            actual_value=a["actual_value"],
                            outcome=OutcomeType(a["outcome"]),
                            confidence_before=a["confidence_before"],
                            confidence_after=a["confidence_after"],
                            metadata=a.get("metadata", {}),
                        )
                        for a in attempts_data
                    ]
                logger.info(f"Loaded adaptive success rate state: {len(self._attempts)} attempts")
            except Exception as e:
                logger.warning(f"Failed to load adaptive success rate state: {e}")

    def _save_state(self) -> None:
        """Save adaptive success rate state to disk."""
        try:
            data = {
                "probabilities": {
                    "phase_1_baseline": self._probabilities.phase_1_baseline,
                    "phase_1_learned": self._probabilities.phase_1_learned,
                    "phase_1_confidence": self._probabilities.phase_1_confidence,
                    "phase_2_baseline": self._probabilities.phase_2_baseline,
                    "phase_2_learned": self._probabilities.phase_2_learned,
                    "phase_2_confidence": self._probabilities.phase_2_confidence,
                    "phase_3_baseline": self._probabilities.phase_3_baseline,
                    "phase_3_learned": self._probabilities.phase_3_learned,
                    "phase_3_confidence": self._probabilities.phase_3_confidence,
                    "phase_4_baseline": self._probabilities.phase_4_baseline,
                    "phase_4_learned": self._probabilities.phase_4_learned,
                    "phase_4_confidence": self._probabilities.phase_4_confidence,
                },
                "attempts": [
                    {
                        "id": a.id,
                        "phase": a.phase,
                        "attempt_type": a.attempt_type,
                        "timestamp": a.timestamp.isoformat(),
                        "target_value": a.target_value,
                        "actual_value": a.actual_value,
                        "outcome": a.outcome.value,
                        "confidence_before": a.confidence_before,
                        "confidence_after": a.confidence_after,
                        "metadata": a.metadata,
                    }
                    for a in self._attempts
                ],
                "last_updated": datetime.now(UTC).isoformat(),
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved adaptive success rate state")
        except Exception as e:
            logger.error(f"Failed to save adaptive success rate state: {e}")

    def record_attempt(
        self,
        phase: str,
        attempt_type: str,
        target_value: float,
        actual_value: float,
        outcome: OutcomeType,
        predicted_probability: float,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Record a new attempt and update learned probabilities.

        Returns the attempt ID.
        """
        attempt_id = f"{phase}_{attempt_type}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        # Get current learned probability
        learned_prob = self._probabilities.get_learned_probability(phase)

        # Create record
        record = AttemptRecord(
            id=attempt_id,
            phase=phase,
            attempt_type=attempt_type,
            timestamp=datetime.now(UTC),
            target_value=target_value,
            actual_value=actual_value,
            outcome=outcome,
            confidence_before=learned_prob,
            confidence_after=learned_prob,  # Will be updated
            metadata=metadata or {},
        )

        # Update learned probability using Bayesian updating
        self._update_learned_probability(phase, outcome, predicted_probability)

        # Store record
        self._attempts.append(record)
        self._save_state()

        logger.info(f"Recorded attempt {attempt_id}: {outcome.value} (phase: {phase})")
        return attempt_id

    def _update_learned_probability(
        self,
        phase: str,
        outcome: OutcomeType,
        predicted_probability: float,
    ) -> None:
        """Update learned probability using Bayesian updating — can reach 100% with sufficient evidence.

        Uses Beta distribution as conjugate prior for Bernoulli trials.
        Learning rate increases with data and can reach 100% with consistent success.
        """
        # Get current parameters
        learned_attr = f"{phase}_learned"
        confidence_attr = f"{phase}_confidence"
        baseline_attr = f"{phase}_baseline"

        current_learned = getattr(self._probabilities, learned_attr)
        current_confidence = getattr(self._probabilities, confidence_attr)
        baseline = getattr(self._probabilities, baseline_attr)

        # Get attempts for this phase
        phase_attempts = [a for a in self._attempts if a.phase == phase]
        n_attempts = len(phase_attempts)

        if n_attempts < 10:
            # Not enough data, keep baseline
            logger.debug(f"Not enough data for {phase} ({n_attempts} attempts), keeping baseline")
            return

        # Calculate actual success rate
        successes = sum(1 for a in phase_attempts if a.outcome == OutcomeType.SUCCESS)
        partials = sum(1 for a in phase_attempts if a.outcome == OutcomeType.PARTIAL)
        actual_rate = (successes + 0.5 * partials) / n_attempts

        # Bayesian update: weighted average of prior and observed
        # Learning rate increases with data (can reach 100% with sufficient evidence)
        learning_rate = min(n_attempts / 50, 1.0)  # Max 100% weight to observations (increased from 80%)
        updated_learned = baseline * (1 - learning_rate) + actual_rate * learning_rate

        # Update confidence (increases with more data, can reach 100%)
        updated_confidence = min(current_confidence + 0.05, 1.0)

        # Update probability
        setattr(self._probabilities, learned_attr, updated_learned)
        setattr(self._probabilities, confidence_attr, updated_confidence)

        logger.info(
            f"Updated {phase} probability: {current_learned:.2%} → {updated_learned:.2%} "
            f"(confidence: {current_confidence:.2%} → {updated_confidence:.2%}, learning_rate: {learning_rate:.2%})"
        )

    def get_current_probabilities(self) -> dict[str, Any]:
        """Get current success probabilities (baseline vs learned)."""
        return {
            "phase_1": {
                "baseline": self._probabilities.phase_1_baseline,
                "learned": self._probabilities.phase_1_learned,
                "confidence": self._probabilities.phase_1_confidence,
                "improvement": self._probabilities.phase_1_learned - self._probabilities.phase_1_baseline,
            },
            "phase_2": {
                "baseline": self._probabilities.phase_2_baseline,
                "learned": self._probabilities.phase_2_learned,
                "confidence": self._probabilities.phase_2_confidence,
                "improvement": self._probabilities.phase_2_learned - self._probabilities.phase_2_baseline,
            },
            "phase_3": {
                "baseline": self._probabilities.phase_3_baseline,
                "learned": self._probabilities.phase_3_learned,
                "confidence": self._probabilities.phase_3_confidence,
                "improvement": self._probabilities.phase_3_learned - self._probabilities.phase_3_baseline,
            },
            "phase_4": {
                "baseline": self._probabilities.phase_4_baseline,
                "learned": self._probabilities.phase_4_learned,
                "confidence": self._probabilities.phase_4_confidence,
                "improvement": self._probabilities.phase_4_learned - self._probabilities.phase_4_baseline,
            },
        }

    def get_improvement_trajectory(self) -> list[dict[str, Any]]:
        """Get trajectory of improvement over time."""
        trajectory = []

        # Group attempts by month
        attempts_by_month = {}
        for attempt in self._attempts:
            month_key = attempt.timestamp.strftime("%Y-%m")
            if month_key not in attempts_by_month:
                attempts_by_month[month_key] = []
            attempts_by_month[month_key].append(attempt)

        # Calculate improvement over time
        for month in sorted(attempts_by_month.keys()):
            month_attempts = attempts_by_month[month]
            phase_success_rates = {}

            for phase in ["phase_1", "phase_2", "phase_3", "phase_4"]:
                phase_attempts = [a for a in month_attempts if a.phase == phase]
                if phase_attempts:
                    successes = sum(1 for a in phase_attempts if a.outcome == OutcomeType.SUCCESS)
                    partials = sum(1 for a in phase_attempts if a.outcome == OutcomeType.PARTIAL)
                    rate = (successes + 0.5 * partials) / len(phase_attempts)
                    phase_success_rates[phase] = rate

            trajectory.append({
                "month": month,
                "success_rates": phase_success_rates,
                "total_attempts": len(month_attempts),
            })

        return trajectory

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics."""
        total_attempts = len(self._attempts)
        if total_attempts == 0:
            return {
                "total_attempts": 0,
                "success_rate": 0.0,
                "phase_breakdown": {},
            }

        overall_successes = sum(1 for a in self._attempts if a.outcome == OutcomeType.SUCCESS)
        overall_partials = sum(1 for a in self._attempts if a.outcome == OutcomeType.PARTIAL)
        overall_rate = (overall_successes + 0.5 * overall_partials) / total_attempts

        phase_breakdown = {}
        for phase in ["phase_1", "phase_2", "phase_3", "phase_4"]:
            phase_attempts = [a for a in self._attempts if a.phase == phase]
            if phase_attempts:
                successes = sum(1 for a in phase_attempts if a.outcome == OutcomeType.SUCCESS)
                partials = sum(1 for a in phase_attempts if a.outcome == OutcomeType.PARTIAL)
                rate = (successes + 0.5 * partials) / len(phase_attempts)
                phase_breakdown[phase] = {
                    "attempts": len(phase_attempts),
                    "successes": successes,
                    "partials": partials,
                    "rate": rate,
                }

        return {
            "total_attempts": total_attempts,
            "overall_success_rate": overall_rate,
            "phase_breakdown": phase_breakdown,
            "current_probabilities": self.get_current_probabilities(),
        }

    def get_adaptive_target(self, phase: str) -> dict[str, Any]:
        """Get adaptive target based on learned performance — can reach 100% with sufficient evidence."""
        learned_prob = self._probabilities.get_learned_probability(phase)
        confidence = self._probabilities.get_confidence(phase)
        baseline = self._probabilities.get_baseline_probability(phase)

        effective_prob = learned_prob if confidence >= 0.7 else baseline * 0.7 + learned_prob * 0.3

        return {
            "phase": phase,
            "baseline_probability": baseline,
            "learned_probability": learned_prob,
            "confidence": confidence,
            "effective_probability": effective_prob,
            "improvement": learned_prob - baseline,
            "using_learned": confidence >= 0.7,
            "can_reach_100_percent": confidence >= 0.95 and learned_prob >= 0.95,
        }


# Singleton instance
_global_system: AdaptiveSuccessRateSystem | None = None


def get_adaptive_success_rate_system() -> AdaptiveSuccessRateSystem:
    """Get or create the global adaptive success rate system."""
    global _global_system
    if _global_system is None:
        _global_system = AdaptiveSuccessRateSystem()
    return _global_system
