"""MERLIN — ORION's internal strategic copilot.

MERLIN lives inside ORION as the intelligence layer:
  - Daily Brief: morning summary of system state, priorities, opportunities
  - Decision Log: structured record of decisions with expected vs actual outcomes
  - Memory: strategic context built on UnifiedMemoryStore
  - Planner: goal tracking and strategy (future)
"""

from __future__ import annotations

from cores.merlin.brief import MerlinBrief
from cores.merlin.decision_log import MerlinDecisionLog
from cores.merlin.memory import MerlinMemory

__all__ = ["MerlinBrief", "MerlinDecisionLog", "MerlinMemory"]
