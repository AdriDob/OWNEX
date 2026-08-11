"""Opyre Adapter — OSS issue bounties platform (similar to Opire)."""

from __future__ import annotations

from typing import Any


class OpyreAdapter:
    """Opyre adapter - OSS issue bounties platform."""

    platform = "opyre"
    cycle = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.token = self.config.get("token")

    @property
    def platform_name(self) -> str:
        return "opyre"

    @property
    def cycle_name(self) -> str:
        return "forge"

    def is_enabled(self) -> bool:
        return self.enabled

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[dict]:
        """Fetch bounties from Opyre API."""
        try:
            import httpx

            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            async with httpx.AsyncClient() as client:
                # Try multiple possible API endpoints
                endpoints = [
                    "https://api.opyre.com/v1/bounties",
                    "https://opyre.com/api/bounties",
                    "https://app.opyre.com/api/v1/bounties",
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

                raw_opps = []
                for bounty in bounties[:20]:
                    raw_opps.append(
                        {
                            "id": f"opyre_{bounty.get('id', bounty.get('slug'))}",
                            "name": bounty.get("title") or bounty.get("name") or "Opyre Bounty",
                            "description": bounty.get("description") or "",
                            "platform": "opyre",
                            "url": bounty.get("url") or bounty.get("link"),
                            "reward": float(bounty.get("amount", bounty.get("reward", 0))),
                            "effort_hours": float(bounty.get("estimated_hours", 5)),
                            "tags": bounty.get("labels", bounty.get("tags", ["oss", "bounty"])),
                            "cycle": "forge",
                            "source_type": "dev_bounty",
                            "source_name": "opyre",
                            "metadata": {"original": bounty},
                            "created_at": bounty.get("created_at"),
                        }
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("OpyreAdapter fetch failed: %s", e)
            return []


class OpyreMicrotaskAdapter:
    """Opyre micro-tasks / quick fixes adapter (Pulse cycle)."""

    platform = "opyre_microtask"
    cycle = "pulse"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.token = self.config.get("token")

    @property
    def platform_name(self) -> str:
        return "opyre_microtask"

    @property
    def cycle_name(self) -> str:
        return "pulse"

    def is_enabled(self) -> bool:
        return self.enabled

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[dict]:
        """Fetch quick-fix micro-tasks from Opyre (low effort, fast payout)."""
        try:
            import httpx

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

                raw_opps = []
                for task in tasks[:15]:
                    raw_opps.append(
                        {
                            "id": f"opyre_micro_{task.get('id')}",
                            "name": f"[Quick] {task.get('title') or 'Opyre Quick Task'}",
                            "description": task.get("description") or "",
                            "platform": "opyre_microtask",
                            "url": task.get("url"),
                            "reward": float(task.get("reward", 0)),
                            "effort_hours": float(task.get("time_estimate", 1)),
                            "tags": ["quick-fix", "microtask"] + task.get("labels", []),
                            "cycle": "pulse",
                            "source_type": "microtask",
                            "source_name": "opyre_microtask",
                            "metadata": {"original": task},
                            "created_at": task.get("created_at"),
                        }
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("OpyreMicrotaskAdapter fetch failed: %s", e)
            return []
