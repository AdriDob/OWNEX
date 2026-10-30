"""ObservationEngine — orchestrates the Universal Sensor Network.

Collects observations from all registered sensors and feeds them
into the OWNEX pipeline (Normalization → Identity → Classification → ...).
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from cores.engine.base import Engine
from cores.sensors.base import ObservationCache, Sensor
from cores.sensors.observation import Observation

logger = logging.getLogger("ownex.sensors.observation_engine")


class ObservationEngine(Engine):
    """Coordinates all sensors in the Universal Sensor Network.

    Responsibilities:
    - Register and manage sensors
    - Collect observations on demand or on schedule
    - Deduplicate via ObservationCache
    - Emit observation events to EventBus
    """

    name = "observation_engine"

    def __init__(self, event_bus: Any | None = None) -> None:
        super().__init__()
        self._sensors: dict[str, Sensor] = {}
        self._cache = ObservationCache()
        self._event_bus = event_bus

    async def initialize(self) -> None:
        """Initialize — verify sensors are loaded."""
        logger.info("ObservationEngine: %d sensors registered", len(self._sensors))
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        """Return engine + per-sensor health."""
        sensor_health = {}
        for sid, sensor in self._sensors.items():
            try:
                sensor_health[sid] = await sensor.health()
            except Exception as e:
                sensor_health[sid] = {"error": str(e)}

        return {
            "status": "ok",
            "name": self.name,
            "sensors_count": len(self._sensors),
            "cache_size": self._cache.size(),
            "sensors": sensor_health,
        }

    # ── Sensor management ─────────────────────────────────────────────

    def register(self, sensor: Sensor) -> None:
        """Add a sensor to the network."""
        if sensor.id in self._sensors:
            logger.warning("Sensor '%s' already registered, replacing", sensor.id)
        self._sensors[sensor.id] = sensor
        logger.info("Sensor registered: %s (%s)", sensor.id, sensor.name)

    def unregister(self, sensor_id: str) -> None:
        """Remove a sensor."""
        self._sensors.pop(sensor_id, None)

    def get_sensor(self, sensor_id: str) -> Sensor | None:
        return self._sensors.get(sensor_id)

    @property
    def sensors(self) -> dict[str, Sensor]:
        return dict(self._sensors)

    @property
    def cache(self) -> ObservationCache:
        return self._cache

    # ── Collection ────────────────────────────────────────────────────

    async def collect(self, sensor_id: str | None = None) -> list[Observation]:
        """Collect observations from one or all sensors.

        Args:
            sensor_id: If provided, collect from this sensor only.
                       If None, collect from ALL registered sensors.

        Returns:
            List of unique (non-duplicate) observations.
        """
        target_sensors = (
            [self._sensors[sensor_id]] if sensor_id and sensor_id in self._sensors else list(self._sensors.values())
        )

        all_new: list[Observation] = []

        for sensor in target_sensors:
            try:
                observations = await sensor.fetch()
            except Exception as e:
                logger.error("Sensor '%s' fetch failed: %s", sensor.id, e)
                continue

            # Deduplicate
            new_count = 0
            for obs in observations:
                if not self._cache.is_duplicate(obs):
                    all_new.append(obs)
                    new_count += 1

            if new_count < len(observations):
                logger.debug(
                    "Sensor '%s': %d observations, %d new (dedup removed %d)",
                    sensor.id,
                    len(observations),
                    new_count,
                    len(observations) - new_count,
                )

        # Emit event bus signal
        if self._event_bus and all_new:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    "sensors:observations:new",
                    count=len(all_new),
                    sensor_ids=list({o.sensor_id for o in all_new}),
                )

        return all_new


# ── Singleton ────────────────────────────────────────────────────────────
# El patrón del proyecto (`_revenue_loop`, `_five_pillar_orchestrator`, …):
# un `_x: T | None = None` + un `get_x()` que lo crea la primera vez.
#
# Faltaba, y `universal_connectors.py` la usa: importaba
# `get_observation_engine` de este módulo y no existía, así que **el módulo
# entero no importaba**. Eso hacía inalcanzable `get_platform_manager`, que a
# su vez rompía 4 endpoints de `api/routers/control.py` (500) y 2 tareas de
# `cores/daily_tasks.py` (envueltas en `try/except: pass`, o sea en silencio).
#
# `api/lifespan.py:263` crea SU propia instancia con el event bus del boot; el
# singleton es para quien no tiene a mano el bus (p. ej. los connectors).
_observation_engine: ObservationEngine | None = None


def get_observation_engine(event_bus: Any | None = None) -> ObservationEngine:
    """ObservationEngine global. Crea una sin bus en el primer acceso."""
    global _observation_engine
    if _observation_engine is None:
        _observation_engine = ObservationEngine(event_bus=event_bus)
    return _observation_engine
