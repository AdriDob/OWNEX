from __future__ import annotations

"""Cycle Engine — Work Cycles domain for OWNEX.
Exports:
- Cycle model and enums
- CycleService for lifecycle management
- CycleRegistry for declarative cycle registration
- CycleMetricsEngine for metrics computation
- Event publishing helpers
"""
from core.cycles.events import (
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
from core.cycles.metrics import CycleMetricsEngine
from core.cycles.models import DEFAULT_CYCLES, Cycle, CycleCategory, CycleStatus
from core.cycles.registry import CycleDefinition, CycleRegistry, get_cycle_registry
from core.cycles.schemas import (
    CycleBase,
    CycleCreate,
    CycleMetrics,
    CycleRead,
    CycleStatusUpdate,
    CycleUpdate,
)
from core.cycles.service import CycleService, get_cycle_service

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
