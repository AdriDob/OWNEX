"""Engine Registry — Central registry for all trading engines.

Manages engine discovery, registration, health monitoring, and routing.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.trading.adapters.base import EngineAdapter
from core.trading.contracts import (
    EngineHealth,
    EngineHealthStatus,
    EngineMetadata,
)

logger = logging.getLogger("ownex.trading.registry")


@dataclass
class EngineRegistryEntry:
    """Registry entry for an engine."""

    metadata: Any  # EngineMetadata
    adapter: EngineAdapter | None = None
    config: dict = field(default_factory=dict)
    registered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_health_check: str | None = None
    health_status: EngineHealthStatus | None = None


class EngineRegistry:
    """Central registry for all trading engines.

    Handles:
    - Engine registration and discovery
    - Health monitoring (every 30s)
    - Capability-based routing
    - Engine lifecycle management
    """

    def __init__(self, data_dir: str = "data/trading/engines"):
        self.data_dir = data_dir
        self._engines: dict[str, EngineRegistryEntry] = {}
        self._monitoring_task: asyncio.Task | None = None
        self._monitoring_interval = 30  # seconds
        self._running = False

    # ════════════════════════════════════════════════════════════════════════
    # REGISTRATION
    # ═══════════════════════════════════════════════════════════════════════

    def register_engine(
        self,
        adapter: EngineAdapter,
        config: dict | None = None,
    ) -> bool:
        """Register an engine adapter."""
        engine_id = adapter.engine_id

        if engine_id in self._engines:
            logger.warning(f"Engine {engine_id} already registered, updating")
            self._engines[engine_id].adapter = adapter
            self._engines[engine_id].config = config or {}
        else:
            # Create metadata from adapter
            metadata = adapter.get_metadata()
            entry = EngineRegistryEntry(
                metadata=metadata,
                adapter=adapter,
                config=config or {},
            )
            self._engines[engine_id] = entry
            logger.info(f"Registered engine: {engine_id} ({adapter.ENGINE_NAME})")

        return True

    def unregister_engine(self, engine_id: str) -> bool:
        """Unregister an engine."""
        if engine_id in self._engines:
            entry = self._engines[engine_id]
            if entry.adapter:
                asyncio.create_task(entry.adapter.shutdown())
            del self._engines[engine_id]
            logger.info(f"Unregistered engine: {engine_id}")
            return True
        return False

    def get_engine(self, engine_id: str) -> EngineAdapter | None:
        """Get an engine adapter by ID."""
        entry = self._engines.get(engine_id)
        return entry.adapter if entry else None

    def list_engines(self) -> list[EngineMetadata]:
        """List all registered engines."""
        return [entry.metadata for entry in self._engines.values()]

    def get_engines_by_capability(self, capability: str) -> list[EngineAdapter]:
        """Get all engines supporting a capability."""
        engines = []
        for entry in self._engines.values():
            if entry.adapter and capability in entry.adapter.get_capabilities():
                engines.append(entry.adapter)
        return engines

    def get_engines_by_classification(self, classification: str) -> list[EngineAdapter]:
        """Get all engines matching a classification."""
        engines = []
        for entry in self._engines.values():
            if entry.adapter and classification in [c.value for c in entry.metadata.classification]:
                engines.append(entry.adapter)
        return engines

    # ════════════════════════════════════════════════════════════════════════
    # HEALTH MONITORING
    # ═══════════════════════════════════════════════════════════════════════

    async def start_monitoring(self, interval: int = 30) -> None:
        """Start health monitoring loop."""
        if self._running:
            return

        self._monitoring_interval = interval
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started engine health monitoring (interval: {interval}s)")

    async def stop_monitoring(self) -> None:
        """Stop health monitoring loop."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitoring_task
        logger.info("Stopped engine health monitoring")

    async def _monitoring_loop(self) -> None:
        """Background health monitoring loop."""
        while self._running:
            try:
                await self.check_all_health()
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
            await asyncio.sleep(self._monitoring_interval)

    async def check_all_health(self) -> dict[str, EngineHealthStatus]:
        """Check health of all registered engines."""
        results = {}
        for engine_id, entry in self._engines.items():
            if entry.adapter:
                try:
                    health = await entry.adapter.get_health_status()
                    entry.health_status = health
                    entry.last_health_check = datetime.now(UTC).isoformat()
                    results[engine_id] = health

                    if health.health == EngineHealth.ERROR:
                        logger.warning(f"Engine {engine_id} health check failed: {health.error}")
                except Exception as e:
                    logger.error(f"Health check failed for {engine_id}: {e}")

                    results[engine_id] = EngineHealthStatus(
                        engine_id=engine_id,
                        health=EngineHealth.ERROR,
                        last_check=datetime.now(UTC).isoformat(),
                        error=str(e),
                    )
        return results

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health summary."""
        total = len(self._engines)
        online = sum(
            1 for e in self._engines.values() if e.health_status and e.health_status.health == EngineHealth.ONLINE
        )
        offline = sum(
            1 for e in self._engines.values() if e.health_status and e.health_status.health != EngineHealth.ONLINE
        )

        return {
            "total_engines": total,
            "online": online,
            "offline": offline,
            "health_percentage": (online / total * 100) if total > 0 else 100,
            "engines": {
                eid: {
                    "name": entry.metadata.name,
                    "health": entry.health_status.health.value if entry.health_status else "unknown",
                    "last_check": entry.last_health_check,
                    "active_strategies": entry.health_status.active_strategies if entry.health_status else 0,
                }
                for eid, entry in self._engines.items()
            },
        }

    # ════════════════════════════════════════════════════════════════════════
    # ENGINE LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════

    async def install_engine(self, engine_id: str) -> bool:
        """Install an engine."""
        entry = self._engines.get(engine_id)
        if not entry or not entry.adapter:
            logger.error(f"Engine {engine_id} not registered")
            return False

        try:
            success = await entry.adapter.install()
            if success:
                await entry.adapter.initialize()
                entry.adapter._initialized = True
                logger.info(f"Engine {engine_id} installed and initialized")
                return True
            else:
                logger.error(f"Engine {engine_id} installation failed")
                return False
        except Exception as e:
            logger.error(f"Engine {engine_id} installation error: {e}")
            return False

    async def uninstall_engine(self, engine_id: str) -> bool:
        """Uninstall an engine."""
        entry = self._engines.get(engine_id)
        if not entry or not entry.adapter:
            return False

        try:
            await entry.adapter.shutdown()
            success = await entry.adapter.uninstall()
            if success:
                logger.info(f"Engine {engine_id} uninstalled")
            return success
        except Exception as e:
            logger.error(f"Engine {engine_id} uninstall error: {e}")
            return False

    async def start_engine(self, engine_id: str) -> bool:
        """Start an engine (initialize if needed)."""
        entry = self._engines.get(engine_id)
        if not entry or not entry.adapter:
            return False

        try:
            if not entry.adapter._initialized:
                await entry.adapter.initialize()
                entry.adapter._initialized = True
            logger.info(f"Engine {engine_id} started")
            return True
        except Exception as e:
            logger.error(f"Engine {engine_id} start error: {e}")
            return False

    async def stop_engine(self, engine_id: str) -> bool:
        """Stop an engine."""
        entry = self._engines.get(engine_id)
        if not entry or not entry.adapter:
            return False

        try:
            await entry.adapter.shutdown()
            logger.info(f"Engine {engine_id} stopped")
            return True
        except Exception as e:
            logger.error(f"Engine {engine_id} stop error: {e}")
            return False

    # ════════════════════════════════════════════════════════════════════════
    # CAPABILITY ROUTING
    # ═══════════════════════════════════════════════════════════════════════

    def get_best_engine_for(
        self,
        capability: str,
        classification: str | None = None,
        exchange: str | None = None,
    ) -> EngineAdapter | None:
        """Get the best engine for a given capability."""
        candidates = self.get_engines_by_capability(capability)

        if not candidates:
            return None

        # Filter by classification
        if classification:
            candidates = [e for e in candidates if classification in [c.value for c in e.get_metadata().classification]]

        # Filter by exchange
        if exchange:
            candidates = [e for e in candidates if exchange in e.SUPPORTED_EXCHANGES]

        if not candidates:
            return None

        # Prefer online engines
        online = [e for e in candidates if e.is_healthy()]
        if online:
            return online[0]

        return candidates[0] if candidates else None

    # ════════════════════════════════════════════════════════════════════════
    # STRATEGY ROUTING
    # ═══════════════════════════════════════════════════════════════════════

    async def route_signal(self, signal) -> str | None:
        """Route a signal to the appropriate engine."""
        # For now, return the strategy's engine
        # Could be enhanced with smart routing
        return None

    async def execute_order(self, order) -> bool:
        """Execute an order through the appropriate engine."""
        # Route to the engine that owns the strategy
        return True

    # ════════════════════════════════════════════════════════════════════════
    # SYSTEM STATUS
    # ═══════════════════════════════════════════════════════════════════════

    def get_registry_status(self) -> dict[str, Any]:
        """Get complete registry status."""
        return {
            "total_engines": len(self._engines),
            "engines": {
                eid: {
                    "id": eid,
                    "name": entry.metadata.name,
                    "version": entry.metadata.version,
                    "health": entry.health_status.health.value if entry.health_status else "unknown",
                    "last_check": entry.last_health_check,
                    "active_strategies": entry.health_status.active_strategies if entry.health_status else 0,
                    "capabilities": entry.adapter.get_capabilities() if entry.adapter else [],
                }
                for eid, entry in self._engines.items()
            },
        }


# ═════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════

_engine_registry: EngineRegistry | None = None


def get_engine_registry(data_dir: str = "data/trading/engines") -> EngineRegistry:
    """Get the global engine registry singleton."""
    global _engine_registry
    if _engine_registry is None:
        _engine_registry = EngineRegistry(data_dir)
    return _engine_registry
