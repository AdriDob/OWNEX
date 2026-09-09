"""Base reasoner — interface for all offensive reasoners with feedback mechanism."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from core.offensive.models import EndpointInfo, Hypothesis

logger = logging.getLogger("orion.core.offensive.reasoners.base")


class BaseReasoner(ABC):
    """A reasoner analyzes an endpoint and generates hypotheses.

    Each reasoner specializes in one vulnerability type (IDOR, SSRF, etc.)
    and implements its own signal detection and confidence calculation.

    Feedback mechanism: record_outcome() adjusts internal weights based on
    whether a hypothesis was confirmed or rejected, enabling the reasoner
    to learn from real outcomes.
    """

    def __init__(self) -> None:
        self._outcome_history: list[dict[str, Any]] = []
        self._confidence_multiplier: float = 1.0

    @property
    @abstractmethod
    def vulnerability_type(self) -> str:
        """e.g. 'idor', 'ssrf', 'api_abuse'"""

    @abstractmethod
    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        """Analyze an endpoint and return zero or more hypotheses."""

    @abstractmethod
    def supported_methods(self) -> list[str]:
        """HTTP methods this reasoner can analyze (e.g. ['GET', 'POST', 'PUT', 'DELETE'])."""

    # ── Feedback mechanism ─────────────────────────────────────────

    def record_outcome(self, hypothesis_id: str, was_confirmed: bool, metadata: dict[str, Any] | None = None) -> None:
        """Record whether a hypothesis from this reasoner was confirmed or rejected.

        Adjusts confidence multiplier based on accuracy:
        - Confirmed: slightly increase multiplier (reasoner is reliable)
        - Rejected: decrease multiplier (reasoner is overconfident)
        """
        delta = 0.05 if was_confirmed else -0.03
        self._confidence_multiplier = max(0.5, min(2.0, self._confidence_multiplier + delta))

        record = {
            "hypothesis_id": hypothesis_id,
            "vulnerability_type": self.vulnerability_type,
            "was_confirmed": was_confirmed,
            "old_multiplier": round(self._confidence_multiplier - delta, 4),
            "new_multiplier": round(self._confidence_multiplier, 4),
            "metadata": metadata or {},
        }
        self._outcome_history.append(record)
        logger.info(
            "[%s] Outcome recorded: %s=%s → multiplier=%.2f",
            self.vulnerability_type.upper(),
            hypothesis_id,
            "confirmed" if was_confirmed else "rejected",
            self._confidence_multiplier,
        )

    def get_outcome_stats(self) -> dict[str, Any]:
        """Return summary statistics about outcomes."""
        if not self._outcome_history:
            return {
                "total": 0,
                "confirmed": 0,
                "rejected": 0,
                "accuracy": 0.0,
                "multiplier": self._confidence_multiplier,
            }
        total = len(self._outcome_history)
        confirmed = sum(1 for r in self._outcome_history if r["was_confirmed"])
        return {
            "total": total,
            "confirmed": confirmed,
            "rejected": total - confirmed,
            "accuracy": round(confirmed / total, 3) if total > 0 else 0.0,
            "multiplier": round(self._confidence_multiplier, 4),
        }

    def apply_confidence_multiplier(self, base_confidence: float) -> float:
        """Apply the learned confidence multiplier to a raw confidence score."""
        return min(1.0, base_confidence * self._confidence_multiplier)
