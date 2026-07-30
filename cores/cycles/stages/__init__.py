"""Stage Executors — base abstraction and factory for the Security Cycle pipeline.

Each stage executor implements a single pipeline stage:
    recon → attack_surface → hypothesis → validation → evidence → report → learning

Usage:
    from cores.cycles.stages import get_executor

    executor = get_executor("recon")
    result = executor.execute(context)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("ownex.cycles.stages")


class StageExecutor(ABC):
    """Abstract base for all security pipeline stage executors.

    Subclasses must implement:
        - execute(context) -> dict      # Run the stage
        - name property                  # Stage identifier (matches STAGE_ORDER keys)
    """

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute this pipeline stage.

        Args:
            context: Stage-specific parameters (target, scope, previous results, etc.)

        Returns:
            dict with at minimum:
                - status: str           "completed" | "failed" | "skipped"
                - summary: str          Human-readable one-liner
                - stage: str            Stage name
                - details: dict         Stage-specific output data
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Stage identifier matching STAGE_ORDER in SecurityCycle."""
        ...


class BaseStageExecutor(StageExecutor):
    """Common base with logging, DB session helpers, and error handling."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"ownex.cycles.stages.{self.name}")

    def _get_session(self):
        """Get a fresh DB session for this stage execution."""
        from database import db
        return db.SessionLocal()

    def _wrap_result(
        self,
        status: str,
        summary: str,
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Standardised result envelope."""
        result: dict[str, Any] = {
            "stage": self.name,
            "status": status,
            "summary": summary,
            "details": details or {},
        }
        if error:
            result["error"] = error
        return result

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Override in subclass."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement execute()")


# ── Factory ──────────────────────────────────────────────────────────


_STAGE_EXECUTORS: dict[str, type[StageExecutor]] = {}


def register_executor(name: str, cls: type[StageExecutor]) -> None:
    """Register a stage executor by name."""
    _STAGE_EXECUTORS[name] = cls
    logger.debug("Registered stage executor: %s", name)


def get_executor(name: str) -> StageExecutor:
    """Factory: return a StageExecutor instance for the given stage name.

    Raises KeyError if the stage is not registered.
    """
    if name not in _STAGE_EXECUTORS:
        available = ", ".join(sorted(_STAGE_EXECUTORS))
        raise KeyError(
            f"Unknown stage executor: '{name}'. Available: {available}"
        )
    return _STAGE_EXECUTORS[name]()


# ── Auto-register built-in executors ────────────────────────────────


def _auto_register() -> None:
    """Import and register all built-in stage executors."""
    from cores.cycles.stages.attack_surface_executor import AttackSurfaceExecutor
    from cores.cycles.stages.evidence_executor import EvidenceExecutor
    from cores.cycles.stages.hypothesis_executor import HypothesisExecutor
    from cores.cycles.stages.learning_executor import LearningExecutor
    from cores.cycles.stages.recon_executor import ReconExecutor
    from cores.cycles.stages.report_executor import ReportExecutor
    from cores.cycles.stages.validation_executor import ValidationExecutor

    _STAGE_EXECUTORS["recon"] = ReconExecutor
    _STAGE_EXECUTORS["attack_surface"] = AttackSurfaceExecutor
    _STAGE_EXECUTORS["hypothesis"] = HypothesisExecutor
    _STAGE_EXECUTORS["validation"] = ValidationExecutor
    _STAGE_EXECUTORS["evidence"] = EvidenceExecutor
    _STAGE_EXECUTORS["report"] = ReportExecutor
    _STAGE_EXECUTORS["learning"] = LearningExecutor


_auto_register()

__all__ = [
    "StageExecutor",
    "BaseStageExecutor",
    "get_executor",
    "register_executor",
    "ReconExecutor",
    "AttackSurfaceExecutor",
    "HypothesisExecutor",
    "ValidationExecutor",
    "EvidenceExecutor",
    "ReportExecutor",
    "LearningExecutor",
]
