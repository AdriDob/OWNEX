from __future__ import annotations

"""Unified Memory — namespaced, taggable, persistent memory for all ORION subsystems.
Namespaces: global, cateye, atlas, odyssey, hermes, copilot, user, projects, research, decision_history
"""
# ruff: noqa: E402

from core.memory.models import DEFAULT_NAMESPACES, MemoryEntry
from core.memory.store import UnifiedMemoryStore, get_memory_store

__all__ = [
    "UnifiedMemoryStore",
    "get_memory_store",
    "MemoryEntry",
    "DEFAULT_NAMESPACES",
]
