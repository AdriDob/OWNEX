"""Engine base class for OWNEX v6 Autonomous Work OS.

Every engine in the pipeline inherits from Engine.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("ownex.engine")


class Engine(ABC):
    """Base class for all OWNEX v6 engines.

    Each engine has a lifecycle:
      initialize() → start() → ... work ... → stop()

    Health checks are required for every engine (used by the system monitor).
    """

    name: str = ""
    version: str = "6.0.0"

    def __init__(self) -> None:
        self._initialized = False
        self._running = False

    @abstractmethod
    async def initialize(self) -> None:
        """Set up resources, connections, and state.

        Called once at system startup.
        """
        raise NotImplementedError

    async def start(self) -> None:
        """Begin processing.

        Default: set _running flag. Override for engines that
        need background loops.
        """
        self._running = True
        logger.info("Engine '%s' started", self.name)

    async def stop(self) -> None:
        """Graceful shutdown. Called on system stop."""
        self._running = False
        logger.info("Engine '%s' stopped", self.name)

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Return engine health status.

        Must return at minimum:
          {"status": "ok" | "degraded" | "failed", "name": self.name}
        """
        raise NotImplementedError

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_initialized(self) -> bool:
        return self._initialized
