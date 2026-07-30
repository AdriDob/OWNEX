"""Evolution Specialist — System improvement and self-evolution."""

from __future__ import annotations

import logging
from typing import Any

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.evolution")


class EvolutionAgent(SpecialistAgent):
    """Evolution — System improvement and self-evolution specialist.
    
    Objectives:
    - Primary: Improve system through continuous analysis and optimization
    - Secondary: Audit infrastructure, suggest improvements, watch technology trends
    
    Limits:
    - Max 3 concurrent evolution tasks
    - Max 600s per evolution operation
    
    Tools:
    - System auditing
    - Improvement suggestion
    - Self-testing
    - Technology watching
    
    Priorities:
    - Priority level: 5
    - Task preferences: system improvement, infrastructure evolution
    
    Handoffs:
    - Receives from: Finance, Learning
    - Hands off to: Commander (implementation approval)
    """
    
    def _get_agent_id(self) -> AgentId:
        return AgentId.EVOLUTION
    
    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Improve system through continuous analysis and optimization",
            secondary_objectives=[
                "Audit system infrastructure",
                "Suggest improvements based on learning",
                "Watch technology trends for upgrades",
            ],
            max_concurrent_tasks=3,
            max_execution_time=600,
            available_tools=[
                "system_audit",
                "improvement_suggestion",
                "self_testing",
                "technology_watching",
            ],
            priority_level=5,
            task_preferences=["system_improvement", "infrastructure_evolution"],
            handoff_targets=[AgentId.COMMANDER],
            handoff_conditions={
                "improvement_ready": "commander",
            },
        )
    
    def _get_specialist_tools(self) -> list[str]:
        return ["system_audit", "improvement_suggestion", "self_testing", "technology_watching"]
    
    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.COMMANDER]
    
    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.SYSTEM_AUDIT, EventType.IMPROVEMENT_SUGGESTED]
    
    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.SYSTEM_AUDIT:
            self._execute_audit(event)
        elif event.event_type == EventType.IMPROVEMENT_SUGGESTED:
            self._process_improvement(event)
    
    def _execute_audit(self, event: AgentEvent) -> None:
        """Execute system audit."""
        scope = event.payload.get("scope", "")
        logger.info(f"[EVOLUTION] Executing audit: {scope}")
    
    def _process_improvement(self, event: AgentEvent) -> None:
        """Process improvement suggestion."""
        improvement = event.payload.get("improvement", "")
        logger.info(f"[EVOLUTION] Processing improvement: {improvement}")