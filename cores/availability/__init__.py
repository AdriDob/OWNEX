"""Availability Intelligence Engine — GAP P0.

Engine that scores opportunities based on availability, acceptance probability,
and other factors for the unified execution pipeline.

Responsible for:
- Computing availability scores from agent/ecosystem signals
- Integrating with execution queue for priority ordering
- Providing confidence estimates for opportunity execution
"""

from __future__ import annotations

from typing import Any


class AvailabilityStatus:
    """Status of availability for opportunity execution."""

    HEALTHY = "healthy"  # All systems green, ready to execute
    DEGRADED = "degraded"  # Some systems limited, proceed with caution
    OFFLINE = "offline"  # Critical systems unavailable
    UNKNOWN = "unknown"  # Cannot determine status


class AvailabilityEngine:
    """Engine that computes availability scores for opportunity execution."""

    def __init__(
        self,
        min_score: float = 0.0,
        max_score: float = 1.0,
        healthy_threshold: float = 0.8,
        degraded_threshold: float = 0.5,
    ):
        self.min_score = min_score
        self.max_score = max_score
        self.healthy_threshold = healthy_threshold
        self.degraded_threshold = degraded_threshold

    def compute_score(
        self,
        agent_status: str = "unknown",
        system_load: float = 0.5,
        resource_availability: float = 1.0,
        concurrent_executions: int = 0,
        **kwargs: Any,
    ) -> float:
        """Compute availability score in [0, 1] range.

        Higher score = more available to execute opportunities.

        Args:
            agent_status: Status of primary agent (healthy, degraded, offline, unknown)
            system_load: System load percentage (0.0 = idle, 1.0 = overloaded)
            resource_availability: Resource availability (0.0 = none, 1.0 = full)
            concurrent_executions: Number of concurrent executions currently running
            **kwargs: Additional factors

        Returns:
            Score in [0, 1] range
        """
        # Base score from system resources
        resource_score = resource_availability * (1.0 - system_load)

        # Agent availability factor
        agent_factor = self._agent_status_factor(agent_status)

        # Concurrent execution penalty (diminishing returns)
        concurrency_penalty = min(concurrent_executions * 0.1, 0.3)

        # Final score
        score = resource_score * agent_factor * (1.0 - concurrency_penalty)

        # Clamp to [0, 1]
        return max(self.min_score, min(self.max_score, score))

    def _agent_status_factor(self, status: str) -> float:
        """Convert agent status to numeric factor."""
        factors = {
            "healthy": 1.0,
            "degraded": 0.7,
            "offline": 0.0,
            "unknown": 0.5,
        }
        return factors.get(status.lower(), 0.5)

    def get_status(self, score: float) -> str:
        """Convert numeric score to status string."""
        if score >= self.healthy_threshold:
            return AvailabilityStatus.HEALTHY
        elif score >= self.degraded_threshold:
            return AvailabilityStatus.DEGRADED
        else:
            return AvailabilityStatus.OFFLINE

    def evaluate(
        self,
        agent_status: str = "unknown",
        system_load: float = 0.5,
        resource_availability: float = 1.0,
        concurrent_executions: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Full evaluation returning score and status."""
        score = self.compute_score(
            agent_status=agent_status,
            system_load=system_load,
            resource_availability=resource_availability,
            concurrent_executions=concurrent_executions,
            **kwargs,
        )
        return {
            "score": round(score, 4),
            "status": self.get_status(score),
            "agent_status": agent_status,
            "system_load": system_load,
            "resource_availability": resource_availability,
            "concurrent_executions": concurrent_executions,
        }


# Singleton instance for easy import
availability_engine = AvailabilityEngine()


# Convenience functions
def compute_availability_score(**kwargs) -> float:
    """Quick compute availability score."""
    return availability_engine.compute_score(**kwargs)


def evaluate_availability(**kwargs) -> dict[str, Any]:
    """Quick evaluate availability."""
    return availability_engine.evaluate(**kwargs)


def is_available(**kwargs) -> bool:
    """Check if system is available for opportunity execution."""
    result = evaluate_availability(**kwargs)
    return result["status"] == AvailabilityStatus.HEALTHY
