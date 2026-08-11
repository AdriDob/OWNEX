"""Capability Registration — wires built-in capability definitions into CapabilityRegistry."""

from core.capabilities.registry import get_capability_registry
from core.engine.capability import BUILTIN_CAPABILITIES, CapabilityEngine


def register_builtin_capabilities() -> int:
    """Register all built-in capabilities with the CapabilityRegistry.

    Called once at startup to populate the registry so modules,
    agents, and COPILOT can discover what the system can do.
    """
    registry = get_capability_registry()
    count = 0
    for cap_id, attrs in BUILTIN_CAPABILITIES.items():
        meta = {
            "providers": attrs.get("providers", []),
            "category": attrs.get("category", ""),
            "estimated_cost": attrs.get("estimated_cost_per_run", 0),
            "requires_user": attrs.get("requires_user", False),
        }
        provider_list = attrs.get("providers", [])
        for provider in provider_list:
            registry.register(
                capability=cap_id,
                module=provider,
                metadata=meta,
                description=attrs.get("description", ""),
            )
            count += 1
    return count


def register_all_capabilities() -> int:
    """Full registration: built-in + engine capabilities."""
    total = register_builtin_capabilities()
    _register_engine_capabilities()
    return total


def _register_engine_capabilities() -> None:
    """Register capabilities from the CapabilityEngine's runtime registry."""
    try:
        engine = CapabilityEngine()
        registry = get_capability_registry()
        for cap_id, capability in engine.list_all().items():
            if not registry.has_capability(cap_id):
                registry.register(
                    capability=cap_id,
                    module="capability_engine",
                    metadata={
                        "category": capability.category,
                        "available": capability.available,
                        "requires_user": capability.requires_user,
                    },
                    description=capability.description,
                )
    except Exception:
        pass
