"""Cycle Engine — Work Cycles domain for OWNEX.

Exports:
- Cycle model and enums
- CycleService for lifecycle management
- CycleRegistry for declarative cycle registration
- CycleMetricsEngine for metrics computation
- Event publishing helpers
"""

from __future__ import annotations

from cores.cycles.events import (
    publish_cycle_activated,
    publish_cycle_created,
    publish_cycle_deleted,
    publish_cycle_error,
    publish_cycle_event,
    publish_cycle_metrics_updated,
    publish_cycle_paused,
    publish_cycle_status_changed,
    publish_cycle_updated,
)
from cores.cycles.metrics import CycleMetricsEngine
from cores.cycles.models import DEFAULT_CYCLES, Cycle, CycleCategory, CycleStatus
from cores.cycles.registry import CycleDefinition, CycleRegistry, get_cycle_registry
from cores.cycles.schemas import (
    CycleBase,
    CycleCreate,
    CycleMetrics,
    CycleRead,
    CycleStatusUpdate,
    CycleUpdate,
)
from cores.cycles.service import CycleService, get_cycle_service

__all__ = [
    # Models
    "Cycle",
    "CycleStatus",
    "CycleCategory",
    "DEFAULT_CYCLES",
    # Schemas
    "CycleBase",
    "CycleCreate",
    "CycleUpdate",
    "CycleRead",
    "CycleMetrics",
    "CycleStatusUpdate",
    # Service
    "CycleService",
    "get_cycle_service",
    # Registry
    "CycleRegistry",
    "CycleDefinition",
    "get_cycle_registry",
    # Metrics
    "CycleMetricsEngine",
    # Events
    "publish_cycle_event",
    "publish_cycle_created",
    "publish_cycle_updated",
    "publish_cycle_deleted",
    "publish_cycle_activated",
    "publish_cycle_paused",
    "publish_cycle_status_changed",
    "publish_cycle_metrics_updated",
    "publish_cycle_error",
]
