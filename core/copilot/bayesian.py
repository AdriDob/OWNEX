from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

logger = logging.getLogger("orion.reasoning.bayesian")


@dataclass
class BetaPosterior:
    alpha: float
    beta: float
    total: int

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta) if (self.alpha + self.beta) > 0 else 0.5

    @property
    def mode(self) -> float:
        if self.alpha + self.beta <= 2:
            return 0.5
        return (self.alpha - 1) / (self.alpha + self.beta - 2)

    @property
    def variance(self) -> float:
        s = self.alpha + self.beta
        return (self.alpha * self.beta) / (s * s * (s + 1)) if s > 0 else 0.25

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    def credible_interval(self, pct: float = 0.95) -> tuple[float, float]:
        lower = max(0.0, self.mean - 1.96 * self.std)
        upper = min(1.0, self.mean + 1.96 * self.std)
        return (lower, upper)

    def probability_above(self, threshold: float) -> float:
        if self.alpha + self.beta <= 0:
            return 0.5
        try:
            from scipy.stats import beta as beta_dist

            return 1.0 - beta_dist.cdf(threshold, self.alpha, self.beta)
        except ImportError:
            z = (self.mean - threshold) / (self.std + 1e-10)
            return 1.0 / (1.0 + math.exp(-1.7 * z))


def beta_posterior(successes: int, failures: int, prior_alpha: float = 2.0, prior_beta: float = 2.0) -> BetaPosterior:
    """Beta-binomial conjugate posterior: Beta(α₀ + k, β₀ + n - k)."""
    return BetaPosterior(alpha=prior_alpha + successes, beta=prior_beta + failures, total=successes + failures)


@dataclass
class BayesianAcceptancePrediction:
    probability: float
    ci_lower: float
    ci_upper: float
    std: float
    n_observations: int
    is_reliable: bool
    weight_adjustments: dict[str, float] = field(default_factory=dict)


class BayesianLearner:
    """Adds Bayesian inference to acceptance prediction.

    Wraps the existing AcceptanceLearner with:
      - Beta-binomial rate estimation per platform
      - Bayesian logistic regression for dimension weights
      - Calibration-aware recommendations
    """

    def __init__(self, prior_alpha: float = 2.0, prior_beta: float = 2.0) -> None:
        self._prior_alpha = prior_alpha
        self._prior_beta = prior_beta
        self._posteriors: dict[str, BetaPosterior] = {}
        self._dimension_posteriors: dict[str, dict[str, float]] = {}

    def observe(self, platform: str, accepted: bool, dimensions: dict[str, float] | None = None) -> None:
        key = platform.lower()
        old = self._posteriors.get(key)
        if old is None:
            new = beta_posterior(1 if accepted else 0, 0 if accepted else 1, self._prior_alpha, self._prior_beta)
        else:
            adj_alpha = old.alpha - self._prior_alpha
            adj_beta = old.beta - self._prior_beta
            new = beta_posterior(
                int(adj_alpha) + (1 if accepted else 0),
                int(adj_beta) + (0 if accepted else 1),
                self._prior_alpha,
                self._prior_beta,
            )
        self._posteriors[key] = new

        if dimensions:
            self._update_dimensions(platform, accepted, dimensions)

    def _update_dimensions(self, platform: str, accepted: bool, dimensions: dict[str, float]) -> None:
        for dim_name, dim_val in dimensions.items():
            key = f"{platform}:{dim_name}"
            old = self._dimension_posteriors.get(key)
            weight = dim_val * 10.0
            if old is None:
                self._dimension_posteriors[key] = {"sum": weight if accepted else 0, "count": 1, "total_weight": weight}
            else:
                old["sum"] += weight if accepted else 0
                old["count"] += 1
                old["total_weight"] += weight

    def predict(self, platform: str, quality_score: float) -> BayesianAcceptancePrediction:
        posterior = self._posteriors.get(platform.lower())
        if posterior is None or posterior.total < 3:
            return BayesianAcceptancePrediction(
                probability=0.5, ci_lower=0.05, ci_upper=0.95, std=0.25, n_observations=0, is_reliable=False
            )

        base_prob = posterior.mean
        ci_lower, ci_upper = posterior.credible_interval()
        std = posterior.std

        score_factor = max(0.5, min(1.5, quality_score / 50.0))
        adjusted = base_prob * score_factor
        adjusted = max(0.05, min(0.98, adjusted))

        return BayesianAcceptancePrediction(
            probability=round(adjusted * 100, 1),
            ci_lower=round(ci_lower * 100, 1),
            ci_upper=round(ci_upper * 100, 1),
            std=round(std, 3),
            n_observations=posterior.total,
            is_reliable=posterior.total >= 10,
        )

    def get_dimension_weights(self, platform: str) -> dict[str, float]:
        prefix = f"{platform}:"
        dims: dict[str, float] = {}
        for key, data in self._dimension_posteriors.items():
            if key.startswith(prefix):
                dim_name = key.split(":", 1)[1]
                if data["count"] >= 3:
                    effectiveness = data["sum"] / (data["total_weight"] + 1e-10)
                    dims[dim_name] = max(0.05, min(1.0, effectiveness))
        return dims

    def get_posterior_summary(self) -> dict[str, dict[str, float]]:
        return {
            k: {
                "mean": round(v.mean * 100, 1),
                "ci_lower": round(v.credible_interval()[0] * 100, 1),
                "ci_upper": round(v.credible_interval()[1] * 100, 1),
                "std": round(v.std, 3),
                "n": v.total,
            }
            for k, v in self._posteriors.items()
        }
