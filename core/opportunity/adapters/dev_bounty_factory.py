"""Dev Bounty Platform Adapters Factory.

Connects to all crypto/dev bounty platforms supported by OWNEX/Rastro.
Maps to the "Dev Bounties — Código por tarea" category from the bounty list.
"""

from __future__ import annotations

from typing import Any

from .proxies_sx import ProxiesSXAdapter
from .bountycaster import BountycasterAdapter
from .taskmarket import TaskmarketAdapter
from .collaborators_build import CollaboratorsBuildAdapter
from .warpspeed_open import WarpSpeedOpenAdapter
from .converse_js import ConverseJSAdapter
from .algora import AlgoraAdapter
from .tenstorrent import TenstorrentAdapter
from .superteam_earn import SuperteamEarnAdapter
from .dework import DeworkAdapter
from .layer3 import Layer3Adapter
from .questbook import QuestbookAdapter
from .coordinape import CoordinapeAdapter
from .commonwealth import CommonwealthAdapter
from .dorahacks import DoraHacksAdapter
from .kleoverse import KleoverseAdapter
from .chain_love import ChainLoveAdapter


class DevBountyFactory:
    """Factory for creating Dev Bounty platform adapters."""

    @staticmethod
    def create(platform: str, config: dict[str, Any] | None = None) -> Any:
        """Create a specific platform adapter by name."""
        adapter_map = {
            "proxies_sx": ProxiesSXAdapter,
            "bountycaster": BountycasterAdapter,
            "taskmarket": TaskmarketAdapter,
            "collaborators_build": CollaboratorsBuildAdapter,
            "warpspeed_open": WarpSpeedOpenAdapter,
            "converse_js": ConverseJSAdapter,
            "algora": AlgoraAdapter,
            "tenstorrent": TenstorrentAdapter,
            "superteam_earn": SuperteamEarnAdapter,
            "dework": DeworkAdapter,
            "layer3": Layer3Adapter,
            "questbook": QuestbookAdapter,
            "coordinape": CoordinapeAdapter,
            "commonwealth": CommonwealthAdapter,
            "dorahacks": DoraHacksAdapter,
            "kleoverse": KleoverseAdapter,
            "chain_love": ChainLoveAdapter,
        }

        cls = adapter_map.get(platform.lower())
        if not cls:
            raise ValueError(f"No dev bounty adapter for platform: {platform}")

        return cls(config)

    @staticmethod
    async def list_platforms() -> list[str]:
        """List all available dev bounty platforms."""
        return [
            "proxies_sx",
            "bountycaster",
            "taskmarket",
            "collaborators_build",
            "warpspeed_open",
            "converse_js",
            "algora",
            "tenstorrent",
            "superteam_earn",
            "dework",
            "layer3",
            "questbook",
            "coordinape",
            "commonwealth",
            "dorahacks",
            "kleoverse",
            "chain_love",
        ]

    @staticmethod
    async def fetch_all_programs(config: dict[str, Any] | None = None) -> list[Any]:
        """Fetch from all configured dev bounty platforms."""
        all_opps: list[Any] = []
        for platform in await DevBountyFactory.list_platforms():
            adapter = DevBountyFactory.create(platform, config)
            opps = await adapter.fetch_opportunities()
            all_opps.extend(opps)
        return all_opps

    @staticmethod
    async def fetch_all_submissions(config: dict[str, Any] | None = None) -> list[Any]:
        """Fetch submissions from all dev bounty platforms.

        Note: Most dev bounty platforms don't have a submission model like
        security bounties, so this returns empty by default but can be
        overridden per-adapter if needed.
        """
        all_opps: list[Any] = []
        for platform in await DevBountyFactory.list_platforms():
            adapter = DevBountyFactory.create(platform, config)
            if hasattr(adapter, "fetch_submissions"):
                opps = await adapter.fetch_submissions()
                all_opps.extend(opps)
        return all_opps
