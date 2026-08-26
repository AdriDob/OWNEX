"""Sync Module — Offline-first synchronization for Desktop, Mobile, Watch."""

from __future__ import annotations

from .models import (
    ConflictStrategy,
    PendingMutation,
    SyncConflict,
    SyncEntityType,
    SyncEvent,
    SyncOperation,
    SyncRequest,
    SyncResponse,
)
from .service import SyncService, get_sync_service

__all__ = [
    "SyncEvent",
    "SyncConflict",
    "SyncRequest",
    "SyncResponse",
    "PendingMutation",
    "SyncEntityType",
    "SyncOperation",
    "ConflictStrategy",
    "SyncService",
    "get_sync_service",
]
