"""Capability registry module."""

from __future__ import annotations

from core.capabilities.registry import (
    CapabilityEntry,
    CapabilityRegistry,
    get_capability_registry,
    reset_capability_registry,
)

__all__ = ["CapabilityEntry", "CapabilityRegistry", "get_capability_registry", "reset_capability_registry"]
