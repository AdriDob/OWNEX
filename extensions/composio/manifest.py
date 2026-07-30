from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="composio",
    name="Composio Toolkit",
    version="1.0.0",
    description="1000+ toolkits for AI agents. Gives every OWNEX agent instant "
    "access to GitHub, Slack, Gmail, Jira, Linear, Notion, and hundreds "
    "more tools with managed authentication, sandboxed execution, "
    "and MCP-compatible interfaces.",
    author="OWNEX",
    icon="Wrench",
    capabilities=[
        Capability(
            domain="toolkit_access",
            name="Toolkit Access",
            description="Access 1000+ third-party toolkits for agent actions",
        ),
        Capability(
            domain="auth_management",
            name="Auth Management",
            description="Managed OAuth and API key storage for all integrations",
        ),
        Capability(
            domain="action_execution",
            name="Action Execution",
            description="Execute actions on external platforms with sandboxing",
        ),
    ],
    hooks={
        "agent_action": "composio.hooks.on_agent_action",
        "tool_discovery": "composio.hooks.on_tool_discovery",
    },
    providers=["composio_toolset"],
    hot_reloadable=False,
    requires_core="5.0.0",
)
