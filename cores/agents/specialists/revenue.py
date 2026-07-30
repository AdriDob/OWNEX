"""Revenue Agent — Business Department.

Converts technology into results and revenue.
"""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.revenue")


class RevenueAgent(SpecialistAgent):
    """Revenue Agent — Business Department.

    Converts technology into results and revenue.

    Objectives:
    - Primary: Find opportunities, analyze markets, prepare proposals
    - Secondary: Prioritize tasks with ROI, calculate revenue

    Limits:
    - Max 5 concurrent revenue tasks
    - Max 240s per revenue operation

    Tools:
    - Market research
    - Financial analysis
    - Proposal writing
    - ROI calculators

    Priorities:
    - Priority level: 3
    - Task preferences: opportunity finding, revenue analysis

    Handoffs:
    - Receives from: Research, Product
    - Hands off to: Orchestrator (prioritization)
    """

    def _get_agent_id(self) -> AgentId:
        return AgentId.REVENUE

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Find opportunities, analyze markets, prepare proposals",
            secondary_objectives=[
                "Prioritize tasks with ROI",
                "Calculate revenue potential",
                "Analyze market trends",
                "Prepare business proposals",
            ],
            max_concurrent_tasks=5,
            max_execution_time=240,
            available_tools=[
                "market_research",
                "financial_analysis",
                "proposal_writing",
                "roi_calculators",
            ],
            priority_level=3,
            task_preferences=["opportunity_finding", "revenue_analysis"],
            handoff_targets=[AgentId.ORCHESTRATOR],
            handoff_conditions={
                "opportunity_found": "orchestrator",
            },
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["market_research", "financial_analysis", "proposal_writing"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.ORCHESTRATOR]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.OPPORTUNITY_FOUND, EventType.MARKET_ANALYZED, EventType.REVENUE_CALCULATED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.OPPORTUNITY_FOUND:
            self._analyze_opportunity(event)
        elif event.event_type == EventType.REVENUE_CALCULATED:
            self._analyze_revenue(event)

    def _analyze_opportunity(self, event: AgentEvent) -> None:
        """Analyze opportunity for revenue potential."""
        opportunity = event.payload.get("opportunity", "")
        logger.info(f"[REVENUE] Analyzing opportunity: {opportunity}")

    def _analyze_revenue(self, event: AgentEvent) -> None:
        """Analyze revenue data."""
        period = event.payload.get("period", "")
        logger.info(f"[REVENUE] Analyzing revenue for: {period}")
