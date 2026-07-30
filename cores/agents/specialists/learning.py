"""Learning Specialist — Knowledge capture and pattern learning."""

from __future__ import annotations

import logging
from typing import Any

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.learning")


class LearningAgent(SpecialistAgent):
    """Learning — Knowledge capture and pattern learning specialist.
    
    Objectives:
    - Primary: Capture knowledge and learn from system operations
    - Secondary: Analyze patterns, process feedback, improve decision-making
    
    Limits:
    - Max 15 concurrent learning tasks
    - Max 240s per learning operation
    
    Tools:
    - Knowledge storage
    - Pattern recognition
    - Error analysis
    - Feedback processing
    
    Priorities:
    - Priority level: 4
    - Task preferences: pattern learning, knowledge capture
    
    Handoffs:
    - Receives from: All specialists
    - Hands off to: Evolution (improvement suggestions)
    """
    
    def _get_agent_id(self) -> AgentId:
        return AgentId.LEARNING
    
    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Capture knowledge and learn from system operations",
            secondary_objectives=[
                "Analyze patterns in data",
                "Process feedback from operations",
                "Improve decision-making through learning",
            ],
            max_concurrent_tasks=15,
            max_execution_time=240,
            available_tools=[
                "knowledge_storage",
                "pattern_recognition",
                "error_analysis",
                "feedback_processing",
            ],
            priority_level=4,
            task_preferences=["pattern_learning", "knowledge_capture"],
            handoff_targets=[AgentId.EVOLUTION],
            handoff_conditions={
                "improvement_opportunity": "evolution",
            },
        )
    
    def _get_specialist_tools(self) -> list[str]:
        return ["knowledge_storage", "pattern_recognition", "error_analysis", "feedback_processing"]
    
    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.EVOLUTION]
    
    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.PATTERN_LEARNED, EventType.ERROR_ANALYZED, EventType.FEEDBACK_PROCESSED]
    
    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.PATTERN_LEARNED:
            self._process_pattern(event)
        elif event.event_type == EventType.ERROR_ANALYZED:
            self._analyze_error(event)
    
    def _process_pattern(self, event: AgentEvent) -> None:
        """Process learned pattern."""
        pattern = event.payload.get("pattern", "")
        logger.info(f"[LEARNING] Processing pattern: {pattern}")
    
    def _analyze_error(self, event: AgentEvent) -> None:
        """Analyze error for learning."""
        error = event.payload.get("error", "")
        logger.info(f"[LEARNING] Analyzing error: {error}")