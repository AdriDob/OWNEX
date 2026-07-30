"""Research Specialist — Intelligence gathering and analysis."""

from __future__ import annotations

import logging
from typing import Any

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.research")


class ResearchAgent(SpecialistAgent):
    """Research — Intelligence gathering and analysis specialist.
    
    Objectives:
    - Primary: Gather and analyze intelligence about targets
    - Secondary: Discover vulnerabilities, analyze competitive landscape
    
    Limits:
    - Max 10 concurrent research tasks
    - Max 600s per research operation
    
    Tools:
    - OSINT tools (Shodan, Censys, Wayback)
    - Target discovery
    - Endpoint enumeration
    - Vulnerability scanning
    
    Priorities:
    - Priority level: 3
    - Task preferences: target discovery, intelligence gathering
    
    Handoffs:
    - Receives from: Commander, Planner
    - Hands off to: Security, Coder, Learning
    """
    
    def _get_agent_id(self) -> AgentId:
        return AgentId.RESEARCH
    
    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Gather and analyze intelligence about targets",
            secondary_objectives=[
                "Discover vulnerabilities and attack surface",
                "Analyze competitive landscape",
                "Map technology stacks",
            ],
            max_concurrent_tasks=10,
            max_execution_time=600,
            available_tools=[
                "shodan_search",
                "censys_search",
                "wayback_machine",
                "subdomain_enumeration",
                "endpoint_discovery",
                "technology_detection",
            ],
            priority_level=3,
            task_preferences=["target_discovery", "intelligence_gathering"],
            handoff_targets=[AgentId.SECURITY, AgentId.CODER, AgentId.LEARNING],
            handoff_conditions={
                "vulnerability_found": "security",
                "requires_coding": "coder",
                "pattern_discovered": "learning",
            },
        )
    
    def _get_specialist_tools(self) -> list[str]:
        return ["shodan_search", "censys_search", "wayback_machine", "subdomain_enumeration"]
    
    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.SECURITY, AgentId.CODER, AgentId.LEARNING]
    
    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.RESEARCH_START, EventType.TARGET_DISCOVERED]
    
    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.RESEARCH_START:
            self._execute_research(event)
    
    def _execute_research(self, event: AgentEvent) -> None:
        """Execute research operation."""
        target = event.payload.get("target", "")
        logger.info(f"[RESEARCH] Executing research on: {target}")
        # Implement research logic