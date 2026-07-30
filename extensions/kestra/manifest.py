from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="kestra",
    name="Kestra Orchestration",
    version="1.0.0",
    description="Event-driven orchestration and scheduling for mission-critical "
    "workflows. Declare OWNEX workflows as YAML, trigger by event or "
    "schedule, with built-in retries, error handling, and observability. "
    "Replaces APScheduler for production-grade scheduling.",
    author="OWNEX",
    icon="Timer",
    capabilities=[
        Capability(domain="flow_execution",
            name="Flow Execution",
            description="Execute Kestra flows from OWNEX events",
        ),
        Capability(domain="flow_scheduling",
            name="Flow Scheduling",
            description="Schedule recurring OWNEX tasks via Kestra",
        ),
        Capability(domain="event_trigger",
            name="Event Trigger",
            description="Trigger Kestra flows from EventBus events",
        ),
    ],
    hooks={
        "flow_trigger": "kestra.hooks.on_flow_trigger",
        "schedule_event": "kestra.hooks.on_schedule_event",
    },
    providers=["kestra_orchestrator"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
