"""MERLIN — ORION's internal strategic copilot.

MERLIN lives inside ORION as the intelligence layer:
  - Daily Brief: morning summary of system state, priorities, opportunities
  - Decision Log: structured record of decisions with expected vs actual outcomes
  - Memory: strategic context built on UnifiedMemoryStore
  - Planner: goal tracking and strategy (future)
"""

from __future__ import annotations

from core.merlin.brief import MerlinBrief
from core.merlin.decision_log import MerlinDecisionLog
from core.merlin.memory import MerlinMemory

__all__ = ["MerlinBrief", "MerlinDecisionLog", "MerlinMemory"]
