"""Security Specialist — Vulnerability detection and security testing."""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.security")


class SecurityAgent(SpecialistAgent):
    """Security — Vulnerability detection and security testing specialist.
    
    Objectives:
    - Primary: Detect vulnerabilities and perform security testing
    - Secondary: Collect evidence, confirm exploits, validate findings
    
    Limits:
    - Max 3 concurrent security scans
    - Max 1200s per security operation
    
    Tools:
    - Vulnerability scanners (Nuclei, Nmap)
    - Exploit testing
    - Evidence collection
    - Security validation
    
    Priorities:
    - Priority level: 2
    - Task preferences: security scanning, vulnerability detection
    
    Handoffs:
    - Receives from: Commander, Research
    - Hands off to: Reviewer, Documentation, Learning
    """

    def _get_agent_id(self) -> AgentId:
        return AgentId.SECURITY

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Detect vulnerabilities and perform security testing",
            secondary_objectives=[
                "Collect evidence for findings",
                "Confirm exploit viability",
                "Validate security hypotheses",
            ],
            max_concurrent_tasks=3,
            max_execution_time=1200,
            available_tools=[
                "nuclei_scanner",
                "nmap_scanner",
                "exploit_testing",
                "evidence_collection",
                "security_validation",
            ],
            priority_level=2,
            task_preferences=["security_scanning", "vulnerability_detection"],
            handoff_targets=[AgentId.REVIEWER, AgentId.DOCUMENTATION, AgentId.LEARNING],
            handoff_conditions={
                "evidence_collected": "reviewer",
                "report_needed": "documentation",
                "pattern_learned": "learning",
            },
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["nuclei_scanner", "nmap_scanner", "exploit_testing", "evidence_collection"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.REVIEWER, AgentId.DOCUMENTATION, AgentId.LEARNING]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.SECURITY_SCAN, EventType.VULNERABILITY_FOUND]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.SECURITY_SCAN:
            self._execute_scan(event)

    def _execute_scan(self, event: AgentEvent) -> None:
        """Execute security scan."""
        target = event.payload.get("target", "")
        logger.info(f"[SECURITY] Scanning target: {target}")
