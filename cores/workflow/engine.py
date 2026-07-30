"""OWNEX OMEGA Workflow Engine — Core workflow execution system.

Orchestrates departmental workflows with handoffs between agents.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.workflow.engine")


class WorkflowStatus(StrEnum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    """Status of a workflow task."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowTask:
    """A single task within a workflow."""
    id: str
    name: str
    agent_id: str  # Use string to avoid AgentId conflict
    description: str
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class Workflow:
    """A workflow composed of multiple tasks."""
    id: str
    name: str
    description: str
    tasks: list[WorkflowTask] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_task(self, task_id: str) -> WorkflowTask | None:
        """Get a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_ready_tasks(self) -> list[WorkflowTask]:
        """Get tasks that are ready to execute (dependencies met)."""
        ready = []
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            # Check if all dependencies are completed
            deps_met = all(
                self.get_task(dep_id).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
                if self.get_task(dep_id) is not None
            )
            if deps_met:
                ready.append(task)
        return ready

    def get_next_task(self) -> WorkflowTask | None:
        """Get the next task to execute (first ready task)."""
        ready = self.get_ready_tasks()
        return ready[0] if ready else None

    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return all(task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED) for task in self.tasks)

    def is_failed(self) -> bool:
        """Check if workflow has failed."""
        return any(task.status == TaskStatus.FAILED for task in self.tasks)


class WorkflowEngine:
    """Core workflow execution engine.

    Manages workflow lifecycle, task assignment, and execution coordination.
    """

    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}
        self._active_workflow: str | None = None

    def create_workflow(
        self,
        workflow_id: str,
        name: str,
        description: str,
        tasks: list[WorkflowTask],
        metadata: dict[str, Any] | None = None,
    ) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            tasks=tasks,
            metadata=metadata or {},
        )
        self._workflows[workflow_id] = workflow
        logger.info(f"[WORKFLOW] Created workflow {workflow_id}: {name}")
        return workflow

    def start_workflow(self, workflow_id: str) -> bool:
        """Start a workflow execution."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            logger.error(f"[WORKFLOW] Workflow {workflow_id} not found")
            return False

        if workflow.status != WorkflowStatus.PENDING:
            logger.warning(f"[WORKFLOW] Workflow {workflow_id} already started")
            return False

        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.utcnow()
        self._active_workflow = workflow_id
        logger.info(f"[WORKFLOW] Started workflow {workflow_id}")
        return True

    def assign_task(self, workflow_id: str, task_id: str, agent_id: str) -> bool:
        """Assign a task to an agent."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            logger.error(f"[WORKFLOW] Workflow {workflow_id} not found")
            return False

        task = workflow.get_task(task_id)
        if not task:
            logger.error(f"[WORKFLOW] Task {task_id} not found in workflow {workflow_id}")
            return False

        task.agent_id = agent_id
        task.status = TaskStatus.ASSIGNED
        task.assigned_at = datetime.utcnow()
        logger.info(f"[WORKFLOW] Assigned task {task_id} to {agent_id}")
        return True

    def start_task(self, workflow_id: str, task_id: str) -> bool:
        """Mark a task as in progress."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        task = workflow.get_task(task_id)
        if not task:
            return False

        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()
        logger.info(f"[WORKFLOW] Task {task_id} started")
        return True

    def complete_task(
        self, workflow_id: str, task_id: str, result: dict[str, Any]
    ) -> bool:
        """Mark a task as completed with result."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        task = workflow.get_task(task_id)
        if not task:
            return False

        task.status = TaskStatus.COMPLETED
        task.result = result
        task.completed_at = datetime.utcnow()
        logger.info(f"[WORKFLOW] Task {task_id} completed")

        # Check if workflow is complete
        if workflow.is_complete():
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            logger.info(f"[WORKFLOW] Workflow {workflow_id} completed")

        return True

    def fail_task(self, workflow_id: str, task_id: str, error: str) -> bool:
        """Mark a task as failed."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        task = workflow.get_task(task_id)
        if not task:
            return False

        task.status = TaskStatus.FAILED
        task.error = error
        task.completed_at = datetime.utcnow()
        logger.error(f"[WORKFLOW] Task {task_id} failed: {error}")

        # Check if workflow has failed
        if workflow.is_failed():
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.utcnow()
            logger.error(f"[WORKFLOW] Workflow {workflow_id} failed")

        return True

    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        workflow.status = WorkflowStatus.PAUSED
        logger.info(f"[WORKFLOW] Workflow {workflow_id} paused")
        return True

    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        if workflow.status != WorkflowStatus.PAUSED:
            logger.warning(f"[WORKFLOW] Workflow {workflow_id} not paused")
            return False

        workflow.status = WorkflowStatus.RUNNING
        logger.info(f"[WORKFLOW] Workflow {workflow_id} resumed")
        return True

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.utcnow()
        logger.info(f"[WORKFLOW] Workflow {workflow_id} cancelled")
        return True

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def get_active_workflow(self) -> Workflow | None:
        """Get the currently active workflow."""
        if self._active_workflow:
            return self._workflows.get(self._active_workflow)
        return None

    def list_workflows(self) -> list[Workflow]:
        """List all workflows."""
        return list(self._workflows.values())
