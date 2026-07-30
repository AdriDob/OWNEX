from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="n8n",
    name="n8n Workflow Automation",
    version="1.0.0",
    description="Visual workflow automation with 400+ integrations and native "
    "AI capabilities. n8n serves as the visual orchestration layer "
    "for OWNEX — every sensor trigger, agent action, and notification "
    "can be wired into a visual workflow with AI nodes.",
    author="OWNEX",
    icon="Workflow",
    capabilities=[
        Capability(
            domain="workflow_trigger",
            name="Workflow Trigger",
            description="Trigger n8n workflows from OWNEX events",
        ),
        Capability(
            domain="workflow_execution",
            name="Workflow Execution",
            description="Execute n8n workflows with custom payloads",
        ),
        Capability(
            domain="webhook_bridge",
            name="Webhook Bridge",
            description="Bridge OWNEX EventBus events to n8n webhooks",
        ),
    ],
    hooks={
        "eventbus_event": "n8n.hooks.on_eventbus_event",
        "workflow_request": "n8n.hooks.on_workflow_request",
    },
    providers=["n8n_bridge"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
