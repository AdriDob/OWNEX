"""OWNEX OMEGA Workflow System.

Core workflow execution engine with departmental handoffs.
"""

from .engine import TaskStatus, Workflow, WorkflowEngine, WorkflowStatus, WorkflowTask
from .handoff import Handoff, HandoffCondition, HandoffManager, HandoffStatus
from .mvp_workflows import (
    create_bug_fix_workflow,
    create_feature_development_workflow,
    create_revenue_opportunity_workflow,
    get_mvp_workflow_examples,
)
from .orchestrator import WorkflowOrchestrator

__all__ = [
    # Engine
    "Workflow",
    "WorkflowEngine",
    "WorkflowStatus",
    "WorkflowTask",
    "TaskStatus",
    # Handoff
    "Handoff",
    "HandoffCondition",
    "HandoffManager",
    "HandoffStatus",
    # Orchestrator
    "WorkflowOrchestrator",
    # MVP Workflows
    "create_feature_development_workflow",
    "create_bug_fix_workflow",
    "create_revenue_opportunity_workflow",
    "get_mvp_workflow_examples",
]
