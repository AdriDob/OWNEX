"""Synack Adapter — Security Work Cycle.

Invite-only platform with Red Team operations. Requires special handling.
Uses public program directory + optional authenticated API for Red Team members.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.synack")

SYNACK_PUBLIC_API = "https://platform.synack.com/api/public"
SYNACK_AUTH_API = "https://platform.synack.com/api"


class SynackAdapter(OpportunityAdapter):
    """Adapter for Synack Red Team operations.

    Invite-only platform. Public API provides limited program info.
    Full access requires Red Team membership with authenticated API.
    """

    platform: str = "synack"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        creds = get_platform_credentials("synack")
        self._token = creds.get("api_token") or os.environ.get("SYNACK_API_TOKEN", "")
        self._enabled = bool(self._token)

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Synack missions/programs."""
        raw_opps: list[RawOpportunity] = []
        missions = await self._fetch_missions()

        for mission in missions:
            if not mission.get("has_rewards"):
                continue

            raw_opps.append(
                RawOpportunity(
                    id=f"synack_{mission.get('id', mission.get('name', ''))}",
                    name=mission.get("name", ""),
                    description=mission.get("description", "") or f"Synack mission: {mission.get('name', '')}",
                    platform="synack",
                    url=mission.get("mission_url", ""),
                    reward=mission.get("estimated_payout", 0.0),
                    effort_hours=mission.get("estimated_effort_hours", 8.0),
                    tags=mission.get("categories", ["red-team", "penetration-testing", "bug-bounty"]),
                    cycle="security",
                    source_type="platform",
                    source_name="synack",
                    metadata={"original": mission, "personal": personal, "invite_only": True},
                    created_at=mission.get("created_at", ""),
                )
            )

        logger.info("SynackAdapter: fetched %d opportunities", len(raw_opps))
        return raw_opps

    async def _fetch_missions(self) -> list[dict[str, Any]]:
        """Fetch missions from Synack public/private API."""
        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            # Try public missions endpoint first
            try:
                url = f"{SYNACK_PUBLIC_API}/missions"
                resp = await client.get(url, headers={"Accept": "application/json"}, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    missions = data if isinstance(data, list) else data.get("missions", data.get("data", []))
                    for mission in missions:
                        results.append(self._normalize_mission(mission))
                    logger.info("Synack public: %d missions", len(results))
                    return results
            except Exception as e:
                logger.debug("Synack public API not available: %s", e)

            # If authenticated, try private API
            if self._enabled:
                try:
                    url = f"{SYNACK_AUTH_API}/redteam/missions"
                    resp = await client.get(url, headers=self._headers(), timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        missions = data if isinstance(data, list) else data.get("missions", data.get("data", []))
                        for mission in missions:
                            results.append(self._normalize_mission(mission))
                        logger.info("Synack authenticated: %d missions", len(results))
                except Exception as e:
                    logger.warning("Synack authenticated fetch failed: %s", e)

        # Fallback: known Synack-style missions (for development)
        if not results:
            results = self._fallback_missions()

        return results

    def _normalize_mission(self, mission: dict[str, Any]) -> dict[str, Any]:
        """Normalize mission data from API."""
        name = mission.get("name", mission.get("title", mission.get("code_name", "")))
        if not name:
            name = f"Synack Mission {mission.get('id', 'unknown')}"

        payout = mission.get("max_payout", mission.get("payout", mission.get("reward", 0)))
        if isinstance(payout, str):
            import re

            amounts = re.findall(r"[\d,]+(?:\.\d+)?", payout.replace(",", ""))
            payout = float(max(amounts)) if amounts else 0

        return {
            "id": mission.get("id", mission.get("slug", name.lower().replace(" ", "-"))),
            "name": name,
            "description": mission.get("description", mission.get("overview", "")),
            "categories": mission.get("categories", mission.get("tags", ["red-team"])),
            "mission_url": mission.get("url", mission.get("mission_url", "")),
            "has_rewards": bool(mission.get("has_bounty", mission.get("payout", True))),
            "estimated_payout": float(payout) if payout else 0.0,
            "estimated_effort_hours": self._estimate_effort(float(payout) if payout else 0),
            "created_at": mission.get("created_at", mission.get("start_date", "")),
        }

    def _estimate_effort(self, payout: float) -> float:
        # Synack missions are typically full pentest engagements
        if payout >= 50000:
            return 60.0
        elif payout >= 20000:
            return 40.0
        elif payout >= 10000:
            return 25.0
        elif payout >= 5000:
            return 15.0
        return 10.0

    def _fallback_missions(self) -> list[dict[str, Any]]:
        """Fallback missions for development/testing when API unavailable."""
        logger.info("Synack: using fallback missions (API unavailable)")
        return [
            {
                "id": "synack_enterprise_web",
                "name": "Enterprise Web Application Assessment",
                "description": "Comprehensive security assessment of enterprise web application including authentication, authorization, and business logic.",
                "categories": ["web-application", "red-team", "penetration-testing"],
                "mission_url": "https://platform.synack.com/missions/enterprise-web",
                "has_rewards": True,
                "estimated_payout": 25000.0,
                "estimated_effort_hours": 40.0,
                "created_at": "2026-01-15T00:00:00Z",
            },
            {
                "id": "synack_mobile_app",
                "name": "Mobile Application Security Review",
                "description": "iOS and Android mobile application security testing including local storage, network communication, and platform-specific vulnerabilities.",
                "categories": ["mobile", "red-team", "penetration-testing"],
                "mission_url": "https://platform.synack.com/missions/mobile-app",
                "has_rewards": True,
                "estimated_payout": 15000.0,
                "estimated_effort_hours": 25.0,
                "created_at": "2026-01-10T00:00:00Z",
            },
            {
                "id": "synack_api_security",
                "name": "API Security Assessment",
                "description": "REST/GraphQL API security testing including authentication bypasses, authorization flaws, and data exposure.",
                "categories": ["api", "red-team", "penetration-testing"],
                "mission_url": "https://platform.synack.com/missions/api-security",
                "has_rewards": True,
                "estimated_payout": 12000.0,
                "estimated_effort_hours": 20.0,
                "created_at": "2026-01-05T00:00:00Z",
            },
        ]
