"""GitHub Bounty Search — real discovery adapter for the Direct Work Engine.

Searches GitHub issues with "bounty" label (or similar reward labels) across
public repositories. Free, no auth required (rate-limited to 10 req/min),
outcome-based: PR merged = paid.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource
from cores.direct_work_engine.models import (
    DifficultyLevel,
    Opportunity,
    OpportunityCategory,
    WorkPlatform,
)

logger = logging.getLogger("ownex.api.direct_work.adapters.github_bounty")

GITHUB_API_BASE = "https://api.github.com"


class GitHubBountyDweAdapter(BaseDiscoveryAdapter):
    """Discovers bounty-labeled GitHub issues via GitHub Search API."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        source = DiscoverySource(
            name="github_bounty",
            platform=WorkPlatform.GITHUB,
            categories=[
                OpportunityCategory.OPEN_SOURCE,
                OpportunityCategory.SOFTWARE_ENGINEERING,
            ],
            tier=1,
            analysis_cadence_hours=12,  # issues change frequently
            requires_auth=False,  # works unauthenticated (rate-limited)
        )
        super().__init__(source)

    # Search queries for different bounty label patterns
    _BOUNTY_QUERIES = [
        "label:bounty state:open",
        "label:reward state:open",
        "label:paid state:open",
        'label:"good first issue" state:open',  # often have rewards
        "label:hacktoberfest state:open",  # some have rewards
    ]

    async def fetch_opportunities(self) -> list:
        """Search GitHub for bounty issues via Search API."""
        opportunities: list = []

        for query in self._BOUNTY_QUERIES:
            try:
                items = await self._search_query(query)
                for item in items[:15]:  # limit per query
                    opp = self._convert_issue(item)
                    if opp:
                        opp.id = f"github_bounty_{opp.id}"
                        opportunities.append(opp)
            except Exception as e:
                logger.warning(f"GitHub bounty search '{query}' failed: {e}")

        # Deduplicate by issue URL
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.url not in seen:
                seen.add(opp.url)
                unique.append(opp)

        return unique

    async def _search_query(self, query: str) -> list[dict]:
        """Execute a single GitHub search query."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GITHUB_API_BASE}/search/issues",
                params={"q": query, "sort": "updated", "order": "desc", "per_page": 30},
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            if resp.status_code == 403:
                logger.warning("GitHub API rate limited (403)")
                return []
            if resp.status_code != 200:
                logger.warning(f"GitHub search API returned {resp.status_code}")
                return []
            data = resp.json()
            return data.get("items", [])

    def _convert_issue(self, issue: dict[str, Any]) -> Opportunity | None:
        """Convert GitHub issue to Opportunity."""
        try:
            from cores.direct_work_engine.models import (
                EmploymentType,
                EntryMechanism,
                ExperienceLevel,
                OpportunityCategory,
                PaymentMethod,
            )

            issue_url = issue.get("html_url", "")
            issue_number = issue.get("number", 0)
            repo_url = issue.get("repository_url", "").replace("api.github.com/repos", "github.com")
            repo_full = repo_url.replace("https://github.com/", "")
            title = issue.get("title", "")

            if not issue_url or not title:
                return None

            # Parse labels for bounty amount
            labels = [label.get("name", "").lower() for label in issue.get("labels", [])]
            reward = self._extract_reward(labels, issue.get("body", ""))

            # Estimate difficulty from labels/complexity
            difficulty = self._estimate_difficulty(labels, issue.get("body", ""))

            # Check if it's a "good first issue" (beginner friendly)
            is_beginner = any("good first" in label or "easy" in label or "beginner" in label for label in labels)

            return self._create_opportunity(
                external_id=f"{repo_full}#{issue_number}",
                title=f"[{repo_full}] {title}",
                category=OpportunityCategory.OPEN_SOURCE,
                url=issue_url,
                description=self._build_description(issue, repo_full),
                company=repo_full.split("/")[0],
                country="Global",
                payment=float(reward),
                currency="USD",
                payment_method=PaymentMethod.CRYPTO,
                difficulty=difficulty,
                language_required="english",
                estimated_time_hours=self._estimate_hours(difficulty),
                experience_required=ExperienceLevel.NONE,
                portfolio_required=False,
                interview_required=False,
                technical_test_required=False,
                registration_required=True,
                time_to_payout_days=14.0,  # typical after PR merge
                reputation=0.6,
                risk=0.2,
                payment_proven=False,  # depends on maintainer
                stability=0.5,
                accepts_beginner=is_beginner,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=self._extract_tags(issue) + ["github", "open_source", "bounty"],
                employment_type=EmploymentType.BOUNTY,
                entry_mechanism=EntryMechanism.DIRECT,
                time_to_first_work_hours=4.0,  # setup + first PR
            )
        except Exception as e:
            logger.warning(f"Error converting GitHub issue: {e}")
            return None

    def _extract_reward(self, labels: list[str], body: str) -> float:
        """Extract bounty amount from labels or issue body."""
        # Check labels first
        for label in labels:
            # Patterns: $500, $500.00, 500 USD, 500$, bounty:500

            matches = re.findall(r"\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:usd|usd)?", label, re.IGNORECASE)
            if matches:
                try:
                    return float(matches[0].replace(",", ""))
                except (ValueError, IndexError):
                    pass

        # Fallback: check body for bounty mentions
        if body:
            matches = re.findall(r"(?:bounty|reward|prize).*?\$?(\d+(?:,\d{3})*(?:\.\d{2})?)", body, re.IGNORECASE)
            if matches:
                try:
                    return float(matches[0].replace(",", ""))
                except (ValueError, IndexError):
                    pass

        # Default: unknown reward
        return 0.0

    def _estimate_difficulty(self, labels: list[str], body: str) -> DifficultyLevel:
        """Estimate difficulty from labels and content."""
        text = " ".join(labels + [body[:500]]).lower()
        if any(k in text for k in ["good first issue", "easy", "beginner", "starter", "help wanted"]):
            return DifficultyLevel.BEGINNER
        if any(k in text for k in ["advanced", "expert", "hard", "complex", "architect"]):
            return DifficultyLevel.ADVANCED
        if any(k in text for k in ["intermediate", "medium", "moderate"]):
            return DifficultyLevel.INTERMEDIATE
        return DifficultyLevel.INTERMEDIATE

    def _estimate_hours(self, difficulty: DifficultyLevel) -> float:
        return {
            DifficultyLevel.BEGINNER: 8.0,
            DifficultyLevel.INTERMEDIATE: 24.0,
            DifficultyLevel.ADVANCED: 60.0,
            DifficultyLevel.EXPERT: 100.0,
        }.get(difficulty, 24.0)

    def _build_description(self, issue: dict[str, Any], repo_full: str) -> str:
        parts = [f"GitHub bounty: {issue.get('title', '')}"]
        parts.append(f"Repo: {repo_full}")
        labels = [label.get("name", "") for label in issue.get("labels", [])]
        if labels:
            parts.append(f"Labels: {', '.join(labels[:5])}")
        if issue.get("body"):
            parts.append(f"Description: {issue['body'][:300]}")
        return " | ".join(parts)

    def _extract_tags(self, issue: dict[str, Any]) -> list[str]:
        tags = ["github", "open_source", "bounty", "pr"]
        labels = [label.get("name", "").lower() for label in issue.get("labels", [])]
        for label in labels:
            if label and label not in tags:
                tags.append(label.replace(" ", "_"))
        return tags

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{GITHUB_API_BASE}/rate_limit")
                return resp.status_code in (200, 403)  # 403 = rate limited but alive
        except Exception:
            return False


def build_github_bounty_adapter() -> GitHubBountyDweAdapter:
    """Factory for the GitHub Bounty adapter."""
    return GitHubBountyDweAdapter()
