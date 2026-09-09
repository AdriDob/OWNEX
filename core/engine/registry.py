"""EngineRegistry — singleton that tracks all registered engines."""

from __future__ import annotations

import logging
from typing import Any

from core.engine.base import Engine
from core.engine.contracts import EngineRegistration

logger = logging.getLogger("ownex.registry")


class EngineRegistry:
    """Singleton registry for all OWNEX v6 engines.

    Provides lifecycle management and health aggregation.
    """

    _instance: EngineRegistry | None = None

    def __new__(cls) -> EngineRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._engines: dict[str, EngineRegistration] = {}
        self._initialized = True

    def register(self, engine: Engine) -> None:
        """Register an engine."""
        if engine.name in self._engines:
            logger.warning("Engine '%s' already registered, replacing", engine.name)
        self._engines[engine.name] = EngineRegistration(
            name=engine.name,
            instance=engine,
        )
        logger.info("Engine registered: %s", engine.name)

    def get(self, name: str) -> Engine | None:
        """Get an engine by name."""
        reg = self._engines.get(name)
        return reg.instance if reg else None

    async def initialize_all(self) -> dict[str, Any]:
        """Initialize all registered engines."""
        results = {}
        for name, reg in self._engines.items():
            try:
                await reg.instance.initialize()
                reg.status = "initialized"
                results[name] = {"status": "ok"}
            except Exception as e:
                reg.status = "failed"
                results[name] = {"status": "failed", "error": str(e)}
                logger.error("Engine '%s' init failed: %s", name, e)
        return results

    async def start_all(self) -> dict[str, Any]:
        """Start all initialized engines."""
        results = {}
        for name, reg in self._engines.items():
            if reg.status == "initialized":
                try:
                    await reg.instance.start()
                    reg.status = "running"
                    results[name] = {"status": "ok"}
                except Exception as e:
                    reg.status = "failed"
                    results[name] = {"status": "failed", "error": str(e)}
        return results

    async def stop_all(self) -> None:
        """Stop all running engines."""
        for reg in self._engines.values():
            if reg.status == "running":
                try:
                    await reg.instance.stop()
                    reg.status = "stopped"
                except Exception as e:
                    logger.error("Engine '%s' stop failed: %s", reg.name, e)

    async def aggregate_health(self) -> dict[str, Any]:
        """Get health status for all engines."""
        health = {}
        for name, reg in self._engines.items():
            try:
                h = await reg.instance.health()
                reg.health = h
                health[name] = h
            except Exception as e:
                health[name] = {"status": "error", "error": str(e)}
        return health

    def list_engines(self) -> list[dict[str, Any]]:
        """List all engines with their registration status."""
        return [
            {
                "name": reg.name,
                "status": reg.status,
                "started_at": reg.started_at.isoformat() if reg.started_at else None,
            }
            for reg in self._engines.values()
        ]

    def clear(self) -> None:
        """Clear all engines (for testing)."""
        self._engines.clear()
