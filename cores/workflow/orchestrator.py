"""OWNEX OMEGA Workflow Orchestrator — Workflow execution coordinator.

Coordinates workflow execution with handoffs and event-driven communication.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from cores.agents.types import AgentEvent, AgentId, EventType
from cores.workflow.engine import Workflow, WorkflowEngine, WorkflowTask
from cores.workflow.handoff import Handoff, HandoffManager, HandoffStatus

logger = logging.getLogger("ownex.workflow.orchestrator")


class WorkflowOrchestrator:
    """Orchestrates workflow execution with handoffs.

    Combines WorkflowEngine and HandoffManager to execute departmental workflows.
    """

    def __init__(self) -> None:
        self._engine = WorkflowEngine()
        self._handoff_manager = HandoffManager()
        self._event_callbacks: dict[EventType, list[callable]] = {}

    def create_workflow(
        self,
        name: str,
        description: str,
        tasks: list[WorkflowTask],
        metadata: dict[str, Any] | None = None,
    ) -> Workflow:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())
        return self._engine.create_workflow(workflow_id, name, description, tasks, metadata)

    def start_workflow(self, workflow_id: str) -> bool:
        """Start a workflow and begin task execution."""
        if not self._engine.start_workflow(workflow_id):
            return False

        # Start first ready task
        workflow = self._engine.get_workflow(workflow_id)
        if workflow:
            next_task = workflow.get_next_task()
            if next_task:
                self._assign_and_start_task(workflow_id, next_task.id, next_task.agent_id)

        return True

    def _assign_and_start_task(self, workflow_id: str, task_id: str, agent_id: AgentId) -> bool:
        """Assign and start a task."""
        if not self._engine.assign_task(workflow_id, task_id, agent_id):
            return False

        if not self._engine.start_task(workflow_id, task_id):
            return False

        # Emit task assigned event
        self._emit_event(
            EventType.TASK_ASSIGNED,
            {
                "workflow_id": workflow_id,
                "task_id": task_id,
                "agent_id": agent_id,
            },
        )

        return True

    def complete_task(self, workflow_id: str, task_id: str, result: dict[str, Any]) -> bool:
        """Complete a task and trigger handoffs."""
        if not self._engine.complete_task(workflow_id, task_id, result):
            return False

        workflow = self._engine.get_workflow(workflow_id)
        if not workflow:
            return False

        task = workflow.get_task(task_id)
        if not task:
            return False

        # Emit task completed event
        self._emit_event(
            EventType.TASK_COMPLETED,
            {
                "workflow_id": workflow_id,
                "task_id": task_id,
                "agent_id": task.agent_id,
                "result": result,
            },
        )

        # Trigger handoff based on result
        handoff_condition = result.get("handoff_condition")
        if handoff_condition:
            self._trigger_handoff(workflow_id, task_id, handoff_condition, task.agent_id, result)

        # Start next task if workflow not complete
        if not workflow.is_complete():
            next_task = workflow.get_next_task()
            if next_task:
                self._assign_and_start_task(workflow_id, next_task.id, next_task.agent_id)
        else:
            # Emit workflow completed event
            self._emit_event(
                EventType.WORKFLOW_COMPLETED,
                {
                    "workflow_id": workflow_id,
                    "status": workflow.status.value,
                },
            )

        return True

    def fail_task(self, workflow_id: str, task_id: str, error: str) -> bool:
        """Fail a task."""
        if not self._engine.fail_task(workflow_id, task_id, error):
            return False

        workflow = self._engine.get_workflow(workflow_id)
        if not workflow:
            return False

        task = workflow.get_task(task_id)
        if not task:
            return False

        # Emit task failed event
        self._emit_event(
            EventType.TASK_FAILED,
            {
                "workflow_id": workflow_id,
                "task_id": task_id,
                "agent_id": task.agent_id,
                "error": error,
            },
        )

        # Trigger debug handoff if error
        self._trigger_handoff(workflow_id, task_id, "error_detected", task.agent_id, {"error": error})

        return True

    def _trigger_handoff(
        self,
        workflow_id: str,
        task_id: str,
        condition_type: str,
        source_agent: AgentId,
        payload: dict[str, Any],
    ) -> Handoff | None:
        """Trigger a handoff between departments."""
        handoff = self._handoff_manager.trigger_handoff(
            workflow_id=workflow_id,
            task_id=task_id,
            condition_type=condition_type,
            source_agent=source_agent,
            payload=payload,
        )

        if handoff:
            # Emit department requested event
            self._emit_event(
                EventType.DEPARTMENT_REQUESTED,
                {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "handoff_id": handoff.id,
                    "source_agent": source_agent,
                    "target_agent": handoff.target_agent,
                    "condition": condition_type,
                },
            )

            # If auto-handoff, create new task for target agent
            if handoff.status == HandoffStatus.ACCEPTED:
                self._create_handoff_task(workflow_id, handoff)

        return handoff

    def _create_handoff_task(self, workflow_id: str, handoff: Handoff) -> bool:
        """Create a new task for the target agent of a handoff."""
        workflow = self._engine.get_workflow(workflow_id)
        if not workflow:
            return False

        # Create new task for target agent
        new_task = WorkflowTask(
            id=f"{handoff.task_id}:handoff",
            name=f"Handoff: {handoff.condition.condition_type}",
            agent_id=handoff.target_agent,
            description=f"Handle handoff from {handoff.source_agent}",
            dependencies=[handoff.task_id],
        )

        workflow.tasks.append(new_task)
        logger.info(f"[ORCHESTRATOR] Created handoff task for {handoff.target_agent}")

        return True

    def accept_handoff(self, handoff_id: str) -> bool:
        """Accept a pending handoff."""
        if not self._handoff_manager.accept_handoff(handoff_id):
            return False

        handoff = self._handoff_manager.get_handoff(handoff_id)
        if handoff:
            self._create_handoff_task(handoff.workflow_id, handoff)

        return True

    def reject_handoff(self, handoff_id: str, reason: str) -> bool:
        """Reject a pending handoff."""
        return self._handoff_manager.reject_handoff(handoff_id, reason)

    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a workflow."""
        return self._engine.pause_workflow(workflow_id)

    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        if not self._engine.resume_workflow(workflow_id):
            return False

        # Resume execution
        workflow = self._engine.get_workflow(workflow_id)
        if workflow:
            next_task = workflow.get_next_task()
            if next_task:
                self._assign_and_start_task(workflow_id, next_task.id, next_task.agent_id)

        return True

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a workflow."""
        return self._engine.cancel_workflow(workflow_id)

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Get a workflow by ID."""
        return self._engine.get_workflow(workflow_id)

    def get_active_workflow(self) -> Workflow | None:
        """Get the currently active workflow."""
        return self._engine.get_active_workflow()

    def list_workflows(self) -> list[Workflow]:
        """List all workflows."""
        return self._engine.list_workflows()

    def get_handoff(self, handoff_id: str) -> Handoff | None:
        """Get a handoff by ID."""
        return self._handoff_manager.get_handoff(handoff_id)

    def get_handoffs_for_workflow(self, workflow_id: str) -> list[Handoff]:
        """Get all handoffs for a workflow."""
        return self._handoff_manager.get_handoffs_for_workflow(workflow_id)

    def get_pending_handoffs(self, agent_id: AgentId) -> list[Handoff]:
        """Get pending handoffs for an agent."""
        return self._handoff_manager.get_pending_handoffs(agent_id)

    def list_handoff_conditions(self) -> list:
        """List all handoff conditions."""
        return self._handoff_manager.list_conditions()

    def register_event_callback(self, event_type: EventType, callback: callable) -> None:
        """Register a callback for an event type."""
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)

    def _emit_event(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit an event to registered callbacks."""
        if event_type in self._event_callbacks:
            for callback in self._event_callbacks[event_type]:
                try:
                    callback(AgentEvent(event_type=event_type, payload=payload))
                except Exception as e:
                    logger.error(f"[ORCHESTRATOR] Event callback error: {e}")
