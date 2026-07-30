"""Reviewer Specialist — Code review, quality assurance, and approval."""

from __future__ import annotations

import logging
from typing import Any

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.reviewer")


class ReviewerAgent(SpecialistAgent):
    """Reviewer — Code review and quality assurance specialist.
    
    Objectives:
    - Primary: Review code and changes for quality
    - Secondary: Grant/deny approvals, ensure standards compliance
    
    Limits:
    - Max 8 concurrent reviews
    - Max 300s per review
    
    Tools:
    - Code analysis
    - Quality checks
    - Security review
    - Approval system
    
    Priorities:
    - Priority level: 4
    - Task preferences: code review, quality check
    
    Handoffs:
    - Receives from: Coder, Security
    - Hands off to: Commander (approval), Documentation
    """
    
    def _get_agent_id(self) -> AgentId:
        return AgentId.REVIEWER
    
    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Review code and changes for quality",
            secondary_objectives=[
                "Grant or deny approvals",
                "Ensure coding standards compliance",
                "Security review of changes",
            ],
            max_concurrent_tasks=8,
            max_execution_time=300,
            available_tools=[
                "code_analysis",
                "quality_check",
                "security_review",
                "approval_system",
            ],
            priority_level=4,
            task_preferences=["code_review", "quality_check"],
            handoff_targets=[AgentId.COMMANDER, AgentId.DOCUMENTATION],
            handoff_conditions={
                "approval_granted": "commander",
                "approval_denied": "commander",
                "documentation_needed": "documentation",
            },
        )
    
    def _get_specialist_tools(self) -> list[str]:
        return ["code_analysis", "quality_check", "security_review", "approval_system"]
    
    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.COMMANDER, AgentId.DOCUMENTATION]
    
    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.REVIEW_REQUESTED, EventType.CODE_REVIEWED]
    
    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.REVIEW_REQUESTED:
            self._execute_review(event)
    
    def _execute_review(self, event: AgentEvent) -> None:
        """Execute code review."""
        code_change = event.payload.get("change", "")
        logger.info(f"[REVIEWER] Reviewing change: {code_change}")
        # Implement review logic