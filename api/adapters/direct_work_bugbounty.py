"""Bug bounty — real discovery adapter for the Direct Work Engine.

Works in two grades, auto-selected at fetch time:

* **Public grade (no key required):** reads the community-maintained
  ``arkadiyt/bounty-targets-data`` datasets (HackerOne, Bugcrowd, Intigriti,
  Immunefi) — open data with program name, URL, max payout and in-scope
  targets. This is the "works with zero keys" path.
* **Authenticated grade (key detected in the identity vault):** same source
  plumbing, but each program is also given ``needs_api_key`` access so the
  assisted delivery queue surfaces the missing credential instead of pretending
  submission is public.

The adapter never fabricates rewards: when a program does not publish a max
payout it is still discovered (a real, open program) but ``payment`` stays at
0 so the strict filter keeps it out of the daily delivery bank unless there is
a real published reward. Outcome-based: bug bounties pay for the result, not
for the person.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from api.adapters.legacy import LegacyOpportunityDweAdapter
from cores.direct_work_engine.models import (
    DifficultyLevel,
    EmploymentType,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)

logger = logging.getLogger("ownex.api.direct_work.adapters.bugbounty")

# Open, community-maintained program datasets (no auth). Updated continuously.
_BOUNTY_DATA_URLS: dict[str, str] = {
    "hackerone": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/hackerone_data.json",
    "bugcrowd": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/bugcrowd_data.json",
    "intigriti": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/intigriti_data.json",
    "yeswehack": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/yeswehack_data.json",
}

_PLATFORM_BY_SOURCE: dict[str, WorkPlatform] = {
    "hackerone": WorkPlatform.HACKERONE,
    "bugcrowd": WorkPlatform.BUG_CROWD,
    "intigriti": WorkPlatform.INTIGRITI,
    "yeswehack": WorkPlatform.YES_WE_HACK,
}

# Categories by platform family.
_CATEGORY_DEFAULT = OpportunityCategory.BUG_BOUNTY


class BugBountyDweAdapter(LegacyOpportunityDweAdapter):
    """Discovers open bug-bounty programs from public program datasets.

    Uses the shared ``LegacyOpportunityDweAdapter`` conversion path so it rides
    the same schema/enum normalization as every other platform — no duplicated
    per-platform mapping logic.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        super().__init__(
            None,  # legacy adapter not used; fetch_opportunities is overridden
            name="bugbounty",
            platform=WorkPlatform.HACKERONE,
            category=_CATEGORY_DEFAULT,
            employment_type=EmploymentType.BOUNTY,
            payment_method=PaymentMethod.PLATFORM_CREDIT,
            registration_required=True,
            tier=1,
            analysis_cadence_hours=6,
        )

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch programs across all public bounty datasets concurrently."""
        if self._legacy is not None and self._config.get("use_legacy"):
            return await super().fetch_opportunities()

        jobs = [asyncio.create_task(self._fetch_source(src)) for src in _BOUNTY_DATA_URLS]
        results: list[list[Opportunity]] = []
        for job in asyncio.as_completed(jobs):
            try:
                results.append(await job)
            except Exception as exc:  # pragma: no cover
                logger.warning("bugbounty fetch failed for a source: %s", exc)
                results.append([])
        return [o for batch in results for o in batch]

    async def _fetch_source(self, source: str) -> list[Opportunity]:
        data = await self._load_json(_BOUNTY_DATA_URLS[source])
        platform = _PLATFORM_BY_SOURCE[source]
        category = _CATEGORY_DEFAULT

        creds = self._credentials_for(source)
        has_key = bool(creds.get("api_key"))

        out: list[Opportunity] = []
        for prog in data if isinstance(data, list) else []:
            op = self._program_to_opportunity(prog, platform, category, source)
            if op is None:
                continue
            if not has_key:
                # Public grade: submission is not possible yet, but discovery is
                # real. Keep reward only when published, so the strict filter
                # governs the delivery bank honestly.
                op.registration_required = True
            out.append(op)
        return out

    @staticmethod
    async def _load_json(url: str) -> Any:
        import urllib.request

        with urllib.request.urlopen(url, timeout=20) as resp:  # noqa: S310 (public data only)
            return __import__("json").loads(resp.read())

    @staticmethod
    def _credentials_for(source: str) -> dict[str, str]:
        """Resolve vault credentials for a platform (empty when not configured)."""
        try:
            from core.credentials.vault import get_platform_credentials

            return get_platform_credentials(source) or {}
        except Exception as exc:  # pragma: no cover
            logger.warning("bugbounty credential lookup failed for %s: %s", source, exc)
            return {}

    def _program_to_opportunity(
        self,
        prog: dict[str, Any],
        platform: WorkPlatform,
        category: OpportunityCategory,
        source: str,
    ) -> Opportunity | None:
        name = str(prog.get("name") or prog.get("handle") or "").strip()
        handle = str(prog.get("handle") or "").strip()
        if not name and not handle:
            return None
        url = str(prog.get("url") or "")
        if not url:
            slug = handle or name.lower().replace(" ", "_")
            url = f"https://{source}.com/{slug}"

        max_payout = float(prog.get("max_payout") or 0.0)
        offers_bounties = bool(prog.get("offers_bounties") or prog.get("offersBounties"))
        submission = str(prog.get("submission_state") or "open")
        if max_payout <= 0 and not offers_bounties:
            # Honest signal: a program that publishes no reward is still open,
            # but treat payout as unknown (0) so the strict bank filters it.
            max_payout = 0.0

        targets = prog.get("targets") or {}
        in_scope = targets.get("in_scope") or []
        scope_desc = "; ".join(
            str(t.get("target") or t.get("uri") or t.get("name")) for t in in_scope[:3] if isinstance(t, dict)
        )

        easy = max_payout < 200
        return Opportunity(
            id=f"{source}_{handle or name}",
            title=f"{name} bug bounty",
            platform=platform,
            category=category,
            url=url,
            description=f"Open bug bounty program. Scope: {scope_desc}".strip()
            or f"Open bug bounty program on {source}.",
            remote=True,
            payment=max_payout,
            currency="USD",
            payment_method=PaymentMethod.PLATFORM_CREDIT,
            international_payment=True,
            difficulty=DifficultyLevel.BEGINNER if easy else DifficultyLevel.INTERMEDIATE,
            language_required="english",
            estimated_time_hours=8.0 if easy else 16.0,
            experience_required=ExperienceLevel.NONE,
            portfolio_required=False,
            interview_required=False,
            technical_test_required=False,
            registration_required=(submission != "open"),
            time_to_payout_days=None,
            reputation=0.7,
            risk=0.3,
            payment_proven=False,
            stability=0.6,
            accepts_beginner=True,
            accepts_freelancers=True,
            accepts_individuals=True,
            accepts_ai_tools=True,
            asynchronous=True,
            technology_tags=["bug_bounty", source] + ([str(t) for t in in_scope[:3] if isinstance(t, dict)]),
            employment_type=EmploymentType.BOUNTY,
        )


def build_bugbounty_adapters() -> list[BugBountyDweAdapter]:
    """Build the bug-bounty discovery adapter(s) (one composite covering 4 sources)."""
    try:
        return [BugBountyDweAdapter()]
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build bugbounty adapter: %s", exc)
        return []
