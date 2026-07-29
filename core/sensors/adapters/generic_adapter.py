"""GenericSensor — wraps any existing OpportunityAdapter as a Sensor.

This allows ALL existing adapters (forge, pulse, etc.) to participate
in the Universal Sensor Network without modification.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.opportunity.adapters import OpportunityAdapter
from core.sensors.base import Sensor
from core.sensors.observation import Observation

logger = logging.getLogger("ownex.sensors.generic")


class GenericAdapterSensor(Sensor):
    """Wraps an existing OpportunityAdapter as a Sensor.

    Any platform that already has an adapter can be added to the
    Universal Sensor Network by wrapping it with this class.
    """

    def __init__(
        self,
        adapter: OpportunityAdapter,
        sensor_id: str | None = None,
        cadence_seconds: int = 3600,
    ) -> None:
        super().__init__()
        self._adapter = adapter
        self.id = sensor_id or f"sensor:{adapter.platform}"
        self.name = f"{adapter.platform.capitalize()} Sensor"
        self.source_type = adapter.cycle or "unknown"
        self.source_name = adapter.platform
        self.cadence_seconds = cadence_seconds

    async def fetch(self) -> list[Observation]:
        """Fetch opportunities from the adapter, wrap as Observations."""
        try:
            raw_opportunities = await self._adapter.fetch_opportunities()
        except Exception as e:
            self._last_error = str(e)
            logger.error("GenericSensor %s failed: %s", self.id, e)
            return []

        observations = []
        now = datetime.now(timezone.utc).isoformat()
        for raw in raw_opportunities:
            obs = Observation(
                id=f"{raw.platform}:{raw.id}",
                sensor_id=self.id,
                external_id=raw.id,
                title=raw.name,
                description=raw.description,
                raw_data=raw.metadata if hasattr(raw, "metadata") else {},
                source_type=self.source_type,
                source_name=raw.platform,
                url=raw.url,
                estimated_reward_min=0.0,
                estimated_reward_max=raw.reward,
                tags=raw.tags,
                observed_at=now,
            )
            observations.append(obs)

        self._fetch_count += 1
        self._last_fetch = datetime.now(timezone.utc).timestamp()
        logger.info("GenericSensor %s: %d observations", self.id, len(observations))
        return observations
