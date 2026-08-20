"""Difficulty frontier for the self-improvement loop.

The frontier tracks observed success probability per difficulty band and
selects the difficulty whose estimated success rate is closest to p_target
(Ornith-style curriculum): too easy tasks are dropped, too hard tasks are
deferred until the system's capability improves.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from core.self_improvement.config import SelfImprovementConfig


@dataclass
class FrontierBand:
    """Aggregated success statistics for a difficulty band."""

    low: float  # inclusive
    high: float  # exclusive
    attempts: int = 0
    successes: int = 0

    @property
    def success_rate(self) -> float:
        return self.successes / self.attempts if self.attempts else 0.5

    def record(self, success: bool) -> None:
        self.attempts += 1
        if success:
            self.successes += 1


class DifficultyFrontier:
    """Selects the next difficulty to sample using a gaussian around p_target.

    Each cycle, the difficulty moves by a small step toward the band whose
    observed success rate deviates most from p_target, mirroring how a human
    teacher raises the bar when the student starts succeeding.
    """

    def __init__(self, config: SelfImprovementConfig) -> None:
        self.config = config
        self.difficulty = 0.3  # start conservative
        self._bands: dict[int, FrontierBand] = {}
        self._band_width = 0.1

    def _band_index(self, difficulty: float) -> int:
        return int(difficulty / self._band_width)

    def band(self, difficulty: float) -> FrontierBand:
        idx = self._band_index(difficulty)
        return self._bands.setdefault(idx, FrontierBand(idx * self._band_width, (idx + 1) * self._band_width))

    def record_outcome(self, difficulty: float, success: bool) -> None:
        """Record an outcome and update the current difficulty towards p_target."""
        self.band(difficulty).record(success)
        observed = self.band(difficulty).success_rate
        # If observed rate is above target, we can make tasks harder; below => easier.
        delta = (observed - self.config.p_target) * self.config.difficulty_step
        self.difficulty = min(1.0, max(0.0, self.difficulty + delta))

    def current_difficulty(self) -> float:
        """Return the difficulty to use for the next generated task."""
        return round(self.difficulty, 4)

    def gaussian_score(self, difficulty: float) -> float:
        """Gaussian bump centered on p_target used as a sampling weight.

        Returns a weight in (0, 1]; difficulty 0.0 maps to 0, 1.0 to 0, and the
        peak (1.0) sits at the current difficulty position (not p_target), so
        the sampler favors difficulties near where the system currently is.
        """
        sigma = self.config.frontier_sigma
        d = (difficulty - self.difficulty) / max(sigma, 1e-9)
        return math.exp(-(d * d) / 2.0)

    def to_dict(self) -> dict[str, object]:
        return {
            "difficulty": self.difficulty,
            "p_target": self.config.p_target,
            "band_width": self._band_width,
            "bands": {
                str(idx): {
                    "low": b.low,
                    "high": b.high,
                    "attempts": b.attempts,
                    "successes": b.successes,
                    "success_rate": round(b.success_rate, 4),
                }
                for idx, b in sorted(self._bands.items())
            },
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        self.difficulty = float(data.get("difficulty", 0.3))
        for key, raw in (data.get("bands") or {}).items():
            b = FrontierBand(low=float(raw["low"]), high=float(raw["high"]))
            b.attempts = int(raw.get("attempts", 0))
            b.successes = int(raw.get("successes", 0))
            self._bands[int(key)] = b
