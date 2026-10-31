"""OWNEX Operating Context — persistent operating context and policy engine.

This module integrates the Operating Context (docs/OPERATING_CONTEXT.md) as a
persistent, versioned, queryable system that guides the execution layer.
It reuses existing components:

  - PolicyEngine      (core/copilot/permissions.py)
  - UnifiedMemoryStore (core/memory/store.py)
  - DailyBriefing     (core/daily_cycle/system.py)

It does NOT create a second policy engine, a second scheduler, or a second
ledger. It adds the operational layer on top of what already exists.
"""

from __future__ import annotations

from .engine import OperatingContext
from .register import (
    ContextQuality,
    ContextStatus,
    OperatingContextPolicies,
    OpportunityPolicyEngine,
    OpportunityState,
)

__all__ = [
    "OperatingContext",
    "OperatingContextPolicies",
    "OpportunityPolicyEngine",
    "OpportunityState",
    "ContextStatus",
    "ContextQuality",
]

__version__ = "1.0.0"
