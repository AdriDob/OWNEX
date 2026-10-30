"""A minimal, deterministic EvaluationEngine for tests and local runs.

Returns conservative evaluation results based on work_item attributes.
"""

from __future__ import annotations

from typing import Any


class SimpleEvaluationEngine:
    def evaluate(self, work_item: Any, profile: Any = None) -> dict[str, Any]:
        """Evaluate a WorkItem and return a result dict.

        Logic:
        - expected_value_usd_per_hour: use work_item.expected_value_usd_per_hour if present,
          otherwise compute reward / max(hours,1)
        - acceptance_probability: use existing or default 0.5
        - risk_score: use existing or default 0.3
        - quality_gate_result: pass if risk_score <= 0.8 and expected_value_usd_per_hour > 0
        """
        ev = getattr(work_item, "expected_value_usd_per_hour", None)
        if not ev:
            hours = getattr(work_item, "estimated_hours", 1.0) or 1.0
            reward = getattr(work_item, "estimated_reward_usd", 0.0) or 0.0
            ev = reward / max(hours, 1.0)

        acceptance = getattr(work_item, "acceptance_probability", None) or 0.5
        risk = getattr(work_item, "risk_score", None) or 0.3

        quality_pass = (risk <= 0.8) and (ev > 0)

        return {
            "passed": quality_pass,
            "score": float(ev) * 10.0,
            "barrier_score": 100.0 - (risk * 100.0),
            "expected_value_usd_per_hour": float(ev),
            "acceptance_probability": float(acceptance),
            "risk_score": float(risk),
            "quality_gate_result": {"passed": quality_pass, "reason": None if quality_pass else "low_ev_or_high_risk"},
        }
