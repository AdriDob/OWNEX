"""Browser Specialist — Web automation and interaction."""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.browser")


class BrowserAgent(SpecialistAgent):
    """Browser — Web automation and interaction specialist.

    Objectives:
    - Primary: Automate web interactions and scraping
    - Secondary: Form submission, element interaction, navigation

    Limits:
    - Max 5 concurrent browser sessions
    - Max 600s per browser operation

    Tools:
    - Playwright automation
    - Form submission
    - Element interaction
    - Web scraping

    Priorities:
    - Priority level: 3
    - Task preferences: browser automation, web scraping

    Handoffs:
    - Receives from: Commander, Planner
    - Hands off to: Research, Documentation
    """

    def _get_agent_id(self) -> AgentId:
        return AgentId.BROWSER

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Automate web interactions and scraping",
            secondary_objectives=[
                "Form submission and validation",
                "Element interaction and clicking",
                "Navigation and page handling",
            ],
            max_concurrent_tasks=5,
            max_execution_time=600,
            available_tools=[
                "playwright_automation",
                "form_submission",
                "element_interaction",
                "web_scraping",
            ],
            priority_level=3,
            task_preferences=["browser_automation", "web_scraping"],
            handoff_targets=[AgentId.RESEARCH, AgentId.DOCUMENTATION],
            handoff_conditions={
                "data_collected": "research",
                "guide_needed": "documentation",
            },
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["playwright_automation", "form_submission", "element_interaction", "web_scraping"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.RESEARCH, AgentId.DOCUMENTATION]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.BROWSER_NAVIGATE, EventType.BROWSER_SCRAPE]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.BROWSER_NAVIGATE:
            self._navigate(event)
        elif event.event_type == EventType.BROWSER_SCRAPE:
            self._scrape(event)

    def _navigate(self, event: AgentEvent) -> None:
        """Navigate to URL."""
        url = event.payload.get("url", "")
        logger.info(f"[BROWSER] Navigating to: {url}")

    def _scrape(self, event: AgentEvent) -> None:
        """Scrape web page."""
        target = event.payload.get("target", "")
        logger.info(f"[BROWSER] Scraping: {target}")
