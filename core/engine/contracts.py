"""Shared dataclasses and contracts for OWNEX v6.

All engines share these definitions. No ambiguity about types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ── Engine registry singleton ────────────────────────────────────────────


@dataclass
class EngineRegistration:
    """Registered engine in the system."""
    name: str
    instance: Any  # Engine instance
    status: str = "created"  # created | initialized | running | stopped | failed
    started_at: datetime | None = None
    health: dict[str, Any] = field(default_factory=dict)
