"""Dework Discovery Adapter for Direct Work Engine.

Fetches DAO work and bounties from Dework and converts them to
DirectWorkEngine Opportunities with web3/DAO focus.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource
from cores.direct_work_engine.models import (
    DifficultyLevel,
    EmploymentType,
    EntryMechanism,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)

logger = logging.getLogger("ownex.api.direct_work.adapters.dework")

DEWORK_API_BASE = "https://api.dework.xyz"


class DeworkDweAdapter(BaseDiscoveryAdapter):
    """Discovers Dework tasks and bounties via public API."""

    def __init__(self) -> None:
        source = DiscoverySource(
            name="dework",
            platform=WorkPlatform.DEWORK,
            categories=[
                OpportunityCategory.DEV_BOUNTY,
                OpportunityCategory.OPEN_SOURCE,
                OpportunityCategory.OPEN_CALL,
            ],
            tier=1,
            analysis_cadence_hours=24,
            requires_auth=False,
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch active Dework tasks/bounties and convert to Opportunities."""
        opportunities: list[Opportunity] = []

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                endpoints = [
                    "https://api.dework.xyz/v1/tasks",
                    "https://dework.xyz/api/tasks",
                ]

                tasks = []
                for endpoint in endpoints:
                    try:
                        resp = await client.get(endpoint, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            tasks = data if isinstance(data, list) else data.get("data", data.get("tasks", []))
                            if tasks:
                                logger.info("Dework: successfully fetched from %s", endpoint)
                                break
                    except Exception as e:
                        logger.debug("Dework endpoint %s failed: %s", endpoint, e)
                        continue

                if not tasks:
                    logger.warning("Dework: all endpoints failed")
                    return opportunities

                for task in tasks:
                    opp = self._convert_task(task)
                    if opp:
                        opportunities.append(opp)

        except Exception as e:
            logger.error("Error fetching Dework tasks: %s", e)

        return opportunities

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get("https://api.dework.xyz/v1/tasks")
                return resp.status_code == 200
        except Exception:
            return False

    def _convert_task(self, task: dict[str, Any]) -> Opportunity | None:
        """Convert Dework task to Opportunity with web3/DAO barrier assessment."""
        try:
            task_id = str(task.get("id", "") or task.get("slug", ""))
            name = str(task.get("title", "") or task.get("name", ""))
            if not task_id or not name:
                return None

            max_bounty = float(task.get("reward", 0) or task.get("amount", 0) or task.get("reward_usd", 0) or 0)
            avg_bounty = max_bounty * 0.4

            effort_hours = 10.0 if max_bounty > 2000 else 5.0

            return self._create_opportunity(
                external_id=task_id,
                title=f"{name} — Dework",
                category=OpportunityCategory.DEV_BOUNTY,
                url=f"https://dework.xyz/tasks/{task_id}",
                description=self._build_description(task),
                company="Dework",
                country="Global",
                payment=avg_bounty or max_bounty * 0.2,
                currency="USD",
                payment_method=PaymentMethod.CRYPTO,
                difficulty=DifficultyLevel.INTERMEDIATE,
                language_required="english",
                estimated_time_hours=effort_hours,
                experience_required=ExperienceLevel.NONE,
                portfolio_required=False,
                interview_required=False,
                technical_test_required=False,
                registration_required=True,
                time_to_payout_days=7.0,
                reputation=0.75,
                risk=0.15,
                payment_proven=True,
                stability=0.7,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=self._extract_tags(task),
                employment_type=EmploymentType.BOUNTY,
                entry_mechanism=EntryMechanism.ASSESSMENT,
                hourly_rate_usd=None,
                time_to_first_work_hours=None,
                rate_source="platform",
            )
        except Exception as e:
            logger.error("Error converting Dework task %s: %s", task.get("id"), e)
            return None

    def _build_description(self, task: dict[str, Any]) -> str:
        parts = []
        if task.get("description"):
            parts.append(task["description"][:500])
        if task.get("skills"):
            parts.append(f"Skills: {', '.join(task['skills'][:5])}")
        if task.get("tags"):
            parts.append(f"Tags: {', '.join(task['tags'][:5])}")
        return " | ".join(parts)

    def _extract_tags(self, task: dict[str, Any]) -> list[str]:
        tags = ["web3", "dao", "dework", "dev_bounty", "bounty"]
        if task.get("skills"):
            tags.extend([s.lower() for s in task["skills"][:5]])
        if task.get("tags"):
            tags.extend([t.lower() for t in task["tags"][:5]])
        return tags


def build_dework_adapter() -> DeworkDweAdapter:
    """Factory function for building the Dework adapter."""
    return DeworkDweAdapter()
