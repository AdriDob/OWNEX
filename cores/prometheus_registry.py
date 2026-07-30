"""Prometheus registry access for OWNEX metrics."""

from __future__ import annotations

# Import the registry directly from prometheus_client to avoid circular import
from prometheus_client.core import CollectorRegistry as RegistryType


# The OWNEX_REGISTRY is a CollectorRegistry instance defined in prometheus_metrics
# We need to import it dynamically to avoid circular import issues
def get_registry() -> RegistryType:
    """Return the OWNEX Prometheus registry."""
    from cores.prometheus_metrics import OWNEX_REGISTRY
    return OWNEX_REGISTRY
