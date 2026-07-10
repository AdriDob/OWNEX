from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cores.validation.replayer import ComparisonResult
from cores.validation.rules import ValidationReport

logger = logging.getLogger("catseye.validation.confidence")

DEFAULT_WEIGHTS: dict[str, float] = {
    "consistency": 0.40,
    "signal": 0.30,
    "evidence_strength": 0.20,
    "noise_penalty": -0.10,
}

STATE_FILE = Path.home() / ".orion" / "confidence_state.json"


@dataclass
class ConfidenceScore:
    score: float
    breakdown: dict[str, float]
    level: str


class ConfidenceScorer:
    def __init__(self) -> None:
        self._weights: dict[str, float] = dict(DEFAULT_WEIGHTS)
        self._llm_bias: float = 0.0

    # ── Weight management ─────────────────────────────────────────

    def adjust_weights(self, adjustments: dict[str, float]) -> None:
        """Apply dynamic weight adjustments from FeedbackLearner.

        values are added to current weights, then normalized so
        positive weights sum to 1.0 and negative weights stay negative.
        """
        for key, adj in adjustments.items():
            if key in self._weights:
                self._weights[key] = round(self._weights[key] + adj, 4)
        positive_keys = [k for k, v in self._weights.items() if v > 0]
        pos_sum = sum(self._weights[k] for k in positive_keys)
        if pos_sum > 0:
            for k in positive_keys:
                self._weights[k] = round(self._weights[k] / pos_sum, 4)

    def get_weights(self) -> dict[str, float]:
        return dict(self._weights)

    # ── LLM bias management ───────────────────────────────────────

    def adjust_bias(self, delta: float) -> None:
        """Adjust the persistent LLM-learned bias."""
        self._llm_bias = round(self._llm_bias + delta, 4)

    def set_bias(self, value: float) -> None:
        """Set the persistent LLM-learned bias directly."""
        self._llm_bias = round(value, 4)

    def get_bias(self) -> float:
        return self._llm_bias

    # ── Scoring ───────────────────────────────────────────────────

    def calculate(
        self,
        results: list[ComparisonResult],
        validation: ValidationReport,
        endpoint_signals: dict[str, Any],
        llm_boost: float = 0.0,
        uncertainty_penalty: float = 0.0,
    ) -> ConfidenceScore:
        total = len(results)
        if total == 0:
            return ConfidenceScore(
                score=0.0,
                breakdown={
                    "consistency_score": 0.0,
                    "signal_score": 0.0,
                    "evidence_strength": 0.0,
                    "noise_penalty": 0.0,
                    "uncertainty_penalty": uncertainty_penalty,
                },
                level="none",
            )

        consistent_count = sum(1 for r in results if r.consistent)
        consistency_score = consistent_count / total

        risk_score = float(endpoint_signals.get("risk_score", 0))
        signal_score = min(risk_score / 100.0, 1.0)

        total_rules = 4
        passed_rules = len(validation.passed_rules)
        evidence_strength = passed_rules / total_rules

        noise_count = sum(1 for r in results if r.has_rate_limit or r.has_timeout)
        noise_penalty = noise_count / total

        raw_score = (
            (consistency_score * self._weights["consistency"])
            + (signal_score * self._weights["signal"])
            + (evidence_strength * self._weights["evidence_strength"])
            + (noise_penalty * self._weights["noise_penalty"])
            + llm_boost
            + self._llm_bias
            - uncertainty_penalty
        )
        score = max(0.0, min(1.0, round(raw_score, 4)))

        if score >= 0.8:
            level = "high"
        elif score >= 0.6:
            level = "medium"
        elif score >= 0.3:
            level = "low"
        else:
            level = "none"

        return ConfidenceScore(
            score=score,
            breakdown={
                "consistency_score": round(consistency_score, 4),
                "signal_score": round(signal_score, 4),
                "evidence_strength": round(evidence_strength, 4),
                "noise_penalty": round(noise_penalty, 4),
                "uncertainty_penalty": round(uncertainty_penalty, 4),
            },
            level=level,
        )

    # ── Persistence ────────────────────────────────────────────────

    def save_state(self) -> None:
        """Persist weights and bias so they survive restart."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "weights": self._weights,
                "llm_bias": self._llm_bias,
            }
            with open(STATE_FILE, "w") as f:
                json.dump(data, f)
        except Exception as exc:
            logger.warning("Failed to save confidence state: %s", exc)

    def load_state(self) -> None:
        """Restore persisted weights and bias."""
        if not STATE_FILE.exists():
            return
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            saved_weights = data.get("weights", {})
            for key, value in saved_weights.items():
                if key in self._weights:
                    self._weights[key] = value
            self._llm_bias = data.get("llm_bias", 0.0)
            logger.info("Confidence state restored: weights=%s, bias=%s", self._weights, self._llm_bias)
        except Exception as exc:
            logger.warning("Failed to load confidence state: %s", exc)


# ── Shared singleton ──────────────────────────────────────────────
# All consumers (FeedbackTuner, ValidationLoopEngine) share the same
# ConfidenceScorer instance so weight adjustments propagate to live scoring.

_scorer_instance: ConfidenceScorer | None = None


def get_confidence_scorer() -> ConfidenceScorer:
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = ConfidenceScorer()
        _scorer_instance.load_state()
    return _scorer_instance
