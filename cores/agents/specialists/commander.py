"""Commander Specialist — Coordinates all OWNEX specialists.

The Commander NEVER does actual work. It only:
- Receives high-level objectives
- Decomposes objectives into tasks
- Assigns tasks to appropriate specialists
- Monitors task progress
- Handles failures and retries
- Optimizes team cooperation
- Reports system status
"""

from __future__ import annotations

import logging
from typing import Any

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.commander")


class CommanderAgent(SpecialistAgent):
    """Commander — Team coordination specialist.
    
    Objectives:
    - Primary: Coordinate specialists to achieve system objectives
    - Secondary: Optimize team cooperation, handle failures, report status
    
    Limits:
    - NEVER executes tasks directly
    - Max 50 concurrent delegations
    - Max 120s per coordination cycle
    
    Tools:
    - Task assignment system
    - Agent status monitoring
    - Workflow orchestration
    - Health monitoring dashboard
    
    Priorities:
    - Priority level: 1 (highest)
    - Task preferences: workflow coordination, agent management
    
    Memory:
    - Namespace: "commander"
    - Retains: 10000 items (system-wide state)
    
    Communication:
    - Channels: All specialist agents, system alerts
    - Response timeout: 30s (urgent)
    
    Handoffs:
    - NEVER receives handoffs (top-level coordinator)
    - Can delegate to any specialist
    """
    
    def _get_agent_id(self) -> AgentId:
        return AgentId.COMMANDER
    
    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Coordinate OWNEX specialists to achieve system objectives",
            secondary_objectives=[
                "Optimize team cooperation and performance",
                "Handle task failures and retries",
                "Monitor system health and status",
                "Report system state to users",
            ],
            max_concurrent_tasks=50,  # High concurrency for coordination
            max_execution_time=120,  # 2 min per coordination cycle
            resource_limits={
                "max_delegations": 50,
                "max_monitored_agents": 20,
            },
            available_tools=[
                "task_assignment",
                "agent_monitoring",
                "workflow_orchestration",
                "health_dashboard",
                "failure_handler",
                "status_reporter",
            ],
            tool_permissions={
                "task_assignment": True,
                "agent_monitoring": True,
                "workflow_orchestration": True,
                "health_dashboard": True,
                "failure_handler": True,
                "status_reporter": True,
                # Never has execution tools
                "code_execution": False,
                "browser_automation": False,
                "security_testing": False,
            },
            priority_level=1,  # Highest priority
            task_preferences=[
                "workflow_coordination",
                "agent_management",
                "system_monitoring",
                "failure_recovery",
            ],
            memory_namespace="commander",
            memory_retention=10000,
            communication_channels=[
                "all_specialists",
                "system_alerts",
                "user_interface",
            ],
            response_timeout=30,
            handoff_targets=[],  # Commander doesn't receive handoffs
            handoff_conditions={},
        )
    
    def _get_specialist_tools(self) -> list[str]:
        return [
            "task_assignment",
            "agent_monitoring",
            "workflow_orchestration",
            "health_dashboard",
            "failure_handler",
            "status_reporter",
        ]
    
    def _get_handoff_targets(self) -> list[AgentId]:
        # Commander can delegate to any specialist
        return [
            AgentId.PLANNER,
            AgentId.RESEARCH,
            AgentId.CODER,
            AgentId.REVIEWER,
            AgentId.BROWSER,
            AgentId.SECURITY,
            AgentId.DOCUMENTATION,
            AgentId.LEARNING,
            AgentId.FINANCE,
            AgentId.EVOLUTION,
        ]
    
    def _get_subscriptions(self) -> list[EventType | str]:
        return [
            EventType.TASK_COMPLETED,
            EventType.TASK_FAILED,
            EventType.WORKFLOW_STARTED,
            EventType.WORKFLOW_COMPLETED,
            EventType.AGENT_HEALTH_CHANGED,
            EventType.SYSTEM_ALERT,
            EventType.SYSTEM_ERROR,
            # Legacy events
            EventType.PIPELINE_START,
            EventType.PIPELINE_FAILED,
        ]
    
    def handle_event(self, event: AgentEvent) -> None:
        """Handle coordination events."""
        if event.event_type == EventType.TASK_COMPLETED:
            self._handle_task_completion(event)
        elif event.event_type == EventType.TASK_FAILED:
            self._handle_task_failure(event)
        elif event.event_type == EventType.WORKFLOW_STARTED:
            self._handle_workflow_start(event)
        elif event.event_type == EventType.WORKFLOW_COMPLETED:
            self._handle_workflow_completion(event)
        elif event.event_type == EventType.AGENT_HEALTH_CHANGED:
            self._handle_agent_health_change(event)
        elif event.event_type in (EventType.SYSTEM_ALERT, EventType.SYSTEM_ERROR):
            self._handle_system_alert(event)
    
    def _handle_task_completion(self, event: AgentEvent) -> None:
        """Handle task completion from a specialist."""
        task_id = event.payload.get("task_id", "")
        specialist = event.payload.get("specialist", "")
        logger.info(f"[COMMANDER] Task {task_id} completed by {specialist}")
        
        # Check if this was part of a workflow
        workflow_id = event.payload.get("workflow_id", "")
        if workflow_id:
            self._advance_workflow(workflow_id, task_id)
    
    def _handle_task_failure(self, event: AgentEvent) -> None:
        """Handle task failure from a specialist."""
        task_id = event.payload.get("task_id", "")
        specialist = event.payload.get("specialist", "")
        error = event.payload.get("error", "")
        
        logger.warning(f"[COMMANDER] Task {task_id} failed on {specialist}: {error}")
        
        # Attempt recovery or reassignment
        self._handle_failure_recovery(task_id, specialist, error)
    
    def _handle_workflow_start(self, event: AgentEvent) -> None:
        """Handle workflow initiation."""
        workflow_id = event.payload.get("workflow_id", "")
        logger.info(f"[COMMANDER] Workflow {workflow_id} started")
    
    def _handle_workflow_completion(self, event: AgentEvent) -> None:
        """Handle workflow completion."""
        workflow_id = event.payload.get("workflow_id", "")
        logger.info(f"[COMMANDER] Workflow {workflow_id} completed")
    
    def _handle_agent_health_change(self, event: AgentEvent) -> None:
        """Handle agent health status changes."""
        agent_id = event.payload.get("agent_id", "")
        status = event.payload.get("status", "")
        
        if status == "error":
            logger.error(f"[COMMANDER] Agent {agent_id} in error state")
            self._handle_unhealthy_agent(agent_id)
    
    def _handle_system_alert(self, event: AgentEvent) -> None:
        """Handle system-level alerts."""
        alert_type = event.payload.get("alert_type", "")
        severity = event.payload.get("severity", "info")
        
        logger.warning(f"[COMMANDER] System alert: {alert_type} ({severity})")
        
        if severity in ("critical", "error"):
            self._handle_critical_alert(alert_type, event.payload)
    
    def _advance_workflow(self, workflow_id: str, completed_task_id: str) -> None:
        """Advance workflow to next stage."""
        # Implement workflow advancement logic
        pass
    
    def _handle_failure_recovery(self, task_id: str, failed_specialist: str, error: str) -> None:
        """Handle task failure recovery."""
        # Implement retry or reassignment logic
        pass
    
    def _handle_unhealthy_agent(self, agent_id: str) -> None:
        """Handle unhealthy agent."""
        # Implement agent recovery or replacement logic
        pass
    
    def _handle_critical_alert(self, alert_type: str, payload: dict[str, Any]) -> None:
        """Handle critical system alerts."""
        # Implement critical alert handling
        pass