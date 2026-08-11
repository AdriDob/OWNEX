"""Base adapter for pulse platforms."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PulseAdapter(ABC):
    """Base class for all pulse platform adapters.

    Pulse adapters discover AI work / microtasks. They use vault credentials
    and HTTP clients, returning RawOpportunity objects.
    """

    platform: str = "unknown"
    cycle: str = "pulse"

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

    @abstractmethod
    async def fetch_opportunities(self, personal: dict | None = None) -> list[dict]:
        """Fetch opportunities from the platform.

        Returns a list of RawOpportunity dicts with these keys:
          - id, name, description, platform, url
          - reward, effort_hours, tags, cycle
          - source_type, source_name, metadata, created_at
        """
        pass
