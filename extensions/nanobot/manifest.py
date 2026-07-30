from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="nanobot",
    name="Nanobot Agent Frontend",
    version="1.0.0",
    description="Lightweight multi-agent chat interface with file upload, "
    "model switching, and full conversation history. Provides the "
    "human-facing chat UI for OWNEX, letting the user interact with "
    "any agent, switch models mid-conversation, and upload files. "
    "Supports MCP tools and custom agent personas.",
    author="OWNEX",
    icon="MessageSquare",
    capabilities=[
        Capability(domain="chat_interface",
            name="Chat Interface",
            description="Web UI for multi-model, multi-agent conversations",
        ),
        Capability(domain="file_upload",
            name="File Upload",
            description="Upload images, code, PDFs, and archives to conversations",
        ),
        Capability(domain="agent_switching",
            name="Agent Switching",
            description="Switch between specialized OWNEX agents mid-conversation",
        ),
        Capability(domain="mcp_integration",
            name="MCP Integration",
            description="Expose OWNEX capabilities as MCP tools to Nanobot",
        ),
    ],
    hooks={
        "chat_request": "nanobot.hooks.on_chat_request",
        "agent_switch": "nanobot.hooks.on_agent_switch",
    },
    providers=["nanobot_frontend"],
    hot_reloadable=False,
    requires_core="5.0.0",
)
