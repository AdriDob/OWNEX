"""HackerOne Sensor — wraps the existing BountyScraper.scrape_hackerone().

No modifications to the legacy scraper.
Just wraps its output as ownObservations.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.sensors.base import Sensor
from core.sensors.observation import Observation
from cores.bounty_scraper.scraper import BountyScraper

logger = logging.getLogger("ownex.sensors.hackerone")


class HackerOneSensor(Sensor):
    """Monitors HackerOne's public program directory.

    Wraps the existing BountyScraper.scrape_hackerone() method.
    The scraper remains unmodified — this sensor just adapts its output.
    """

    id = "hackerone"
    name = "HackerOne Public Programs"
    source_type = "bug_bounty"
    source_name = "hackerone"
    cadence_seconds = 1800  # 30 min

    def __init__(self, scraper: BountyScraper | None = None) -> None:
        super().__init__()
        self._scraper = scraper or BountyScraper()

    async def fetch(self) -> list[Observation]:
        """Scrape HackerOne programs and wrap as Observations."""
        programs = self._scraper.scrape_hackerone(max_pages=3)

        observations = []
        for prog in programs:
            if not prog.has_rewards:
                continue

            now = datetime.now(timezone.utc).isoformat()
            obs = Observation(
                id=f"hackerone:{prog.name}",
                sensor_id=self.id,
                external_id=prog.name,
                title=prog.name,
                description=prog.description or f"HackerOne program: {prog.name}",
                raw_data={
                    "program_url": prog.program_url,
                    "scope_url": prog.scope_url,
                    "platform": prog.platform,
                },
                source_type=self.source_type,
                source_name=self.source_name,
                url=prog.program_url or prog.scope_url,
                tags=prog.technologies or ["bug-bounty"],
                observed_at=now,
            )
            observations.append(obs)

        self._fetch_count += 1
        self._last_fetch = datetime.now(timezone.utc).timestamp()
        logger.info("HackerOneSensor: %d observations", len(observations))
        return observations
