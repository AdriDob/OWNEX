"""Finance Specialist — Financial tracking and revenue optimization."""

from __future__ import annotations

import logging
from typing import Any

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.finance")


class FinanceAgent(SpecialistAgent):
    """Finance — Financial tracking and revenue optimization specialist.
    
    Objectives:
    - Primary: Track financial performance and optimize revenue
    - Secondary: Calculate costs, manage payouts, track profitability
    
    Limits:
    - Max 5 concurrent financial tasks
    - Max 180s per financial operation
    
    Tools:
    - Revenue calculation
    - Cost tracking
    - Payout management
    - Profitability analysis
    
    Priorities:
    - Priority level: 4
    - Task preferences: revenue calculation, cost tracking
    
    Handoffs:
    - Receives from: Commander, Security (payouts)
    - Hands off to: Evolution (optimization suggestions)
    """
    
    def _get_agent_id(self) -> AgentId:
        return AgentId.FINANCE
    
    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Track financial performance and optimize revenue",
            secondary_objectives=[
                "Calculate operational costs",
                "Manage payouts and payments",
                "Track profitability by project",
            ],
            max_concurrent_tasks=5,
            max_execution_time=180,
            available_tools=[
                "revenue_calculation",
                "cost_tracking",
                "payout_management",
                "profitability_analysis",
            ],
            priority_level=4,
            task_preferences=["revenue_calculation", "cost_tracking"],
            handoff_targets=[AgentId.EVOLUTION],
            handoff_conditions={
                "optimization_needed": "evolution",
            },
        )
    
    def _get_specialist_tools(self) -> list[str]:
        return ["revenue_calculation", "cost_tracking", "payout_management", "profitability_analysis"]
    
    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.EVOLUTION]
    
    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.FINANCIAL_UPDATED, EventType.REVENUE_CALCULATED]
    
    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.REVENUE_CALCULATED:
            self._analyze_revenue(event)
    
    def _analyze_revenue(self, event: AgentEvent) -> None:
        """Analyze revenue data."""
        period = event.payload.get("period", "")
        logger.info(f"[FINANCE] Analyzing revenue for: {period}")