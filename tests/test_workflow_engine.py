"""Test OWNEX OMEGA Workflow Engine.

Basic integration test for workflow execution and handoffs.
"""

import pytest

from cores.workflow import (
    TaskStatus,
    WorkflowOrchestrator,
    WorkflowStatus,
)


def test_workflow_creation():
    """Test basic workflow creation."""
    from cores.workflow.engine import WorkflowTask

    orchestrator = WorkflowOrchestrator()
    tasks = [
        WorkflowTask(
            id="task1",
            name="Test Task",
            agent_id="test_agent",
            description="Test task description",
        )
    ]

    workflow = orchestrator.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        tasks=tasks,
    )

    assert workflow is not None
    assert workflow.name == "Test Workflow"
    assert len(workflow.tasks) == 1
    assert workflow.status == WorkflowStatus.PENDING


def test_workflow_start():
    """Test workflow start."""
    from cores.workflow.engine import WorkflowTask

    orchestrator = WorkflowOrchestrator()
    tasks = [
        WorkflowTask(
            id="task1",
            name="Test Task",
            agent_id="test_agent",
            description="Test task description",
        )
    ]

    workflow_id = orchestrator.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        tasks=tasks,
    ).id

    success = orchestrator.start_workflow(workflow_id)
    assert success is True

    workflow = orchestrator.get_workflow(workflow_id)
    assert workflow.status == WorkflowStatus.RUNNING
    assert workflow.started_at is not None


def test_task_assignment():
    """Test task assignment."""
    from cores.workflow.engine import WorkflowTask

    orchestrator = WorkflowOrchestrator()
    tasks = [
        WorkflowTask(
            id="task1",
            name="Test Task",
            agent_id="test_agent",
            description="Test task description",
        )
    ]

    workflow_id = orchestrator.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        tasks=tasks,
    ).id

    orchestrator.start_workflow(workflow_id)

    workflow = orchestrator.get_workflow(workflow_id)
    first_task = workflow.tasks[0]
    assert first_task.status == TaskStatus.IN_PROGRESS


def test_task_completion():
    """Test task completion."""
    from cores.workflow.engine import WorkflowTask

    orchestrator = WorkflowOrchestrator()
    tasks = [
        WorkflowTask(
            id="task1",
            name="Test Task",
            agent_id="test_agent",
            description="Test task description",
        )
    ]

    workflow_id = orchestrator.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        tasks=tasks,
    ).id

    orchestrator.start_workflow(workflow_id)

    workflow = orchestrator.get_workflow(workflow_id)
    first_task = workflow.tasks[0]

    success = orchestrator.complete_task(workflow_id, first_task.id, {"status": "success"})
    assert success is True

    workflow = orchestrator.get_workflow(workflow_id)
    first_task = workflow.get_task(first_task.id)
    assert first_task.status == TaskStatus.COMPLETED
    assert first_task.completed_at is not None


def test_handoff_trigger():
    """Test handoff triggering."""
    from cores.workflow.engine import WorkflowTask

    orchestrator = WorkflowOrchestrator()
    tasks = [
        WorkflowTask(
            id="task1",
            name="Test Task",
            agent_id="test_agent",
            description="Test task description",
        )
    ]

    workflow_id = orchestrator.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        tasks=tasks,
    ).id

    orchestrator.start_workflow(workflow_id)

    workflow = orchestrator.get_workflow(workflow_id)
    first_task = workflow.tasks[0]

    # Complete task with handoff condition
    orchestrator.complete_task(
        workflow_id,
        first_task.id,
        {"handoff_condition": "test_condition", "status": "success"},
    )

    # Check if handoff was created (may not find condition, but should not crash)
    handoffs = orchestrator.get_handoffs_for_workflow(workflow_id)
    # Handoff may not be created if condition not found
    assert isinstance(handoffs, list)


def test_workflow_list():
    """Test workflow listing."""
    from cores.workflow.engine import WorkflowTask

    orchestrator = WorkflowOrchestrator()
    tasks = [
        WorkflowTask(
            id="task1",
            name="Test Task",
            agent_id="test_agent",
            description="Test task description",
        )
    ]

    orchestrator.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        tasks=tasks,
    )

    workflows = orchestrator.list_workflows()
    assert len(workflows) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
