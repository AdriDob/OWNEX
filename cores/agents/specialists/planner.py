"""Planner Specialist — Creates detailed plans for complex tasks."""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.planner")


class PlannerAgent(SpecialistAgent):
    """Planner — Task planning and decomposition specialist.
    
    Objectives:
    - Primary: Create detailed plans for complex objectives
    - Secondary: Estimate resources, resolve dependencies, optimize execution order
    
    Limits:
    - Max 5 concurrent plans
    - Max 300s per plan generation
    
    Tools:
    - Task decomposition
    - Resource estimation
    - Dependency resolution
    - Timeline optimization
    
    Priorities:
    - Priority level: 2
    - Task preferences: plan generation, resource allocation
    
    Handoffs:
    - Receives from: Commander
    - Hands off to: All specialists (based on plan)
    """

    def _get_agent_id(self) -> AgentId:
        return AgentId.PLANNER

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Create detailed plans for complex objectives",
            secondary_objectives=[
                "Estimate required resources",
                "Resolve task dependencies",
                "Optimize execution order",
                "Handle plan changes dynamically",
            ],
            max_concurrent_tasks=5,
            max_execution_time=300,
            available_tools=[
                "task_decomposition",
                "resource_estimation",
                "dependency_resolution",
                "timeline_optimization",
            ],
            priority_level=2,
            task_preferences=["plan_generation", "resource_allocation"],
            handoff_targets=[
                AgentId.RESEARCH,
                AgentId.CODER,
                AgentId.BROWSER,
                AgentId.SECURITY,
            ],
            handoff_conditions={
                "requires_research": "research",
                "requires_coding": "coder",
                "requires_browser": "browser",
                "requires_security": "security",
            },
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["task_decomposition", "resource_estimation", "dependency_resolution", "timeline_optimization"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.RESEARCH, AgentId.CODER, AgentId.BROWSER, AgentId.SECURITY]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.PLAN_REQUESTED, EventType.TASK_ASSIGNED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.PLAN_REQUESTED:
            self._generate_plan(event)
        elif event.event_type == EventType.TASK_ASSIGNED:
            self._update_plan(event)

    def _generate_plan(self, event: AgentEvent) -> None:
        """Generate a detailed plan for the objective."""
        objective = event.payload.get("objective", "")
        logger.info(f"[PLANNER] Generating plan for: {objective}")
        # Implement plan generation logic

    def _update_plan(self, event: AgentEvent) -> None:
        """Update existing plan based on new information."""
        # Implement plan update logic
        pass
