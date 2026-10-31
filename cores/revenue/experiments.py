"""Revenue Experiments Framework — A/B testing for KEEP/DROP/SCALE decisions.

Provides structured experimentation around revenue optimization decisions,
including hypothesis formation, experiment design, result analysis, and
learning propagation across the system.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, NamedTuple

logger = logging.getLogger("ownex.revenue.experiments")

# ── Experiment Types ────────────────────────────────────────────────────────

EXPERIMENT_TYPE_KEEP = "keep"
EXPERIMENT_TYPE_DROP = "drop"
EXPERIMENT_TYPE_SCALE = "scale"

# ── Experiment State ───────────────────────────────────────────────────────


class ExperimentStatus(NamedTuple):
    """Status of an experiment."""

    PENDING: str = "pending"
    RUNNING: str = "running"
    COMPLETED: str = "completed"
    CANCELLED: str = "cancelled"
    FAILED: str = "failed"


class ExperimentResult(NamedTuple):
    """Result of an experiment."""

    success: bool
    revenue_impact: float  # estimated impact in USD
    confidence: float  # 0.0 to 1.0
    p_value: float | None = None
    sample_size: int = 0


# ── Experiment Design ─────────────────────────────────────────────────────


class ExperimentDesign(NamedTuple):
    """Design of a revenue experiment."""

    experiment_id: str
    name: str
    description: str
    experiment_type: str  # keep/drop/scale
    hypothesis: str
    treatment_groups: dict[str, Any]  # group_name -> configuration
    success_metrics: list[str]  # metrics to track
    minimum_detectable_effect: float  # minimum USD impact to detect
    duration_days: int
    created_at: str
    status: str = ExperimentStatus.PENDING


# ── Experiment Registry ───────────────────────────────────────────────────


class ExperimentsRegistry:
    """Registry for managing revenue experiments."""

    def __init__(self):
        self._experiments: dict[str, ExperimentDesign] = {}
        self._results: dict[str, ExperimentResult] = {}
        self._run_count = 0

    def create_experiment(
        self,
        name: str,
        description: str,
        experiment_type: str,
        hypothesis: str,
        treatment_groups: dict[str, Any],
        success_metrics: list[str],
        minimum_detectable_effect: float,
        duration_days: int,
    ) -> str:
        """Create a new experiment and return its ID."""
        experiment_id = f"exp_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{self._run_count}"
        self._run_count += 1

        design = ExperimentDesign(
            experiment_id=experiment_id,
            name=name,
            description=description,
            experiment_type=experiment_type,
            hypothesis=hypothesis,
            treatment_groups=treatment_groups,
            success_metrics=success_metrics,
            minimum_detectable_effect=minimum_detectable_effect,
            duration_days=duration_days,
            created_at=datetime.now(UTC).isoformat(),
            status=ExperimentStatus.PENDING,
        )

        self._experiments[experiment_id] = design
        logger.info(f"Experiment created: {experiment_id} - {name}")
        return experiment_id

    def get_experiment(self, experiment_id: str) -> ExperimentDesign | None:
        """Get experiment design by ID."""
        return self._experiments.get(experiment_id)

    def update_result(
        self,
        experiment_id: str,
        success: bool,
        revenue_impact: float,
        confidence: float,
        p_value: float | None = None,
        sample_size: int = 0,
    ) -> None:
        """Update experiment result."""
        result = ExperimentResult(
            success=success,
            revenue_impact=revenue_impact,
            confidence=confidence,
            p_value=p_value,
            sample_size=sample_size,
        )
        self._results[experiment_id] = result
        # Update experiment status
        if experiment_id in self._experiments:
            design = self._experiments[experiment_id]
            design = _replace(design, status=ExperimentStatus.COMPLETED)
            self._experiments[experiment_id] = design
        logger.info(f"Experiment result updated: {experiment_id}")

    def get_experiment_result(self, experiment_id: str) -> ExperimentResult | None:
        """Get experiment result by ID."""
        return self._results.get(experiment_id)

    def list_experiments(self) -> list[dict[str, Any]]:
        """List all experiments with summary info."""
        results: list[dict[str, Any]] = []
        for exp_id, design in self._experiments.items():
            result = self._results.get(exp_id)
            results.append(
                {
                    "experiment_id": exp_id,
                    "name": design.name,
                    "type": design.experiment_type,
                    "status": design.status,
                    "created_at": design.created_at,
                    "revenue_impact": result.revenue_impact if result else 0.0,
                    "success": result.success if result else False,
                }
            )
        return results

    def get_active_experiments(self) -> list[dict[str, Any]]:
        """List experiments currently running."""
        active: list[dict[str, Any]] = []
        for exp_id, design in self._experiments.items():
            if design.status == "running":
                active.append(
                    {
                        "experiment_id": exp_id,
                        "name": design.name,
                        "type": design.experiment_type,
                        "duration_days": design.duration_days,
                        "created_at": design.created_at,
                    }
                )
        return active


def _replace(obj, **changes):
    """Helper to create a new namedtuple with changed fields."""
    # Create a mutable dict from the namedtuple
    d = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    d.update(changes)
    # Create new namedtuple type
    T = type(type(obj))
    return T(**d)


# ── Statistical Analysis ───────────────────────────────────────────────────


def _compute_pearson_r(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation coefficient."""
    n = len(x)
    if n < 2 or len(y) != n:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denominator = (sum((xi - mean_x) ** 2 for xi in x) * sum((yi - mean_y) ** 2 for yi in y)) ** 0.5

    if denominator == 0:
        return 0.0

    return numerator / denominator


def _compute_conversion_rate(results: dict[str, Any]) -> dict[str, float]:
    """Compute conversion rates from experiment results."""
    conversions: dict[str, float] = {}
    for group, data in results.items():
        conversions[group] = data.get("conversions", 0) / max(data.get("total", 1), 1)
    return conversions


def _compute_average_revenue(results: dict[str, Any]) -> dict[str, float]:
    """Compute average revenue per group."""
    avg_rev: dict[str, float] = {}
    for group, data in results.items():
        avg_rev[group] = data.get("total_revenue", 0) / max(data.get("total", 1), 1)
    return avg_rev


# ── Convenience Functions ─────────────────────────────────────────────────


def run_keep_experiment(
    experiment_id: str,
    platform: str,
    duration_days: int = 30,
    minimum_detectable_effect: float = 100.0,
) -> dict[str, Any]:
    """Run a KEEP experiment for a platform.

    Tests whether keeping the current allocation strategy
    generates the expected revenue impact.
    """
    # Placeholder - in production would analyze real revenue data
    return {
        "experiment_id": experiment_id,
        "platform": platform,
        "type": "keep",
        "duration_days": duration_days,
        "revenue_impact_estimate": 0.0,
        "confidence": 0.5,
        "recommendation": "INCONCLUSIVE",
    }


def run_drop_experiment(
    experiment_id: str,
    platform: str,
    duration_days: int = 30,
    minimum_detectable_effect: float = 100.0,
) -> dict[str, Any]:
    """Run a DROP experiment for a platform.

    Tests whether dropping/phasing out a platform
    would have positive or negative revenue impact.
    """
    # Placeholder - in production would analyze real revenue data
    return {
        "experiment_id": experiment_id,
        "platform": platform,
        "type": "drop",
        "duration_days": duration_days,
        "revenue_impact_estimate": 0.0,
        "confidence": 0.5,
        "recommendation": "INCONCLUSIVE",
    }


def run_scale_experiment(
    experiment_id: str,
    platform: str,
    duration_days: int = 30,
    minimum_detectable_effect: float = 100.0,
) -> dict[str, Any]:
    """Run a SCALE experiment for a platform.

    Tests whether scaling up the current allocation
    would generate positive revenue impact.
    """
    # Placeholder - in production would analyze real revenue data
    return {
        "experiment_id": experiment_id,
        "platform": platform,
        "type": "scale",
        "duration_days": duration_days,
        "revenue_impact_estimate": 0.0,
        "confidence": 0.5,
        "recommendation": "INCONCLUSIVE",
    }


# ── Singleton instance ────────────────────────────────────────────────────

_experiments_registry: ExperimentsRegistry | None = None


def get_experiments_registry() -> ExperimentsRegistry:
    """Get the singleton experiments registry."""
    global _experiments_registry
    if _experiments_registry is None:
        _experiments_registry = ExperimentsRegistry()
    return _experiments_registry


# ── Public API ─────────────────────────────────────────────────────────────

__all__ = [
    "ExperimentsRegistry",
    "ExperimentDesign",
    "ExperimentStatus",
    "ExperimentResult",
    "get_experiments_registry",
    "run_keep_experiment",
    "run_drop_experiment",
    "run_scale_experiment",
    "EXPERIMENT_TYPE_KEEP",
    "EXPERIMENT_TYPE_DROP",
    "EXPERIMENT_TYPE_SCALE",
    "minimum_detectable_effect",
]
