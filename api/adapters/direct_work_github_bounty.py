"""GitHub Bounty Search — real discovery adapter for the Direct Work Engine.

Searches GitHub issues with "bounty" label (or similar reward labels) across
public repositories. Free, no auth required (rate-limited to 10 req/min),
outcome-based: PR merged = paid.
"""

from __future__ import annotations

import logging
import os
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

#: Upper bound for a published bounty, USD. A bare number pasted into a label
#: or body is not money: "bounty 9999...9" (82 digits) once inflated the
#: WorkBank pipeline to $1e82. Above the observed market ceiling the figure
#: is UNKNOWN (0.0), never a truncated invention.
_MAX_SANE_REWARD_USD: float = 10_000_000.0

#: A currency marker is REQUIRED: a bare year or id is not money.
_REWARD_LABEL_RE = re.compile(
    r"(?:bounty|reward|prize|payout)\s*(?:of|for|is|:|=|-|–|—)?\s*"
    r"(?:\$|usd\b)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*([kKmM])?\b",
    re.IGNORECASE,
)
#: Same shape, but body/title prose is often "bounty of $500".
_REWARD_BODY_RE = re.compile(
    r"(?:bounty|reward|prize|payout)\s*(?:of|for|is|:|=|-|–|—)?\s*"
    r"(?:\$|usd\b)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*([kKmM])?\b",
    re.IGNORECASE,
)
#: "k"/"m" mean thousands/millions: "$3k" is 3000, not 3.
_AMOUNT_SUFFIX = {"k": 1_000.0, "m": 1_000_000.0}


def _sane_reward(value: float) -> float:
    """Keep 0.0 .. $10M; anything else is UNKNOWN, not a truncated number."""
    return value if 0.0 <= value <= _MAX_SANE_REWARD_USD else 0.0


def _first_amount(rx: re.Pattern[str], text: str) -> float:
    """Primer monto con marcador de moneda. Sin marcador ⇒ 0.0 (UNKNOWN)."""
    for match in rx.finditer(text):
        groups = match.groups()
        raw = next((g for g in groups if g and g[0].isdigit()), None)
        suffix = groups[-1] if len(groups) > 1 else None
        if raw is None:
            continue
        try:
            amount = float(raw.replace(",", ""))
        except (ValueError, IndexError):
            continue
        if suffix:
            amount *= _AMOUNT_SUFFIX.get(suffix.lower(), 1.0)
        return _sane_reward(amount)
    return 0.0


class GitHubBountyDweAdapter(BaseDiscoveryAdapter):
    """Discovers bounty-labeled GitHub issues via GitHub Search API."""

    # Base bounty labels. With languages: 3 queries × language (budget-bounded).
    # Without languages: current 5-query behavior (unchanged contract).
    _BASE_LABEL_QUERIES = [
        "label:bounty state:open",
        "label:reward state:open",
        "label:paid state:open",
    ]
    _BOUNTY_QUERIES = [
        "label:bounty state:open",
        "label:reward state:open",
        "label:paid state:open",
        'label:"good first issue" state:open',  # often have rewards
        "label:hacktoberfest state:open",  # some have rewards
    ]

    # Cap idiomas por request: GitHub search cobra 1 request por query.
    # Con token: 30/min; anónimo: 10/min. 3 queries × 5 idiomas = 15 max.
    MAX_LANGUAGES_PER_SCAN = 5

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

    @staticmethod
    def _normalize_languages(languages: list[str] | None) -> list[str]:
        """Lowercase + dedupe + cap. Server-side qualifier needs exact names."""
        seen: list[str] = []
        for lang in languages or []:
            name = (lang or "").strip().lower().replace(" ", "-")
            if name and name not in seen:
                seen.append(name)
        return seen[: GitHubBountyDweAdapter.MAX_LANGUAGES_PER_SCAN]

    def _normalize_keywords(self, keywords: list[str] | None) -> list[str]:
        """Sanitize + dedupe + cap the stack keywords (max 5).

        Only characters valid inside a GitHub search term survive; the
        result is lowercase and order-preserving.
        """
        if not keywords:
            return []
        out: list[str] = []
        for raw in keywords:
            cleaned = re.sub(r"[^a-z0-9._#-]+", " ", str(raw).lower()).strip()
            cleaned = cleaned.replace(" ", "")
            if not cleaned:
                continue
            if cleaned not in out:
                out.append(cleaned)
            if len(out) >= 5:
                break
        return out

    def _build_queries(self, languages: list[str] | None = None, keywords: list[str] | None = None) -> list[str]:
        """Bounty queries, restricted by `language:` and/or a keyword OR-group.

        GitHub ANDs qualifiers, so each language needs its own queries. The
        keyword group is a single OR-group appended to each base, so adding
        stack keywords costs **zero** extra queries.
        """
        langs = self._normalize_languages(languages)
        kws = self._normalize_keywords(keywords if keywords is not None else self._config.get("keywords"))
        group = f"({' OR '.join(kws)})" if kws else ""
        if not langs:
            return [f"{base}{group}" for base in self._BOUNTY_QUERIES]
        return [f"{base} language:{lang}{group}" for lang in langs for base in self._BASE_LABEL_QUERIES]

    async def fetch_opportunities(self, languages: list[str] | None = None, keywords: list[str] | None = None) -> list:
        """Search GitHub for bounty issues via Search API.

        ``languages`` (e.g. ["rust", "go", "solidity"]) restricts server-side
        via ``language:`` qualifiers. ``keywords`` filters by stack as an
        OR-group, at no extra query cost.
        """
        queries = self._build_queries(
            languages if languages is not None else self._config.get("languages"),
            keywords if keywords is not None else self._config.get("keywords"),
        )
        opportunities: list = []

        for query in queries:
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
        """Execute a single GitHub search query.

        Uses GITHUB_TOKEN when configured (30 req/min) else anonymous (10/min).
        """
        headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GITHUB_API_BASE}/search/issues",
                params={"q": query, "sort": "updated", "order": "desc", "per_page": 30},
                headers=headers,
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
            reward = self._extract_reward(
                labels,
                issue.get("body", ""),
                title=issue.get("title", ""),
            )

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

    def _extract_reward(self, labels: list[str], body: str, title: str = "") -> float:
        """Reward amount. UNKNOWN (0.0) unless a CURRENCY marker is present.

        Fuentes, en orden: labels → título → body. El título importa porque
        muchas plataformas escriben ahí el monto ("[PAID BOUNTY - $2k]").

        Un año pegado al nombre de un label NO es dinero: "hacktoberfest2025"
        devolvía $2.025. Y un número absurdo pegado a "bounty" (82 dígitos)
        devolvía $1e82. Ambos ⇒ 0.0.
        """
        for label in labels:
            amount = _first_amount(_REWARD_LABEL_RE, label)
            if amount > 0.0:
                return amount
        if title:
            amount = _first_amount(_REWARD_BODY_RE, title)
            if amount > 0.0:
                return amount
        if body:
            return _first_amount(_REWARD_BODY_RE, body)
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


async def repos_without_paid_evidence(repo_keys: list[str], client: httpx.AsyncClient | None = None) -> dict[str, str]:
    """Repos whose bounty history shows **no merged PR**, mapped to the reason.

    A bounty board that promises "$960 al mergear" and has never merged a
    single PR has not paid anyone. Measured 2026-10-01: the four repos the
    discovery surfaced had 0 merged PRs across 30+ closed PRs each.

    Returns ONLY repos with zero evidence of payment, so the caller can
    exclude them without hiding the ones that do pay.
    """
    owns = client is None
    client = client or httpx.AsyncClient(timeout=20, headers={"Accept": "application/vnd.github+json"})
    out: dict[str, str] = {}
    try:
        for key in repo_keys:
            owner, _, repo = key.partition("/")
            if not owner or not repo:
                continue
            resp = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls", params={"state": "closed", "per_page": 30}
            )
            if resp.status_code != 200:
                continue  # unknown ⇒ do not accuse
            pulls = resp.json()
            merged = sum(1 for p in pulls if p.get("merged_at"))
            if pulls and merged == 0:
                out[key] = (
                    f"sin evidencia de pago: {len(pulls)} PRs cerradas, 0 mergeadas "
                    f"(verificado en GitHub API el 2026-10-01)"
                )
    except Exception as exc:  # noqa: BLE001 — never break discovery
        logger.debug("pago-evidence probe failed: %s", exc)
    finally:
        if owns:
            await client.aclose()
    return out
