"""Forge Cycle Adapter — Dev Bounty platforms.

Credentials integrated via vault.
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class ForgeAdapter(OpportunityAdapter):
    """Base adapter for Dev Bounty platforms (Superteam, Opire, Algora, etc.)."""

    platform: str = "forge"
    cycle: str = "forge"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch dev bounty opportunities from configured platforms."""
        try:
            from core.opportunity import get_engine

            engine = get_engine()
            opportunities = engine.get_all()

            # Filter for dev bounty platforms
            dev_platforms = {"superteam", "opire", "algora", "issuehunt", "gitcoin", "bountysource"}
            filtered = [opp for opp in opportunities if opp.source and opp.source.name.lower() in dev_platforms]

            raw_opps: list[RawOpportunity] = []
            for opp in filtered:
                raw_opps.append(
                    RawOpportunity(
                        id=f"forge_{opp.id}",
                        name=opp.name,
                        description=opp.description or opp.name,
                        platform=opp.source.name.lower() if opp.source else "forge",
                        url=opp.public_url,
                        reward=float(opp.estimated_payout or 0),
                        effort_hours=float(opp.estimated_effort_hours or 4.0),
                        tags=list(opp.technology_tags),
                        cycle="forge",
                        source_type="dev_bounty",
                        source_name=opp.source.name if opp.source else "forge",
                        metadata={"original": opp, "personal": None},
                        created_at=opp.created_at.isoformat() if opp.created_at else "",
                    )
                )
            return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("ForgeAdapter fetch failed: %s", e)
            return []


class SuperteamAdapter(OpportunityAdapter):
    """Superteam.dev adapter - Solana/Web3 dev bounties (Forge cycle)."""

    platform: str = "superteam"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("superteam", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("superteam", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties from Superteam API."""
        try:
            headers = get_auth_headers("superteam", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.superteam.fun/bounties", headers=headers, timeout=10)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:20]:  # Limit
                    raw_opps.append(
                        RawOpportunity(
                            id=f"superteam_{bounty.get('id', bounty.get('slug'))}",
                            name=bounty.get("title") or bounty.get("name") or "Superteam Bounty",
                            description=bounty.get("description") or "",
                            platform="superteam",
                            url=bounty.get("url") or bounty.get("apply_url"),
                            reward=float(bounty.get("reward_usd") or bounty.get("reward", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 8)),
                            tags=bounty.get("tags", ["web3", "solana"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="superteam",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("SuperteamAdapter fetch failed: %s", e)
            return []


class OpireAdapter(OpportunityAdapter):
    """Opire.com adapter - OSS issue bounties (Forge cycle)."""

    platform: str = "opire"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("opire", config)
        super().__init__(merged_config)
        self.token = get_api_key("opire", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties from Opire API."""
        try:
            headers = get_auth_headers("opire", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.opire.com/v1/bounties", headers=headers, timeout=10)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:20]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"opire_{bounty.get('id')}",
                            name=bounty.get("title") or "Opire Bounty",
                            description=bounty.get("description") or "",
                            platform="opire",
                            url=bounty.get("url"),
                            reward=float(bounty.get("amount", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 6)),
                            tags=bounty.get("labels", ["oss", "bounty"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="opire",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("OpireAdapter fetch failed: %s", e)
            return []


class AlgoraAdapter(OpportunityAdapter):
    """Algora.xyz adapter - OSS bounties on GitHub issues (Forge cycle)."""

    platform: str = "algora"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("algora", config)
        super().__init__(merged_config)
        self.token = get_api_key("algora", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties from Algora API."""
        try:
            headers = get_auth_headers("algora", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.algora.xyz/v1/bounties", headers=headers, timeout=10)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:20]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"algora_{bounty.get('id')}",
                            name=bounty.get("title") or "Algora Bounty",
                            description=bounty.get("description") or "",
                            platform="algora",
                            url=bounty.get("url"),
                            reward=float(bounty.get("amount", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 5)),
                            tags=bounty.get("labels", ["oss", "github"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="algora",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("AlgoraAdapter fetch failed: %s", e)
            return []
