"""Introspector — auto-discovers module metadata from live ORION registries.

Reads CapabilityRegistry, Events.ALL, API routers, and other live sources
to build ModuleDoc entries without manual declaration.
"""

from __future__ import annotations

import logging

from core.documentation.models import (
    ApiDoc,
    CapabilityDoc,
    CommandDoc,
    ConfigDoc,
    EventDoc,
    IntegrationDoc,
    ModuleDoc,
)
from core.documentation.registrar import register_module

logger = logging.getLogger("orion.core.documentation.introspect")


def introspect_capability_registry() -> list[CapabilityDoc]:
    """Read every registered capability and return as CapabilityDoc list."""
    try:
        from core.capabilities.registry import get_capability_registry

        reg = get_capability_registry()
        caps: list[CapabilityDoc] = []
        for cap_name in reg.list_capabilities():
            entries = reg.find(cap_name)
            for entry in entries:
                caps.append(CapabilityDoc(name=cap_name, description=entry.description, parameters=entry.metadata))
        return caps
    except Exception as exc:
        logger.debug("CapabilityRegistry introspection failed: %s", exc)
        return []


def introspect_event_types() -> list[EventDoc]:
    """Read all event type constants and return as EventDoc list."""
    try:
        from core.events.types import Events

        events: list[EventDoc] = []
        for attr_name in dir(Events):
            if attr_name.startswith("_"):
                continue
            val = getattr(Events, attr_name)
            if isinstance(val, str) and ":" in val:
                events.append(EventDoc(event_type=val, direction="published"))
        return events
    except Exception as exc:
        logger.debug("Event types introspection failed: %s", exc)
        return []


def introspect_api_routers() -> list[ApiDoc]:
    """Read registered FastAPI routers and extract endpoint metadata.

    Returns a representative list of known API endpoints.
    """
    apis: list[ApiDoc] = []

    # Core API endpoints (from core/api/routers.py)
    core_endpoints = [
        ("GET", "/api/core/health", "Unified health status"),
        ("GET", "/api/core/health/run", "Run all health checks"),
        ("GET", "/api/core/health/history", "Health snapshot history"),
        ("GET", "/api/core/health/checks", "List registered health checks"),
        ("GET", "/api/core/extensions", "List all extensions"),
        ("GET", "/api/core/secrets", "List secret keys"),
        ("GET", "/api/core/secrets/health", "Secrets backend health"),
        ("GET", "/api/core/capabilities", "List all capabilities"),
        ("GET", "/api/core/integrations", "List all integrations"),
        ("GET", "/api/core/decisions", "Decision journal"),
        ("GET", "/api/core/knowledge/nodes", "Find knowledge graph nodes"),
        ("GET", "/api/core/knowledge/nodes/{node_id}", "Get a KG node"),
        ("POST", "/api/core/knowledge/nodes", "Add a KG node"),
        ("DELETE", "/api/core/knowledge/nodes/{node_id}", "Delete a KG node"),
        ("GET", "/api/core/knowledge/nodes/{node_id}/neighbors", "Get KG node neighbors"),
        ("GET", "/api/core/knowledge/path", "Find paths between KG nodes"),
        ("GET", "/api/core/knowledge/subgraph", "Get KG subgraph"),
        ("POST", "/api/core/knowledge/edges", "Add a KG edge"),
        ("GET", "/api/core/knowledge/stats", "KG statistics"),
        ("GET", "/api/core/version", "ORION version info"),
    ]
    for method, path, desc in core_endpoints:
        apis.append(ApiDoc(method=method, path=path, description=desc))

    # CATEYE API endpoints (from api/routers/)
    cateye_endpoints = [
        ("GET", "/api/health", "System health"),
        ("GET", "/api/targets", "List targets"),
        ("POST", "/api/targets", "Create target"),
        ("GET", "/api/targets/{id}", "Get target"),
        ("POST", "/api/targets/{id}/scan", "Trigger target scan"),
        ("GET", "/api/findings", "List findings"),
        ("POST", "/api/findings", "Create finding"),
        ("GET", "/api/findings/{id}", "Get finding"),
        ("GET", "/api/reports", "List reports"),
        ("POST", "/api/reports", "Create or generate report"),
        ("GET", "/api/evidence", "List evidence"),
        ("POST", "/api/evidence/upload", "Upload evidence"),
        ("GET", "/api/events/history", "Event history"),
        ("GET", "/api/system/status", "System status"),
    ]
    for method, path, desc in cateye_endpoints:
        apis.append(ApiDoc(method=method, path=path, description=desc, parameters=[{"app": "cateye"}]))

    return apis


def introspect_integrations() -> list[IntegrationDoc]:
    """Read the IntegrationRegistry and return as IntegrationDoc list."""
    try:
        from core.integrations import init_integration_registry

        registry = init_integration_registry()
        summary = registry.summary()
        integrations: list[IntegrationDoc] = []
        for name, info in summary.get("integrations", {}).items():
            integrations.append(
                IntegrationDoc(name=name, category=info.get("category", ""), description=info.get("description", ""))
            )
        return integrations
    except Exception as exc:
        logger.debug("Integration introspection failed: %s", exc)
        return []


def auto_register_core_modules() -> int:
    """Register all core ORION modules automatically.

    Returns the number of modules registered.
    """
    count_before = len(__import__("core.documentation.registrar", fromlist=["list_all_modules"]).list_all_modules())

    # 1. Event Bus
    register_module(
        ModuleDoc(
            id="event_bus",
            name="Event Bus",
            category="core",
            description="Namespace-aware event bus with SQLite persistence and legacy CATEYE bridge.",
            capabilities=[CapabilityDoc(name="publish_events", description="Publish events to all subscribers")],
            events_published=[EventDoc(event_type="*", direction="published", description="All system events")],
            config_options=[
                ConfigDoc(key="persist", type="bool", default="True", description="Enable SQLite persistence"),
                ConfigDoc(key="bridge", type="bool", default="True", description="Bridge to legacy EventBus"),
            ],
        )
    )

    # 2. Event Store
    register_module(
        ModuleDoc(
            id="event_store",
            name="Event Store",
            category="core",
            description="SQLite-backed persistent event store with replay, search, and time-window queries.",
            apis=[
                ApiDoc(method="method", path="store()", description="Persist an event envelope"),
                ApiDoc(method="method", path="replay()", description="Replay events in a time window"),
                ApiDoc(method="method", path="search()", description="Search events by type/source/correlation"),
                ApiDoc(method="method", path="get_stats()", description="Event store aggregate statistics"),
                ApiDoc(method="method", path="prune()", description="Delete old events"),
            ],
        )
    )

    # 3. Knowledge Graph
    register_module(
        ModuleDoc(
            id="knowledge_graph",
            name="Knowledge Graph",
            category="core",
            description="Unified graph connecting all ORION entities — targets, findings, reports, decisions, wallets, exchanges.",
            capabilities=[
                CapabilityDoc(name="query_graph", description="Query entities and relationships via API"),
            ],
            apis=[
                ApiDoc(method="method", path="add_node()", description="Add or upsert a node"),
                ApiDoc(method="method", path="get_node()", description="Get a node by ID"),
                ApiDoc(method="method", path="get_neighbors()", description="Get neighboring nodes"),
                ApiDoc(method="method", path="get_path()", description="Find paths between nodes"),
                ApiDoc(method="method", path="get_subgraph()", description="Get subgraph centered on a node"),
                ApiDoc(method="method", path="get_stats()", description="Graph aggregate statistics"),
                ApiDoc(method="method", path="record_finding()", description="Record a finding with target edge"),
                ApiDoc(method="method", path="record_decision()", description="Record a COPILOT decision"),
            ],
            events_consumed=[
                EventDoc(event_type="finding:*", direction="consumed", description="Auto-record findings as nodes"),
                EventDoc(event_type="target:*", direction="consumed", description="Auto-record targets as nodes"),
            ],
        )
    )

    # 4. Capability Registry
    register_module(
        ModuleDoc(
            id="capability_registry",
            name="Capability Registry",
            category="core",
            description="Central registry where modules register their capabilities. Enables COPILOT discovery.",
            apis=[
                ApiDoc(method="method", path="register()", description="Register a capability"),
                ApiDoc(method="method", path="find()", description="Find modules providing a capability"),
                ApiDoc(method="method", path="has_capability()", description="Check if a capability exists"),
                ApiDoc(method="method", path="list_capabilities()", description="List all registered capabilities"),
            ],
        )
    )

    # 5. COPILOT
    register_module(
        ModuleDoc(
            id="copilot",
            name="COPILOT",
            category="core",
            description="Senior Copilot Agent — the transversal reasoning and quality center of ORION. Analyzes findings, creates plans, reviews reports, audits system health, and makes decisions.",
            capabilities=[
                CapabilityDoc(name="analyze_finding", description="Analyze findings with Evidence Graph context"),
                CapabilityDoc(name="create_plan", description="Create multi-step investigation plans"),
                CapabilityDoc(name="execute_plan", description="Execute investigation plan steps"),
                CapabilityDoc(name="pre_report_review", description="Run pre-report quality checklist"),
                CapabilityDoc(name="audit_system", description="Run all registered system auditors"),
                CapabilityDoc(name="make_decision", description="Decision Engine: standardized decisions from events"),
            ],
            events_published=[
                EventDoc(
                    event_type="copilot:analysis:completed", direction="published", description="Finding analysis done"
                ),
                EventDoc(
                    event_type="copilot:plan:created", direction="published", description="Investigation plan created"
                ),
                EventDoc(event_type="copilot:plan:executed", direction="published", description="Plan executed"),
                EventDoc(
                    event_type="copilot:review:completed", direction="published", description="Pre-report review done"
                ),
                EventDoc(event_type="copilot:audit:completed", direction="published", description="System audit done"),
                EventDoc(event_type="copilot:decision", direction="published", description="Decision Engine output"),
            ],
            events_consumed=[
                EventDoc(event_type="finding:*", direction="consumed", description="Trigger analysis/decisions"),
                EventDoc(event_type="system:*", direction="consumed", description="Trigger system audit decisions"),
            ],
            dependencies=[
                "core.events.types",
                "core.events.correlation",
                "core.events.store",
                "core.capabilities.registry",
                "core.knowledge.graph",
                "core.evidence_graph.graph",
                "core.memory.store",
                "core.copilot.*",
            ],
        )
    )

    # 6. Correlation ID
    register_module(
        ModuleDoc(
            id="correlation_id",
            name="Correlation ID",
            category="core",
            description="Contextvar-based trace ID propagation through end-to-end workflows.",
            apis=[
                ApiDoc(
                    method="method",
                    path="get_or_create_correlation_id()",
                    description="Get or generate a correlation ID",
                ),
                ApiDoc(
                    method="method", path="with_correlation_id()", description="Context manager to set correlation ID"
                ),
                ApiDoc(
                    method="method",
                    path="with_new_correlation_id()",
                    description="Generate a fresh correlation ID in context",
                ),
            ],
        )
    )

    # 7. Event Types
    register_module(
        ModuleDoc(
            id="event_types",
            name="Event Types",
            category="core",
            description="Centralized event type constants (40+) and standardized EventEnvelope/Decision data structures.",
            apis=[
                ApiDoc(method="class", path="Events", description="All event type constants as class attributes"),
                ApiDoc(
                    method="dataclass",
                    path="EventEnvelope",
                    description="Standard envelope with correlation_id, payload, duration",
                ),
                ApiDoc(method="dataclass", path="Decision", description="COPILOT Decision Engine output"),
            ],
        )
    )

    # 8. Health Center
    register_module(
        ModuleDoc(
            id="health_center",
            name="Health Center",
            category="core",
            description="Unified health monitoring system. Checks system, background, and integration health. Green/yellow/red status with snapshots.",
            capabilities=[
                CapabilityDoc(name="health_check", description="Run health checks and return status"),
            ],
            apis=[
                ApiDoc(method="GET", path="/api/core/health", description="Unified health status"),
                ApiDoc(method="POST", path="/api/core/health/run", description="Run all health checks"),
                ApiDoc(method="GET", path="/api/core/health/history", description="Health snapshot history"),
                ApiDoc(method="GET", path="/api/core/health/checks", description="List registered health checks"),
            ],
        )
    )

    # 9. Secrets Manager
    register_module(
        ModuleDoc(
            id="secrets_manager",
            name="Secrets Manager",
            category="core",
            description="AES-256-GCM encrypted secrets storage with IdentityVault bridge and env var fallback.",
            apis=[
                ApiDoc(method="GET", path="/api/core/secrets", description="List secret keys"),
                ApiDoc(method="GET", path="/api/core/secrets/{key}", description="Get a secret value"),
                ApiDoc(method="PUT", path="/api/core/secrets/{key}", description="Store a secret"),
                ApiDoc(method="DELETE", path="/api/core/secrets/{key}", description="Delete a secret"),
            ],
            permissions=["vault_access"],
        )
    )

    # 10. Extension SDK
    register_module(
        ModuleDoc(
            id="extension_sdk",
            name="Extension SDK",
            category="core",
            description="Load, unload, and manage extensions with hooks, capabilities, settings, and failure isolation.",
            apis=[
                ApiDoc(method="GET", path="/api/core/extensions", description="List all extensions"),
                ApiDoc(method="POST", path="/api/core/extensions/{id}/load", description="Load an extension"),
                ApiDoc(method="POST", path="/api/core/extensions/{id}/unload", description="Unload an extension"),
                ApiDoc(method="GET", path="/api/core/hooks", description="List all hooks and handlers"),
            ],
        )
    )

    # 11. Integration Center
    register_module(
        ModuleDoc(
            id="integration_center",
            name="Integration Center",
            category="core",
            description="Discovers and checks status of 23+ built-in integrations across 7 categories.",
            integrations=introspect_integrations(),
        )
    )

    # 12. Decision Journal
    register_module(
        ModuleDoc(
            id="decision_journal",
            name="Decision Journal",
            category="core",
            description="Persistent SQLite journal of every COPILOT decision with outcome tracking.",
            apis=[
                ApiDoc(method="GET", path="/api/core/decisions", description="Query decisions"),
                ApiDoc(method="GET", path="/api/core/decisions/{id}", description="Get a decision"),
                ApiDoc(method="POST", path="/api/core/decisions/{id}/outcome", description="Record decision outcome"),
            ],
        )
    )

    # 13. Scheduler
    register_module(
        ModuleDoc(
            id="scheduler",
            name="Scheduler",
            category="core",
            description="Adaptive scheduler for automated pipeline stages: DISCOVER, RECON, HYPOTHESIS, VALIDATE, REPORT.",
            config_options=[
                ConfigDoc(key="cooldown", type="int", default="3600", description="Seconds between runs per target"),
                ConfigDoc(key="batch_size", type="int", default="5", description="Targets per batch"),
            ],
        )
    )

    # 14. Evidence Graph
    register_module(
        ModuleDoc(
            id="evidence_graph",
            name="Evidence Graph",
            category="core",
            description="Persistent graph of for/against/neutral evidence per hypothesis. Integrates with COPILOT and feedback pipeline.",
            apis=[
                ApiDoc(method="method", path="get_evidence()", description="Get for/against evidence for a hypothesis"),
                ApiDoc(method="method", path="get_balance()", description="Net evidence balance score"),
                ApiDoc(
                    method="method", path="record_from_verdict()", description="Record evidence from validation verdict"
                ),
                ApiDoc(
                    method="method", path="record_from_copilot()", description="Record evidence from COPILOT analysis"
                ),
            ],
        )
    )

    # 15. Unified Memory
    register_module(
        ModuleDoc(
            id="unified_memory",
            name="Unified Memory",
            category="core",
            description="SQLAlchemy-backed persistent memory with namespaces, tags, priority sorting, and embedding storage.",
            apis=[
                ApiDoc(method="method", path="store()", description="Store a memory entry"),
                ApiDoc(method="method", path="query()", description="Search memory by content/tags"),
                ApiDoc(method="method", path="get()", description="Retrieve a specific entry"),
                ApiDoc(method="method", path="count()", description="Count entries by namespace"),
            ],
        )
    )

    # 16. CopilotEventPublisher
    register_module(
        ModuleDoc(
            id="copilot_publisher",
            name="Copilot Event Publisher",
            category="core",
            description="Thin publisher layer that decouples COPILOT from EventBus. If transport changes (Kafka, Redis), only this file changes.",
            events_published=[
                EventDoc(event_type="copilot:analysis:completed", direction="published"),
                EventDoc(event_type="copilot:plan:created", direction="published"),
                EventDoc(event_type="copilot:plan:executed", direction="published"),
                EventDoc(event_type="copilot:review:completed", direction="published"),
                EventDoc(event_type="copilot:audit:completed", direction="published"),
                EventDoc(event_type="copilot:recommendation", direction="published"),
                EventDoc(event_type="copilot:decision", direction="published"),
                EventDoc(event_type="copilot:heartbeat", direction="published"),
            ],
        )
    )

    # 17. Hermes Automation Agent
    register_module(
        ModuleDoc(
            id="hermes",
            name="Hermes",
            category="app",
            description="Automation agent with safe mode — 6 commands (backup, status, health, logs, doctor, help). JSONL action logging.",
            commands=[
                CommandDoc(command="--hermes backup", description="Create full ORION backup"),
                CommandDoc(command="--hermes status", description="System status overview"),
                CommandDoc(command="--hermes health", description="Run health checks"),
                CommandDoc(command="--hermes logs", description="View recent logs"),
                CommandDoc(command="--hermes doctor", description="Run diagnostics"),
                CommandDoc(command="--hermes help", description="Command reference"),
            ],
        )
    )

    # 18. Execution Platform
    register_module(
        ModuleDoc(
            id="execution_platform",
            name="Execution Platform",
            category="core",
            description="Universal workflow execution platform. Composed of 17 primitive node types (start, trigger, condition, decision, capability, wait, delay, retry, timeout, parallel, loop, persist, approval, notification, checkpoint, rollback, end). Defines Workflow as a directed graph of Nodes and Edges. Supports intents (user → COPILOT → Workflow), capability contracts, checkpoints, rollbacks, human approvals, and replay from Event Store. Knows nothing about CATEYE/ATLAS/AEGIS — only universal concepts: event, capability, decision, condition, action, state.",
            capabilities=[
                CapabilityDoc(name="execute_workflow", description="Execute a compiled workflow graph"),
                CapabilityDoc(name="validate_workflow", description="Validate a workflow definition for correctness"),
                CapabilityDoc(name="compile_workflow", description="Compile a workflow into an execution graph"),
                CapabilityDoc(
                    name="design_from_intent", description="Design a workflow from a natural language intent"
                ),
                CapabilityDoc(
                    name="validate_graph", description="Structural graph validation (cycles, orphans, reachability)"
                ),
                CapabilityDoc(name="validate_capabilities", description="Capability registry and contract validation"),
                CapabilityDoc(name="validate_permissions", description="Permission and credentials validation"),
                CapabilityDoc(name="validate_timeouts", description="Timeout configuration validation"),
                CapabilityDoc(name="validate_retry", description="Retry policy validation"),
                CapabilityDoc(name="validate_dependencies", description="Dependency resolution validation"),
                CapabilityDoc(name="validate_security", description="Security policy validation"),
                CapabilityDoc(name="estimate_resources", description="Resource and cost estimation"),
                CapabilityDoc(name="validate_documentation", description="Documentation completeness validation"),
                CapabilityDoc(name="build_plan", description="Build an ExecutionPlan from validated workflow"),
            ],
            events_published=[
                EventDoc(
                    event_type="execution:workflow:*", direction="published", description="Workflow lifecycle events"
                ),
                EventDoc(event_type="execution:*", direction="published", description="Execution lifecycle events"),
                EventDoc(event_type="execution:node:*", direction="published", description="Node execution events"),
                EventDoc(event_type="execution:approval:*", direction="published", description="Human approval events"),
                EventDoc(event_type="execution:checkpoint:*", direction="published", description="Checkpoint events"),
                EventDoc(event_type="execution:rollback:*", direction="published", description="Rollback events"),
                EventDoc(event_type="execution:intent:*", direction="published", description="Intent lifecycle events"),
                EventDoc(
                    event_type="execution:metrics:collected", direction="published", description="Execution metrics"
                ),
                EventDoc(
                    event_type="execution:validation:*",
                    direction="published",
                    description="Validation lifecycle events",
                ),
                EventDoc(
                    event_type="execution:plan:created", direction="published", description="Execution plan created"
                ),
            ],
            events_consumed=[
                EventDoc(
                    event_type="copilot:decision",
                    direction="consumed",
                    description="Trigger workflow from COPILOT decision",
                ),
                EventDoc(
                    event_type="copilot:plan:*", direction="consumed", description="Trigger workflow from COPILOT plan"
                ),
            ],
            dependencies=[
                "core.events.types",
                "core.events.event_bus",
                "core.events.store",
                "core.events.correlation",
                "core.capabilities.registry",
                "core.knowledge.graph",
                "core.execution.*",
            ],
        )
    )

    after = len(__import__("core.documentation.registrar", fromlist=["list_all_modules"]).list_all_modules())
    return after - count_before
