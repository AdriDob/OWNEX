"""OWNEX Loop Engine — startup initializer.

Wires loop patterns into the scheduler and event bus during app startup.

Called from api/main.py lifespan.
"""

from __future__ import annotations

import logging
from typing import Any

from core.loop.engine import LoopEngine
from core.loop.registry import get_registry

logger = logging.getLogger("orion.core.loop.startup")

# Global registry of active loop engines
_engines: dict[str, LoopEngine] = {}

# Registry for health API
_loop_status_cache: dict[str, dict[str, Any]] = {}


def init_loop_engines(
    scheduler: Any | None = None,
    event_bus: Any | None = None,
) -> dict[str, Any]:
    """Initialize all registered loop engines.

    Called once during app startup.

    Args:
        scheduler: CoreScheduler instance (optional)
        event_bus: CoreEventBus instance (optional)

    Returns:
        dict with initialization status
    """
    global _engines, _loop_status_cache

    registry = get_registry()
    patterns = registry.get_all()
    summary: dict[str, Any] = {
        "total_patterns": len(patterns),
        "registered": [],
        "skipped": [],
        "errors": [],
    }

    for pattern in patterns:
        try:
            engine = LoopEngine(
                pattern=pattern,
                scheduler=scheduler,
                event_bus=event_bus,
            )

            # Register phase handlers for default behaviour
            _register_default_handlers(engine)

            # Register with scheduler
            job_id = engine.register()
            if job_id:
                summary["registered"].append({"pattern": pattern.id, "job_id": job_id, "cadence": pattern.cadence})
            else:
                summary["skipped"].append({"pattern": pattern.id, "reason": "no scheduler"})

            _engines[pattern.id] = engine
            _loop_status_cache[pattern.id] = engine.status()

        except Exception as exc:
            logger.exception("Failed to init loop engine %s", pattern.id)
            summary["errors"].append({"pattern": pattern.id, "error": str(exc)})

    logger.info(
        "Loop engines: %d registered, %d skipped, %d errors",
        len(summary["registered"]),
        len(summary["skipped"]),
        len(summary["errors"]),
    )

    return summary


def _register_default_handlers(engine: LoopEngine) -> None:
    """Register default phase handlers for all pattern phases.

    Each phase handler publishes events and logs progress.
    Specific apps can override these with custom handlers via engine.on().
    """
    from core.loop.models import Phase

    async def _report_handler(eng: LoopEngine, ctx: dict[str, Any]) -> None:
        logger.debug("Loop %s: REPORT phase", eng.pattern_id)

    async def _discover_handler(eng: LoopEngine, ctx: dict[str, Any]) -> None:
        logger.debug("Loop %s: DISCOVER phase", eng.pattern_id)

    async def _triage_handler(eng: LoopEngine, ctx: dict[str, Any]) -> None:
        logger.debug("Loop %s: TRIAGE phase", eng.pattern_id)

    async def _classify_handler(eng: LoopEngine, ctx: dict[str, Any]) -> None:
        logger.debug("Loop %s: CLASSIFY phase", eng.pattern_id)

    async def _act_handler(eng: LoopEngine, ctx: dict[str, Any]) -> None:
        logger.debug("Loop %s: ACT phase", eng.pattern_id)

    async def _verify_handler(eng: LoopEngine, ctx: dict[str, Any]) -> None:
        logger.debug("Loop %s: VERIFY phase", eng.pattern_id)

    async def _notify_handler(eng: LoopEngine, ctx: dict[str, Any]) -> None:
        logger.debug("Loop %s: NOTIFY phase", eng.pattern_id)

    async def _review_handler(eng: LoopEngine, ctx: dict[str, Any]) -> None:
        logger.debug("Loop %s: REVIEW phase", eng.pattern_id)

    # Register all phase handlers
    engine.on(Phase.REPORT, _report_handler)
    engine.on(Phase.DISCOVER, _discover_handler)
    engine.on(Phase.TRIAGE, _triage_handler)
    engine.on(Phase.CLASSIFY, _classify_handler)
    engine.on(Phase.ACT, _act_handler)
    engine.on(Phase.FIX, _act_handler)  # FIX = ACT
    engine.on(Phase.VERIFY, _verify_handler)
    engine.on(Phase.NOTIFY, _notify_handler)
    engine.on(Phase.REVIEW, _review_handler)


def get_loop_status() -> dict[str, Any]:
    """Get status of all registered loop engines for health API."""
    global _loop_status_cache

    # Refresh cache from live engines
    for pid, engine in _engines.items():
        _loop_status_cache[pid] = engine.status()

    return {
        "loop_engines": _loop_status_cache,
        "total": len(_engines),
        "running": sum(1 for e in _engines.values() if e.is_running),
    }


def get_loop_engine(pattern_id: str) -> LoopEngine | None:
    """Get a specific loop engine by pattern ID."""
    return _engines.get(pattern_id)


def shutdown_engines() -> None:
    """Clean shutdown of all loop engines."""
    global _engines, _loop_status_cache
    _engines.clear()
    _loop_status_cache.clear()
    logger.info("All loop engines shut down")
