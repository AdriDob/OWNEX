from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContractField:
    """Schema for a single input or output field of a capability."""

    name: str = ""
    type: str = "string"  # string | number | boolean | object | array | any
    description: str = ""
    required: bool = False
    default: Any = None
    enum: list[str] | None = None


@dataclass
class ContractEvent:
    """An event that the capability publishes or consumes."""

    event_type: str = ""
    description: str = ""
    direction: str = "publishes"  # publishes | consumes


@dataclass
class ContractPermission:
    """Permission required for this capability."""

    resource: str = ""
    action: str = ""  # read | write | execute | admin


@dataclass
class CapabilityContract:
    """Self-describing contract for a capability.

    Every capability registers one of these so that:
    - COPILOT knows how to invoke it
    - The Documentation Generator can auto-generate the manual
    - The Validator can check inputs/outputs at compile time
    - The Runtime knows timeout, retry, and rollback behaviour
    """

    name: str = ""
    version: str = "0.1.0"
    author: str = "orion"
    description: str = ""
    capability: str = ""  # matches CapabilityRegistry key
    category: str = "general"
    tags: list[str] = field(default_factory=list)

    # ── Configuration ────────────────────────────────────────────
    config_schema: dict[str, Any] = field(default_factory=dict)
    config_example: dict[str, Any] = field(default_factory=dict)

    # ── Permissions ──────────────────────────────────────────────
    permissions: list[ContractPermission] = field(default_factory=list)

    # ── Events ───────────────────────────────────────────────────
    events_published: list[ContractEvent] = field(default_factory=list)
    events_consumed: list[ContractEvent] = field(default_factory=list)

    # ── Dependencies ─────────────────────────────────────────────
    dependencies: list[str] = field(default_factory=list)

    # ── Runtime behaviour ────────────────────────────────────────
    timeout_ms: int = 60000
    retry_count: int = 0
    retry_delay_ms: int = 1000
    rollback_strategy: str = "none"  # none | restore | compensate

    # ── I/O ──────────────────────────────────────────────────────
    inputs: list[ContractField] = field(default_factory=list)
    outputs: list[ContractField] = field(default_factory=list)

    # ── Documentation ────────────────────────────────────────────
    usage_examples: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "capability": self.capability,
            "category": self.category,
            "tags": self.tags,
            "config_schema": self.config_schema,
            "config_example": self.config_example,
            "permissions": [{"resource": p.resource, "action": p.action} for p in self.permissions],
            "events_published": [
                {"event_type": e.event_type, "description": e.description} for e in self.events_published
            ],
            "events_consumed": [
                {"event_type": e.event_type, "description": e.description} for e in self.events_consumed
            ],
            "dependencies": self.dependencies,
            "timeout_ms": self.timeout_ms,
            "retry_count": self.retry_count,
            "retry_delay_ms": self.retry_delay_ms,
            "rollback_strategy": self.rollback_strategy,
            "inputs": [
                {
                    "name": i.name,
                    "type": i.type,
                    "description": i.description,
                    "required": i.required,
                    "default": i.default,
                    "enum": i.enum,
                }
                for i in self.inputs
            ],
            "outputs": [
                {
                    "name": o.name,
                    "type": o.type,
                    "description": o.description,
                    "required": o.required,
                    "default": o.default,
                    "enum": o.enum,
                }
                for o in self.outputs
            ],
            "usage_examples": self.usage_examples,
            "notes": self.notes,
        }
