"""ORION Integration Center — unified view of all external integrations."""

from __future__ import annotations

from core.integrations.discovery import (
    BUILTIN_INTEGRATIONS,
    IntegrationDef,
    get_builtin_integrations,
    get_integration,
    get_integrations_by_category,
)
from core.integrations.registry import (
    IntegrationRegistry,
    IntegrationStatus,
    get_integration_registry,
    init_integration_registry,
)

__all__ = [
    "BUILTIN_INTEGRATIONS",
    "IntegrationDef",
    "IntegrationRegistry",
    "IntegrationStatus",
    "get_builtin_integrations",
    "get_integration",
    "get_integration_registry",
    "get_integrations_by_category",
    "init_integration_registry",
]
