"""Specialist Agent Base — Extended structure for OWNEX team specialists."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from cores.agents.base import BaseAgent
from cores.agents.types import AgentId, EventType

logger = logging.getLogger("ownex.agents.specialist")


@dataclass
class SpecialistConfig:
    """Configuration for a specialist agent."""

    # Objectives
    primary_objective: str
    secondary_objectives: list[str] = field(default_factory=list)

    # Limits
    max_concurrent_tasks: int = 3
    max_execution_time: int = 300  # seconds
    resource_limits: dict[str, Any] = field(default_factory=dict)

    # Tools
    available_tools: list[str] = field(default_factory=list)
    tool_permissions: dict[str, bool] = field(default_factory=dict)

    # Priorities
    priority_level: int = 5  # 1 (highest) -> 10 (lowest)
    task_preferences: list[str] = field(default_factory=list)

    # Memory
    memory_namespace: str = "general"
    memory_retention: int = 1000  # max items

    # Communication
    communication_channels: list[str] = field(default_factory=list)
    response_timeout: int = 60  # seconds

    # Handoffs
    handoff_targets: list[AgentId] = field(default_factory=list)
    handoff_conditions: dict[str, str] = field(default_factory=dict)


class SpecialistAgent(BaseAgent, ABC):
    """Base class for all OWNEX specialist agents.

    Each specialist has:
    - Clear objectives (primary + secondary)
    - Defined limits (concurrency, time, resources)
    - Specific tools with permissions
    - Priority preferences
    - Memory namespace
    - Communication channels
    - Handoff targets and conditions
    """

    def __init__(self, bus: Any = None, config: SpecialistConfig | None = None) -> None:
        super().__init__(bus)
        self.config = config or self._get_default_config()
        self._active_tasks: dict[str, Any] = {}
        self._task_queue: list[dict[str, Any]] = []
        self._performance_metrics: dict[str, Any] = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_execution_time": 0.0,
            "handoffs_completed": 0,
            "resource_usage": {},
        }

    @abstractmethod
    def _get_default_config(self) -> SpecialistConfig:
        """Return default configuration for this specialist."""
        return SpecialistConfig(
            primary_objective="Execute specialized tasks",
            secondary_objectives=[],
        )

    @abstractmethod
    def _get_specialist_tools(self) -> list[str]:
        """Return list of tools this specialist can use."""
        return []

    @abstractmethod
    def _get_handoff_targets(self) -> list[AgentId]:
        """Return list of agents this specialist can handoff to."""
        return []

    def can_handle_task(self, task: dict[str, Any]) -> bool:
        """Check if this specialist can handle a given task."""
        task_type = task.get("type", "")
        return task_type in self.config.task_preferences

    def should_handoff(self, task: dict[str, Any]) -> tuple[bool, AgentId | None]:
        """Determine if task should be handed off to another specialist."""
        for condition, target_agent in self.config.handoff_conditions.items():
            if self._evaluate_condition(task, condition):
                return True, AgentId(target_agent)
        return False, None

    def _evaluate_condition(self, task: dict[str, Any], condition: str) -> bool:
        """Evaluate a handoff condition."""
        # Simple condition evaluation (can be extended)
        if condition == "complexity_high":
            return task.get("complexity", 0) > 7
        elif condition == "requires_security":
            return task.get("requires_security", False)
        elif condition == "requires_browser":
            return task.get("requires_browser", False)
        elif condition == "requires_coding":
            return task.get("requires_coding", False)
        elif condition == "requires_review":
            return task.get("requires_review", False)
        return False

    def handoff_task(self, task: dict[str, Any], target: AgentId) -> None:
        """Handoff a task to another specialist."""
        self.emit(
            event_type=EventType.TASK_DELEGATED,
            payload={
                "task": task,
                "from_agent": self.agent_id.value,
                "to_agent": target.value,
                "reason": "specialist_handoff",
            },
            target=target,
            correlation_id=task.get("correlation_id", ""),
        )
        self._performance_metrics["handoffs_completed"] += 1
        logger.info(f"[SPECIALIST] {self.agent_id.value} handed off task to {target.value}")

    def update_performance_metrics(self, success: bool, execution_time: float) -> None:
        """Update performance metrics after task completion."""
        if success:
            self._performance_metrics["tasks_completed"] += 1
        else:
            self._performance_metrics["tasks_failed"] += 1

        # Update average execution time
        total = self._performance_metrics["tasks_completed"] + self._performance_metrics["tasks_failed"]
        current_avg = self._performance_metrics["avg_execution_time"]
        self._performance_metrics["avg_execution_time"] = (
            (current_avg * (total - 1) + execution_time) / total
        )

    def get_specialist_health(self) -> dict[str, Any]:
        """Return detailed health status for this specialist."""
        base_health = self.health()
        specialist_health = {
            "config": {
                "primary_objective": self.config.primary_objective,
                "secondary_objectives": self.config.secondary_objectives,
                "max_concurrent_tasks": self.config.max_concurrent_tasks,
                "priority_level": self.config.priority_level,
            },
            "tools": {
                "available": self.config.available_tools,
                "permissions": self.config.tool_permissions,
            },
            "performance": self._performance_metrics,
            "current_state": {
                "active_tasks": len(self._active_tasks),
                "queued_tasks": len(self._task_queue),
                "memory_usage": len(self._active_tasks) / max(self.config.memory_retention, 1),
            },
        }
        return {**base_health, **specialist_health}

    def optimize_cooperation(self) -> dict[str, Any]:
        """Analyze and suggest optimizations for agent cooperation."""
        suggestions = []

        # Analyze handoff patterns
        if self._performance_metrics["handoffs_completed"] > 10:
            suggestions.append({
                "type": "handoff_optimization",
                "suggestion": "Consider direct integration with frequent handoff targets",
                "evidence": f"High handoff count: {self._performance_metrics['handoffs_completed']}",
            })

        # Analyze task completion rate
        total = self._performance_metrics["tasks_completed"] + self._performance_metrics["tasks_failed"]
        if total > 0:
            success_rate = self._performance_metrics["tasks_completed"] / total
            if success_rate < 0.8:
                suggestions.append({
                    "type": "success_rate_improvement",
                    "suggestion": "Review task complexity vs specialist capabilities",
                    "evidence": f"Low success rate: {success_rate:.2%}",
                })

        # Analyze execution time
        avg_time = self._performance_metrics["avg_execution_time"]
        if avg_time > self.config.max_execution_time * 0.8:
            suggestions.append({
                "type": "performance_optimization",
                "suggestion": "Consider task decomposition or parallelization",
                "evidence": f"High avg execution time: {avg_time:.1f}s",
            })

        return {
            "specialist": self.agent_id.value,
            "suggestions": suggestions,
            "optimization_potential": len(suggestions),
        }
