"""Kaggle Competitions — real discovery adapter for the Direct Work Engine.

Kaggle competitions are paid data science challenges: outcome-based, zero
experience required (leaderboard is the proof), public leaderboard = transparent
acceptance. No interview, no portfolio, no resume — just submit and rank.
"""

from __future__ import annotations

import logging
import re
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

logger = logging.getLogger("ownex.api.direct_work.adapters.kaggle")

KAGGLE_API_BASE = "https://www.kaggle.com/api/v1"
KAGGLE_PUBLIC_BASE = "https://www.kaggle.com"


class KaggleDweAdapter(BaseDiscoveryAdapter):
    """Discovers active Kaggle competitions and converts them to Opportunities."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        source = DiscoverySource(
            name="kaggle",
            platform=WorkPlatform.KAGGLE,
            categories=[
                OpportunityCategory.AI_EVALUATION,
                OpportunityCategory.DATA_ANNOTATION,
                OpportunityCategory.SYNTHETIC_DATA,
            ],
            tier=1,
            analysis_cadence_hours=72,  # competitions don't change daily
            requires_auth=True,  # API key needed for full access
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch active competitions from Kaggle API."""
        opportunities: list[Opportunity] = []

        # Try authenticated API first (full data)
        if await self._fetch_from_api(opportunities):
            return opportunities

        # Fallback: scrape public page (limited but no auth needed)
        await self._scrape_public_page(opportunities)
        return opportunities

    async def _fetch_from_api(self, opportunities: list[Opportunity]) -> bool:
        """Try authenticated Kaggle API. Returns True if successful."""
        try:
            from cores.credentials.vault import get_platform_credentials

            creds = get_platform_credentials("kaggle")
            if not creds.get("username") or not creds.get("key"):
                logger.debug("Kaggle credentials not in vault, skipping API")
                return False

            auth = (creds["username"], creds["key"])
            async with httpx.AsyncClient(auth=auth, timeout=30) as client:
                resp = await client.get(
                    f"{KAGGLE_API_BASE}/competitions/list",
                    params={"status": "active", "page": 1, "pageSize": 50},
                )
                if resp.status_code != 200:
                    logger.warning(f"Kaggle API returned {resp.status_code}")
                    return False

                competitions = resp.json()
                for comp in competitions:
                    opp = self._convert_competition(comp)
                    if opp:
                        opportunities.append(opp)
                return True
        except Exception as e:
            logger.debug(f"Kaggle API fetch failed: {e}")
            return False

        return False

    async def _scrape_public_page(self, opportunities: list[Opportunity]) -> None:
        """Fallback: scrape active competitions from public page."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{KAGGLE_PUBLIC_BASE}/competitions", timeout=30)
                if resp.status_code != 200:
                    return

                # Parse HTML for competition data
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(resp.text, "html.parser")
                # Kaggle public page structure - find competition cards
                comps = soup.find_all("a", href=re.compile(r"/competitions/[^/]+$"))
                seen = set()
                for link in comps[:20]:
                    href = link.get("href", "")
                    if href in seen:
                        continue
                    seen.add(href)

                    # Extract basic info
                    title_elem = link.find("div", class_=re.compile(r"title|name"))
                    title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)

                    # Build opportunity with minimal data
                    opp = self._create_minimal_opportunity(href, title)
                    if opp:
                        opportunities.append(opp)
        except Exception as e:
            logger.warning(f"Kaggle public scrape failed: {e}")

    def _convert_competition(self, comp: dict[str, Any]) -> Opportunity | None:
        """Convert Kaggle API competition to Opportunity."""
        try:
            comp_id = str(comp.get("id", ""))
            title = str(comp.get("title", "") or comp.get("ref", ""))
            if not comp_id or not title:
                return None

            reward = float(comp.get("totalPrize", comp.get("rewardQuantity", 0)) or 0)
            currency = str(comp.get("rewardTypeName", "USD")).upper()

            # Estimate effort based on prize tier
            if reward >= 100000:
                difficulty = DifficultyLevel.ADVANCED
                effort_hours = 100.0
            elif reward >= 10000:
                difficulty = DifficultyLevel.INTERMEDIATE
                effort_hours = 40.0
            else:
                difficulty = DifficultyLevel.BEGINNER
                effort_hours = 20.0

            tags = list(comp.get("tags", []))
            if "tabular" in str(comp).lower():
                tags.append("tabular")
            if "computer vision" in str(comp).lower():
                tags.append("computer_vision")
            if "nlp" in str(comp).lower():
                tags.append("nlp")

            return Opportunity(
                id=f"kaggle_{comp_id}",
                title=f"{title} (Kaggle)",
                platform=WorkPlatform.KAGGLE,
                category=OpportunityCategory.AI_EVALUATION,
                url=f"https://www.kaggle.com/competitions/{comp.get('ref', comp_id)}",
                description=self._build_description(comp),
                remote=True,
                payment=reward,
                currency=currency,
                payment_method=PaymentMethod.PLATFORM_CREDIT,
                international_payment=True,
                difficulty=difficulty,
                language_required="english",
                estimated_time_hours=effort_hours,
                experience_required=ExperienceLevel.NONE,
                portfolio_required=False,
                interview_required=False,
                technical_test_required=False,
                registration_required=True,
                time_to_payout_days=30.0,
                reputation=0.85,
                risk=0.1,
                payment_proven=True,
                stability=0.8,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=tags + ["kaggle", "data_science", "competition"],
                employment_type=EmploymentType.PRIZE,
                entry_mechanism=EntryMechanism.DIRECT,
                time_to_first_work_hours=2.0,
                hourly_rate_usd=None,
                rate_source="platform",
            )
        except Exception as e:
            logger.warning(f"Error converting Kaggle competition {comp.get('id')}: {e}")
            return None

    def _create_minimal_opportunity(self, href: str, title: str) -> Opportunity | None:
        """Create minimal opportunity from public page scrape."""
        comp_id = href.split("/")[-1]
        if not comp_id or not title:
            return None

        return Opportunity(
            id=f"kaggle_{comp_id}",
            title=f"{title} (Kaggle)",
            platform=WorkPlatform.KAGGLE,
            category=OpportunityCategory.AI_EVALUATION,
            url=f"https://www.kaggle.com{href}",
            description=f"Kaggle competition: {title}. Public page only — full details need API key.",
            remote=True,
            payment=0.0,  # unknown from public page
            currency="USD",
            payment_method=PaymentMethod.PLATFORM_CREDIT,
            international_payment=True,
            difficulty=DifficultyLevel.INTERMEDIATE,
            language_required="english",
            estimated_time_hours=40.0,
            experience_required=ExperienceLevel.NONE,
            portfolio_required=False,
            interview_required=False,
            technical_test_required=False,
            registration_required=True,
            time_to_payout_days=None,
            reputation=0.7,
            risk=0.2,
            payment_proven=False,
            stability=0.6,
            accepts_beginner=True,
            accepts_freelancers=True,
            accepts_individuals=True,
            accepts_ai_tools=True,
            asynchronous=True,
            technology_tags=["kaggle", "data_science", "competition"],
            employment_type=EmploymentType.PRIZE,
            entry_mechanism=EntryMechanism.DIRECT,
            time_to_first_work_hours=2.0,
            hourly_rate_usd=None,
            rate_source="public_page",
        )

    def _build_description(self, comp: dict[str, Any]) -> str:
        parts = [f"Kaggle competition: {comp.get('title', 'Unknown')}"]
        if comp.get("description"):
            parts.append(comp["description"][:300])
        if comp.get("totalPrize"):
            parts.append(f"Prize: ${comp['totalPrize']:,}")
        if comp.get("tags"):
            parts.append(f"Tags: {', '.join(comp['tags'][:5])}")
        if comp.get("evaluationAlgorithm"):
            parts.append(f"Evaluation: {comp['evaluationAlgorithm']}")
        return " | ".join(parts)

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{KAGGLE_PUBLIC_BASE}/competitions")
                return resp.status_code == 200
        except Exception:
            return False


def build_kaggle_adapter() -> KaggleDweAdapter:
    """Factory for the Kaggle adapter."""
    return KaggleDweAdapter()
