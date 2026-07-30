"""OWNEX OMEGA MVP Workflows — Example workflows for core agents.

Demonstrates the 5-agent MVP in action.
"""

from typing import Any

from cores.agents.types import AgentId
from cores.workflow.engine import WorkflowTask
from cores.workflow.orchestrator import WorkflowOrchestrator


def create_feature_development_workflow(orchestrator: WorkflowOrchestrator, feature_name: str) -> str:
    """Create a feature development workflow (MVP example).

    This workflow demonstrates the 5 core agents:
    1. Orchestrator (coordination)
    2. Coding (implementation)
    3. QA (testing)
    4. Documentation (memory)
    5. Revenue (business value)
    """
    tasks = [
        WorkflowTask(
            id="arch_design",
            name="Architecture Design",
            agent_id=AgentId.ARCHITECTURE,
            description=f"Design architecture for {feature_name}",
        ),
        WorkflowTask(
            id="implement",
            name="Implementation",
            agent_id=AgentId.CODING,
            description=f"Implement {feature_name}",
            dependencies=["arch_design"],
        ),
        WorkflowTask(
            id="test",
            name="Testing",
            agent_id=AgentId.QA,
            description=f"Test {feature_name}",
            dependencies=["implement"],
        ),
        WorkflowTask(
            id="document",
            name="Documentation",
            agent_id=AgentId.DOCUMENTATION,
            description=f"Document {feature_name}",
            dependencies=["test"],
        ),
        WorkflowTask(
            id="revenue_analysis",
            name="Revenue Analysis",
            agent_id=AgentId.REVENUE,
            description=f"Analyze revenue potential of {feature_name}",
            dependencies=["document"],
        ),
    ]

    workflow = orchestrator.create_workflow(
        name=f"Feature Development: {feature_name}",
        description=f"Complete feature development workflow for {feature_name}",
        tasks=tasks,
        metadata={"feature_name": feature_name, "type": "feature_development"},
    )

    return workflow.id


def create_bug_fix_workflow(orchestrator: WorkflowOrchestrator, bug_description: str) -> str:
    """Create a bug fix workflow (MVP example).

    This workflow demonstrates the 5 core agents in bug fixing:
    1. Orchestrator (coordination)
    2. Debug (diagnosis)
    3. Coding (fix)
    4. QA (validation)
    5. Documentation (record)
    """
    tasks = [
        WorkflowTask(
            id="diagnose",
            name="Error Diagnosis",
            agent_id=AgentId.DEBUG,
            description=f"Diagnose: {bug_description}",
        ),
        WorkflowTask(
            id="fix",
            name="Bug Fix",
            agent_id=AgentId.CODING,
            description=f"Fix bug: {bug_description}",
            dependencies=["diagnose"],
        ),
        WorkflowTask(
            id="validate",
            name="Validation",
            agent_id=AgentId.QA,
            description=f"Validate fix for: {bug_description}",
            dependencies=["fix"],
        ),
        WorkflowTask(
            id="record",
            name="Documentation",
            agent_id=AgentId.DOCUMENTATION,
            description=f"Record bug fix: {bug_description}",
            dependencies=["validate"],
        ),
    ]

    workflow = orchestrator.create_workflow(
        name=f"Bug Fix: {bug_description}",
        description=f"Bug fix workflow for: {bug_description}",
        tasks=tasks,
        metadata={"bug_description": bug_description, "type": "bug_fix"},
    )

    return workflow.id


def create_revenue_opportunity_workflow(orchestrator: WorkflowOrchestrator, opportunity_description: str) -> str:
    """Create a revenue opportunity workflow (MVP example).

    This workflow demonstrates the 5 core agents in revenue generation:
    1. Orchestrator (coordination)
    2. Research (investigation)
    3. Product (definition)
    4. Coding (implementation)
    5. Revenue (monetization)
    """
    tasks = [
        WorkflowTask(
            id="research",
            name="Market Research",
            agent_id=AgentId.RESEARCH,
            description=f"Research: {opportunity_description}",
        ),
        WorkflowTask(
            id="define",
            name="Product Definition",
            agent_id=AgentId.PRODUCT,
            description=f"Define product for: {opportunity_description}",
            dependencies=["research"],
        ),
        WorkflowTask(
            id="implement",
            name="Implementation",
            agent_id=AgentId.CODING,
            description=f"Implement: {opportunity_description}",
            dependencies=["define"],
        ),
        WorkflowTask(
            id="monetize",
            name="Monetization",
            agent_id=AgentId.REVENUE,
            description=f"Monetize: {opportunity_description}",
            dependencies=["implement"],
        ),
    ]

    workflow = orchestrator.create_workflow(
        name=f"Revenue Opportunity: {opportunity_description}",
        description=f"Revenue opportunity workflow for: {opportunity_description}",
        tasks=tasks,
        metadata={"opportunity_description": opportunity_description, "type": "revenue_opportunity"},
    )

    return workflow.id


def get_mvp_workflow_examples() -> dict[str, Any]:
    """Get MVP workflow examples documentation."""
    return {
        "feature_development": {
            "name": "Feature Development",
            "description": "Complete feature development workflow",
            "agents": ["Architecture", "Coding", "QA", "Documentation", "Revenue"],
            "steps": [
                "Architecture Design",
                "Implementation",
                "Testing",
                "Documentation",
                "Revenue Analysis",
            ],
        },
        "bug_fix": {
            "name": "Bug Fix",
            "description": "Bug fix workflow",
            "agents": ["Debug", "Coding", "QA", "Documentation"],
            "steps": [
                "Error Diagnosis",
                "Bug Fix",
                "Validation",
                "Documentation",
            ],
        },
        "revenue_opportunity": {
            "name": "Revenue Opportunity",
            "description": "Revenue opportunity workflow",
            "agents": ["Research", "Product", "Coding", "Revenue"],
            "steps": [
                "Market Research",
                "Product Definition",
                "Implementation",
                "Monetization",
            ],
        },
    }
