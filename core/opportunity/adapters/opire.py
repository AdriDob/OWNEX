"""Opire/Opyre Adapter — OSS issue bounties platform (Forge cycle)."""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class OpireAdapter(OpportunityAdapter):
    """Opire.com adapter - OSS issue bounties (Forge cycle)."""

    platform: str = "opire"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("opire", config)
        super().__init__(merged_config)
        self.token = self.config.get("token") or self.config.get("api_key")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties from Opire API."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
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


class OpyreAdapter(OpportunityAdapter):
    """Opyre.com adapter - OSS issue bounties (Forge cycle, alias/alternative to Opire)."""

    platform: str = "opyre"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("opyre", config)
        super().__init__(merged_config)
        self.token = self.config.get("token") or self.config.get("api_key")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties from Opyre API."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            async with httpx.AsyncClient() as client:
                # Try primary endpoint, fallback to Opire API
                endpoints = [
                    "https://api.opyre.com/v1/bounties",
                    "https://opyre.com/api/bounties",
                    "https://api.opire.com/v1/bounties",  # fallback to Opire
                ]

                for endpoint in endpoints:
                    try:
                        resp = await client.get(endpoint, headers=headers, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            bounties = data.get("bounties", data.get("data", []))
                            break
                    except Exception:
                        continue
                else:
                    return []

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:20]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"opyre_{bounty.get('id', bounty.get('slug'))}",
                            name=bounty.get("title") or bounty.get("name") or "Opyre Bounty",
                            description=bounty.get("description") or "",
                            platform="opyre",
                            url=bounty.get("url") or bounty.get("link"),
                            reward=float(bounty.get("amount", bounty.get("reward", 0))),
                            effort_hours=float(bounty.get("estimated_hours", 5)),
                            tags=bounty.get("labels", bounty.get("tags", ["oss", "bounty"])),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="opyre",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("OpyreAdapter fetch failed: %s", e)
            return []


class OpyreMicrotaskAdapter(OpportunityAdapter):
    """Opyre micro-tasks / quick fixes adapter (Pulse cycle)."""

    platform: str = "opyre_microtask"
    cycle: str = "pulse"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("opyre_micro", config)
        super().__init__(merged_config)
        self.token = self.config.get("token") or self.config.get("api_key")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch quick-fix micro-tasks from Opyre (low effort, fast payout)."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.opyre.com/v1/tasks/quick",
                    headers=headers,
                    params={"max_effort_hours": 4, "min_reward": 25},
                    timeout=10,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"opyre_micro_{task.get('id')}",
                            name=f"[Quick] {task.get('title') or 'Opyre Quick Task'}",
                            description=task.get("description") or "",
                            platform="opyre_microtask",
                            url=task.get("url"),
                            reward=float(task.get("reward", 0)),
                            effort_hours=float(task.get("time_estimate", 1)),
                            tags=["quick-fix", "microtask"] + task.get("labels", []),
                            cycle="pulse",
                            source_type="microtask",
                            source_name="opyre_microtask",
                            metadata={"original": task},
                            created_at=task.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("OpyreMicrotaskAdapter fetch failed: %s", e)
            return []
