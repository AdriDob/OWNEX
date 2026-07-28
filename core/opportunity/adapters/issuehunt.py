"""IssueHunt / IssueHand Adapter — OSS issue bounties (issuehunt.io / issuehand)."""

from __future__ import annotations

from typing import Any

import httpx

from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class IssueHuntAdapter(OpportunityAdapter):
    """IssueHunt.io adapter - OSS issue bounties (Forge cycle)."""

    platform: str = "issuehunt"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties from IssueHunt API."""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.issuehunt.io/v1/bounties", headers=headers, timeout=10)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:20]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"issuehunt_{bounty.get('id')}",
                            name=bounty.get("title") or "IssueHunt Bounty",
                            description=bounty.get("description") or "",
                            platform="issuehunt",
                            url=bounty.get("url"),
                            reward=float(bounty.get("amount", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 4)),
                            tags=bounty.get("labels", ["oss", "bounty", "github"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="issuehunt",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("IssueHuntAdapter fetch failed: %s", e)
            return []


class IssueHandAdapter(OpportunityAdapter):
    """IssueHand adapter (separate platform, Forge cycle)."""

    platform: str = "issuehand"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties from IssueHand API."""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.issuehand.io/v1/bounties", headers=headers, timeout=10)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"issuehand_{bounty.get('id')}",
                            name=f"[IssueHand] {bounty.get('title') or 'IssueHand Bounty'}",
                            description=bounty.get("description") or "",
                            platform="issuehand",
                            url=bounty.get("url"),
                            reward=float(bounty.get("amount", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 3)),
                            tags=bounty.get("labels", ["oss", "bounty"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="issuehand",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("IssueHandAdapter fetch failed: %s", e)
            return []
