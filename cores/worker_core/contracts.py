"""WorkerCore Contracts — Protocol definitions for engine interfaces.

Defines typed protocols for all engines that WorkerCore integrates with.
These are structural subtyping contracts (PEP 544) — any class that implements
the required methods satisfies the protocol without explicit inheritance.

Usage:
    from cores.worker_core.contracts import DiscoveryEngineProtocol

    class MyDiscovery:
        async def discover_all(self, categories=None, platforms=None):
            return [...]

    # MyDiscovery satisfies DiscoveryEngineProtocol automatically
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

# ── Discovery ────────────────────────────────────────────────────────────────


@runtime_checkable
class DiscoveryEngineProtocol(Protocol):
    """Protocol for discovery engines that find work opportunities."""

    async def discover_all(
        self,
        categories: list[Any] | None = None,
        platforms: list[Any] | None = None,
    ) -> list[Any]:
        """Discover opportunities from all registered adapters.

        Args:
            categories: Optional filter by category
            platforms: Optional filter by platform

        Returns:
            List of Opportunity objects
        """
        ...


# ── Evaluation ───────────────────────────────────────────────────────────────


@runtime_checkable
class EvaluationEngineProtocol(Protocol):
    """Protocol for evaluation engines that score and filter work items."""

    def evaluate(self, work_item: Any, profile: Any = None) -> dict[str, Any]:
        """Evaluate a work item and return evaluation result.

        Args:
            work_item: Work item with opportunity attributes
            profile: Optional user profile

        Returns:
            Dict with keys: passed, score, reasons, barrier_score,
            expected_value_usd_per_hour, acceptance_probability,
            quality_gate_result, etc.
        """
        ...


# ── Execution ────────────────────────────────────────────────────────────────


@runtime_checkable
class ExecutionEngineProtocol(Protocol):
    """Protocol for execution engines that perform work."""

    def execute(self, work_item: Any, profile: Any = None) -> dict[str, Any]:
        """Execute a work item using the appropriate executor.

        Args:
            work_item: Work item to execute
            profile: Optional user profile

        Returns:
            Dict with keys: success, artifacts, evidence, output,
            error, execution_time_s
        """
        ...


# ── Delivery ─────────────────────────────────────────────────────────────────


@runtime_checkable
class DeliveryEngineProtocol(Protocol):
    """Protocol for delivery engines that submit completed work."""

    def deliver(self, work_item: Any, approved_by_human: bool = True) -> dict[str, Any]:
        """Deliver a completed work item.

        Args:
            work_item: Completed work item to deliver
            approved_by_human: Whether human has approved the delivery

        Returns:
            Dict with keys: success, submission_id, submission_url,
            platform_response, error
        """
        ...


# ── Learning ─────────────────────────────────────────────────────────────────


@runtime_checkable
class LearningEngineProtocol(Protocol):
    """Protocol for learning engines that improve from outcomes."""

    def learn(
        self,
        work_item: Any,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Learn from a completed work item outcome.

        Args:
            work_item: Completed work item
            outcome: Outcome status (completed, failed, accepted, paid, etc.)
            details: Optional additional outcome details

        Returns:
            Dict with keys: success, lessons, skill_updates,
            platform_updates, category_updates, error
        """
        ...


# ── Skill Analysis ───────────────────────────────────────────────────────────


@runtime_checkable
class SkillEngineProtocol(Protocol):
    """Protocol for skill engines that analyze gaps and readiness."""

    def analyze(self, work_item: Any, profile: Any) -> Any:
        """Analyze skill gaps for a work item against user profile.

        Args:
            work_item: WorkItem with opportunity info
            profile: User's current profile

        Returns:
            SkillAnalysisResult with gap report, readiness, can_execute
        """
        ...


# ── Cost Tracker ─────────────────────────────────────────────────────────────


@runtime_checkable
class CostTrackerProtocol(Protocol):
    """Protocol for cost tracking across AI operations."""

    def get_daily_spent(self) -> float:
        """Get total USD spent today."""
        ...

    def record_usage(
        self,
        provider_id: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float = 0.0,
    ) -> None:
        """Record usage for a provider/model."""
        ...


# ── AI Router ────────────────────────────────────────────────────────────────


@runtime_checkable
class AIRouterProtocol(Protocol):
    """Protocol for AI routers that select providers."""

    async def route(self, context: Any) -> Any:
        """Route a request to the best available provider.

        Args:
            context: RoutingContext with messages, task_type, constraints

        Returns:
            RoutingDecision with provider_id, model_id, estimated_cost
        """
        ...
