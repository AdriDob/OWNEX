from __future__ import annotations

from core.extension.manifest import ExtensionManifest
from core.extension.capabilities import Capability

manifest = ExtensionManifest(
    id="mcp",
    name="MCP Bridge",
    version="1.0.0",
    description="Model Context Protocol bridge. "
                "Connects OWNEX to any MCP-compatible server for tool access, "
                "file operations, web search, and external data sources.",
    author="OWNEX",
    icon="Plug",
    capabilities=[
        Capability(
            id="mcp_tools",
            name="MCP Tools",
            description="Access tools from any MCP server",
        ),
        Capability(
            id="mcp_resources",
            name="MCP Resources",
            description="Read external resources via MCP",
        ),
        Capability(
            id="mcp_prompts",
            name="MCP Prompts",
            description="Use MCP prompt templates",
        ),
    ],
    hooks={},
    dependencies=["core/event_bus", "core/interfaces"],
    providers=["mcp_bridge"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
