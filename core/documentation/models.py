"""Documentation models — structured metadata for every ORION module.

Each module self-describes via these models so the Documentation Generator
can produce the ORION_MANUAL/ tree without hand-written markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CapabilityDoc:
    """A capability the module provides."""

    name: str
    description: str = ""
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass
class EventDoc:
    """An event the module publishes or consumes."""

    event_type: str
    direction: str = "published"  # "published" | "consumed"
    payload_schema: str = ""
    description: str = ""


@dataclass
class ConfigDoc:
    """A configuration option."""

    key: str
    type: str = "str"
    default: str = ""
    description: str = ""
    required: bool = False


@dataclass
class ApiDoc:
    """An API endpoint or method."""

    method: str  # "GET" | "POST" | "DELETE" | "method" for Python methods
    path: str = ""
    description: str = ""
    parameters: list[dict[str, str]] = field(default_factory=list)


@dataclass
class IntegrationDoc:
    """An external integration (tool, API, service)."""

    name: str
    category: str = ""  # "exchange" | "blockchain" | "ai" | "infrastructure" | ...
    description: str = ""
    events_published: list[str] = field(default_factory=list)
    events_consumed: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass
class CommandDoc:
    """A CLI command available in the module."""

    command: str
    description: str = ""
    arguments: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ScreenDoc:
    """A frontend screen or view."""

    name: str
    route: str = ""
    description: str = ""
    widgets: list[str] = field(default_factory=list)


@dataclass
class ModuleDoc:
    """Complete self-description of an ORION module.

    Every module in the system registers one of these.
    """

    id: str
    name: str
    category: str = ""  # "core" | "app" | "integration" | "tool" | ...
    version: str = "1.0.0"
    description: str = ""
    capabilities: list[CapabilityDoc] = field(default_factory=list)
    events_published: list[EventDoc] = field(default_factory=list)
    events_consumed: list[EventDoc] = field(default_factory=list)
    config_options: list[ConfigDoc] = field(default_factory=list)
    apis: list[ApiDoc] = field(default_factory=list)
    integrations: list[IntegrationDoc] = field(default_factory=list)
    commands: list[CommandDoc] = field(default_factory=list)
    screens: list[ScreenDoc] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    examples: list[dict[str, str]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    docs_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "version": self.version,
            "description": self.description,
            "capabilities": [{"name": c.name, "description": c.description} for c in self.capabilities],
            "events_published": [
                {"event_type": e.event_type, "description": e.description} for e in self.events_published
            ],
            "events_consumed": [
                {"event_type": e.event_type, "description": e.description} for e in self.events_consumed
            ],
            "config_options": [{"key": c.key, "type": c.type, "default": c.default} for c in self.config_options],
            "apis": [{"method": a.method, "path": a.path, "description": a.description} for a in self.apis],
            "integrations": [{"name": i.name, "category": i.category} for i in self.integrations],
            "commands": [{"command": c.command, "description": c.description} for c in self.commands],
            "screens": [{"name": s.name, "route": s.route} for s in self.screens],
            "dependencies": self.dependencies,
            "permissions": self.permissions,
            "tags": self.tags,
        }
