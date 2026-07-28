"""OWNEX Loop Engineering — autonomous agent loop patterns.

Bridges loop-engineering (https://github.com/cobusgreyling/loop-engineering)
to OWNEX Work Cycles.

Provides:
  - LoopPattern, LoopState, LoopRun dataclasses
  - LoopEngine — runs patterns via scheduler + event bus
  - Pattern registry (YAML-based)
  - OWNEX-specific patterns for Security, Forge, Pulse, Vault, Atlas
"""

from __future__ import annotations

from core.loop.engine import LoopEngine
from core.loop.models import (
    LoopPattern,
    LoopRunResult,
    LoopState,
    PatternBudget,
    PatternRisk,
    Phase,
    Skill,
)
from core.loop.registry import (
    PatternRegistry,
    get_ownex_patterns,
    register_ownex_patterns,
)
from core.loop.startup import (
    get_loop_engine,
    get_loop_status,
    init_loop_engines,
    shutdown_engines,
)

__all__ = [
    "LoopPattern",
    "LoopState",
    "LoopRunResult",
    "Phase",
    "PatternBudget",
    "PatternRisk",
    "Skill",
    "LoopEngine",
    "PatternRegistry",
    "get_ownex_patterns",
    "register_ownex_patterns",
]
