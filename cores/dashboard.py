"""Control Dashboard — real-time status, opportunities, agents, revenue.

Provides the central command view for OWNEX operations.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cores.events.event_bus import get_core_event_bus

logger = logging.getLogger("ownex.dashboard")


@dataclass
class SystemStatus:
    """Overall system health status."""

    healthy: bool
    components: dict[str, dict[str, Any]]
    issues: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class DashboardMetrics:
    """Key metrics for the dashboard."""

    # Sensors
    active_sensors: int = 0
    total_observations: int = 0
    observations_last_hour: int = 0

    # Opportunities
    total_opportunities: int = 0
    new_opportunities_24h: int = 0
    high_value_opportunities: int = 0
    opportunities_by_category: dict[str, int] = field(default_factory=dict)

    # Agents
    active_agents: int = 0
    agents_by_type: dict[str, int] = field(default_factory=dict)
    tasks_in_progress: int = 0
    tasks_completed_today: int = 0
    tasks_failed_today: int = 0

    # Revenue
    total_revenue: float = 0.0
    revenue_today: float = 0.0
    revenue_this_month: float = 0.0
    pending_payouts: float = 0.0
    revenue_by_platform: dict[str, float] = field(default_factory=dict)
    revenue_by_category: dict[str, float] = field(default_factory=dict)

    # Learning
    total_learnings: int = 0
    learnings_this_week: int = 0
    patterns_discovered: int = 0

    # System
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    disk_usage_percent: float = 0.0

    # Autonomy
    autonomy_level: str = "OBSERVER"
    pending_approvals: int = 0

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class DashboardAggregator:
    """Aggregates metrics from all system components for the dashboard."""

    def __init__(self):
        self.event_bus = get_core_event_bus()
        self._metrics = DashboardMetrics()
        self._start_time = time.time()
        self._component_health: dict[str, dict[str, Any]] = {}
        self._last_update = datetime.now(UTC)

        # Register for events
        self._register_event_handlers()

    def _register_event_handlers(self) -> None:
        """Register event handlers for real-time updates."""
        handlers = {
            "sensor:observation": self._on_observation,
            "opportunity:discovered": self._on_opportunity,
            "opportunity:scored": self._on_opportunity_scored,
            "agent:task_started": self._on_task_started,
            "agent:task_completed": self._on_task_completed,
            "agent:task_failed": self._on_task_failed,
            "revenue:recorded": self._on_revenue,
            "learning:recorded": self._on_learning,
            "autonomy:level_changed": self._on_autonomy_change,
            "approval:requested": self._on_approval_requested,
            "approval:decided": self._on_approval_decided,
            "component:health": self._on_component_health,
        }

        for event, handler in handlers.items():
            self.event_bus.subscribe(event, handler)

    def _on_observation(self, event) -> None:
        self._metrics.total_observations += 1
        self._metrics.observations_last_hour += 1

    def _on_opportunity(self, event) -> None:
        self._metrics.total_opportunities += 1
        self._metrics.new_opportunities_24h += 1
        category = event.payload.get("category", "unknown")
        self._metrics.opportunities_by_category[category] = self._metrics.opportunities_by_category.get(category, 0) + 1

    def _on_opportunity_scored(self, event) -> None:
        score = event.payload.get("score", 0)
        if score > 0.8:
            self._metrics.high_value_opportunities += 1

    def _on_task_started(self, event) -> None:
        self._metrics.tasks_in_progress += 1

    def _on_task_completed(self, event) -> None:
        self._metrics.tasks_in_progress = max(0, self._metrics.tasks_in_progress - 1)
        self._metrics.tasks_completed_today += 1

    def _on_task_failed(self, event) -> None:
        self._metrics.tasks_in_progress = max(0, self._metrics.tasks_in_progress - 1)
        self._metrics.tasks_failed_today += 1

    def _on_revenue(self, event) -> None:
        amount = event.payload.get("amount", 0)
        platform = event.payload.get("platform", "unknown")
        category = event.payload.get("category", "unknown")

        self._metrics.total_revenue += amount
        self._metrics.revenue_today += amount
        self._metrics.revenue_this_month += amount

        self._metrics.revenue_by_platform[platform] = self._metrics.revenue_by_platform.get(platform, 0) + amount
        self._metrics.revenue_by_category[category] = self._metrics.revenue_by_category.get(category, 0) + amount

    def _on_learning(self, event) -> None:
        self._metrics.total_learnings += 1
        self._metrics.learnings_this_week += 1
        if event.payload.get("type") == "pattern":
            self._metrics.patterns_discovered += 1

    def _on_autonomy_change(self, event) -> None:
        self._metrics.autonomy_level = event.payload.get("new_level", "OBSERVER")

    def _on_approval_requested(self, event) -> None:
        self._metrics.pending_approvals += 1

    def _on_approval_decided(self, event) -> None:
        self._metrics.pending_approvals = max(0, self._metrics.pending_approvals - 1)

    def _on_component_health(self, event) -> None:
        component = event.payload.get("component", "unknown")
        self._component_health[component] = event.payload

    def update_system_metrics(self) -> None:
        """Update system-level metrics (CPU, memory, disk, uptime)."""
        try:
            import psutil

            self._metrics.uptime_seconds = time.time() - self._start_time
            self._metrics.memory_usage_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            self._metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            self._metrics.disk_usage_percent = psutil.disk_usage("/").percent
        except ImportError:
            pass  # psutil not available
        except Exception as e:
            logger.warning("Failed to update system metrics: %s", e)

    def get_metrics(self) -> DashboardMetrics:
        """Get current dashboard metrics."""
        self.update_system_metrics()
        self._metrics.timestamp = datetime.now(UTC)
        return self._metrics

    def get_system_status(self) -> SystemStatus:
        """Get overall system health status."""
        issues = []
        components = {}

        # Check each component
        for comp_name, health in self._component_health.items():
            components[comp_name] = health
            if not health.get("healthy", True):
                issues.append(f"{comp_name}: {health.get('issue', 'unhealthy')}")

        # Check core metrics
        if self._metrics.tasks_failed_today > 10:
            issues.append(f"High task failure rate: {self._metrics.tasks_failed_today} today")

        if self._metrics.pending_approvals > 20:
            issues.append(f"Many pending approvals: {self._metrics.pending_approvals}")

        healthy = len(issues) == 0

        return SystemStatus(
            healthy=healthy,
            components=components,
            issues=issues,
        )

    def get_recent_opportunities(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent high-value opportunities."""
        # Would query from discovery engine
        return []

    def get_active_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get currently active tasks."""
        # Would query from commander
        return []

    def get_pending_approvals(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get pending approval requests."""
        # Would query from autonomy manager
        return []


class DashboardAPI:
    """REST/WebSocket API for the dashboard."""

    def __init__(self, aggregator: DashboardAggregator):
        self.aggregator = aggregator
        self.event_bus = get_core_event_bus()

    async def get_dashboard_data(self) -> dict[str, Any]:
        """Get complete dashboard data."""
        metrics = self.aggregator.get_metrics()
        status = self.aggregator.get_system_status()

        return {
            "metrics": {
                "sensors": {
                    "active": metrics.active_sensors,
                    "total_observations": metrics.total_observations,
                    "last_hour": metrics.observations_last_hour,
                },
                "opportunities": {
                    "total": metrics.total_opportunities,
                    "new_24h": metrics.new_opportunities_24h,
                    "high_value": metrics.high_value_opportunities,
                    "by_category": metrics.opportunities_by_category,
                },
                "agents": {
                    "active": metrics.active_agents,
                    "by_type": metrics.agents_by_type,
                    "tasks_in_progress": metrics.tasks_in_progress,
                    "completed_today": metrics.tasks_completed_today,
                    "failed_today": metrics.tasks_failed_today,
                },
                "revenue": {
                    "total": metrics.total_revenue,
                    "today": metrics.revenue_today,
                    "this_month": metrics.revenue_this_month,
                    "pending": metrics.pending_payouts,
                    "by_platform": metrics.revenue_by_platform,
                    "by_category": metrics.revenue_by_category,
                },
                "learning": {
                    "total": metrics.total_learnings,
                    "this_week": metrics.learnings_this_week,
                    "patterns": metrics.patterns_discovered,
                },
                "system": {
                    "uptime_seconds": metrics.uptime_seconds,
                    "memory_mb": metrics.memory_usage_mb,
                    "cpu_percent": metrics.cpu_percent,
                    "disk_percent": metrics.disk_usage_percent,
                },
                "autonomy": {
                    "level": metrics.autonomy_level,
                    "pending_approvals": metrics.pending_approvals,
                },
            },
            "status": {
                "healthy": status.healthy,
                "components": status.components,
                "issues": status.issues,
            },
            "timestamp": metrics.timestamp.isoformat(),
        }

    async def get_opportunities(
        self,
        category: str | None = None,
        min_score: float = 0.0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get filtered opportunities."""
        return self.aggregator.get_recent_opportunities(limit)

    async def get_tasks(
        self,
        status: str | None = None,
        agent: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get tasks."""
        return self.aggregator.get_active_tasks(limit)

    async def get_approvals(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get pending approvals."""
        return self.aggregator.get_pending_approvals(limit)

    async def approve_task(self, approval_id: str) -> dict[str, Any]:
        """Approve a pending task."""
        self.event_bus.publish(
            "approval:decide",
            approval_id=approval_id,
            decision="approved",
        )
        return {"success": True}

    async def reject_task(self, approval_id: str, reason: str = "") -> dict[str, Any]:
        """Reject a pending task."""
        self.event_bus.publish(
            "approval:decide",
            approval_id=approval_id,
            decision="rejected",
            reason=reason,
        )
        return {"success": True}

    async def set_autonomy_level(self, level: str) -> dict[str, Any]:
        """Change autonomy level."""
        self.event_bus.publish("autonomy:set_level", level=level)
        return {"success": True}

    async def trigger_discovery(self) -> dict[str, Any]:
        """Manually trigger opportunity discovery."""
        self.event_bus.publish("discovery:trigger", {"manual": True})
        return {"success": True, "message": "Discovery triggered"}

    async def get_health(self) -> dict[str, Any]:
        """Health check endpoint."""
        status = self.aggregator.get_system_status()
        return {
            "healthy": status.healthy,
            "issues": status.issues,
            "components": status.components,
            "timestamp": datetime.now(UTC).isoformat(),
        }


# ──────────────────────────────────────────────────────────────────────────
# SINGLETON
# ──────────────────────────────────────────────────────────────────────────

_dashboard_aggregator: DashboardAggregator | None = None
_dashboard_api: DashboardAPI | None = None


def get_dashboard_aggregator() -> DashboardAggregator:
    """Get or create the dashboard aggregator."""
    global _dashboard_aggregator
    if _dashboard_aggregator is None:
        _dashboard_aggregator = DashboardAggregator()
    return _dashboard_aggregator


def get_dashboard_api() -> DashboardAPI:
    """Get or create the dashboard API."""
    global _dashboard_api
    if _dashboard_api is None:
        _dashboard_api = DashboardAPI(get_dashboard_aggregator())
    return _dashboard_api
