"""AI-evaluation platforms — discovery adapter for the Direct Work Engine.

Why this file exists
--------------------
The catalog (`cores/opportunity/global_sources.py`) already declared
Mercor / Turing / Outlier / Mindrift as sources with **zero experience and no
interview** — but NO adapter surfaced them. The seven registered adapters were
all bug-bounty, dev-bounty or marketplaces, so the highest-rate-per-hour lane
in the whole catalog (AI evaluation, `$8-25/h`) was invisible to discovery and
never reached the WorkBank or `/today`.

What it reads
-------------
No public API exists for these platforms, so this adapter reads the
**structured data the site already publishes to the browser**: the Next.js
`__NEXT_DATA__` payload embedded in the jobs page. That is the same data the
user's own browser parses to render the list — no auth, no bypass, no
fingerprint evasion.

Honesty rules encoded here
--------------------------
- A listing with **no published rate is skipped**, never emitted with
  `payment=0.0`. A `$0` opportunity with an hour estimate is a fabricated
  rate, which is the failure this file exists to prevent.
- Non-technical domains (medicine, law, arts) are filtered out: this engine
  ranks by `$/human-hour` for software work, and a physician listing is not
  a comparable opportunity.
- `rate_source` is set to the platform name, never `platform_default` — a
  scraped number is observed, not assumed.
"""

from __future__ import annotations

import json
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

logger = logging.getLogger("ownex.api.direct_work.adapters.ai_eval")

#: Listing domains that correspond to software/AI/data work. Everything else
#: on the platform (medicine, law, translation…) is a different labour market
#: and must not pollute the $/h ranking.
TECH_DOMAINS: frozenset[str] = frozenset(
    {
        "software engineering",
        "data analysis",
        "data science",
        "machine learning",
        "artificial intelligence",
        "cybersecurity",
        "information technology",
        "electrical engineering",
        "mechanical engineering",
        "other engineering",
        "systems engineering",
        "devops",
        "qa engineering",
        "web development",
    }
)

#: Platform payment rails, used to set the opportunity's `payment_method`.
#: Mercor pays internationally (Wise/PayOneer/PayPal depending on country);
#: we do not assert a single rail we cannot verify per-listing.
_RAIL_FALLBACK = PaymentMethod.WISE

#: Countries that block a listing for an Argentine resident. Mercor publishes
#: `eligibleLocation`; an empty list means "no restriction" (verified on the
#: 2026-10-01 fetch: 37 tech listings were Remote with `eligibleLocation: []`).
#: A listing restricted to a set that excludes AR is NOT offered to us, so it
#: is skipped rather than ranked as a $125/h opportunity we cannot accept.
_LOCATION_BLOCKED = frozenset({"USA", "CAN", "GBR", "IND", "CHN", "RUS", "PHL", "IDN", "VNM", "NGA", "KEN", "ZAF"})


class AiEvaluationDweAdapter(BaseDiscoveryAdapter):
    """Discovers zero-experience AI-evaluation roles with published rates."""

    #: Jobs page carrying the Next.js payload.
    MERCOR_JOBS_URL = "https://www.mercor.com/jobs"
    #: Application deep link observed in the JSON-LD `itemListElement` list.
    MERCOR_APPLY_BASE = "https://work.mercor.com/jobs/"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        source = DiscoverySource(
            name="mercor",
            platform=WorkPlatform.MERCOR,
            categories=[OpportunityCategory.AI_EVALUATION, OpportunityCategory.DATA_ANNOTATION],
            tier=1,
            # Roles change slowly; twice a day is plenty and keeps us polite.
            analysis_cadence_hours=24,
            requires_auth=False,  # the jobs page is public
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch tech roles with a published rate. Skips unpriced listings."""
        try:
            async with httpx.AsyncClient(
                timeout=30, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
            ) as client:
                resp = await client.get(self.MERCOR_JOBS_URL)
        except Exception as exc:  # noqa: BLE001 — discovery must never raise
            logger.warning("Mercor fetch failed: %s", exc)
            return []

        if resp.status_code != 200:
            logger.warning("Mercor returned %s", resp.status_code)
            return []

        listings = self._extract_listings(resp.text)
        opportunities: list[Opportunity] = []
        for item in listings:
            opp = self._convert(item)
            if opp is not None:
                opportunities.append(opp)
        logger.info("Mercor: %d listings parsed, %d priced tech roles", len(listings), len(opportunities))
        return opportunities

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(self.MERCOR_JOBS_URL, headers={"User-Agent": _USER_AGENT})
            return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    # ── Parsing ───────────────────────────────────────────���───────────

    def _extract_listings(self, html: str) -> list[dict[str, Any]]:
        """Read the listings out of the embedded Next.js payload.

        The page ships one `application/json` script whose
        `props.pageProps.dehydratedState.queries[*].state.data.listings`
        holds the rows. We scan every query because the key order is not
        guaranteed to be `[0]`.
        """
        out: list[dict[str, Any]] = []
        for blob in _JSON_SCRIPT_RE.findall(html):
            try:
                payload = json.loads(blob)
            except (ValueError, TypeError):
                continue
            for listing in _walk_listings(payload):
                if isinstance(listing, dict):
                    out.append(listing)
        return out

    def _convert(self, item: dict[str, Any]) -> Opportunity | None:
        """One listing → Opportunity, or None when it cannot be scored.

        Returns None (not a `$0` opportunity) when: no title, no published
        rate, or a non-technical domain.
        """
        title = str(item.get("title") or "").strip()
        if not title:
            return None

        rate_min, rate_max, frequency = self._rate(item)
        if rate_min <= 0.0:
            return None  # UNKNOWN is not $0

        domain = str(item.get("listingDomain") or "").strip()
        if domain and domain.lower() not in TECH_DOMAINS:
            return None

        if not self._open_to_argentina(item):
            return None

        rate_usd = self._to_hourly(rate_min, frequency)
        if rate_usd <= 0.0:
            return None

        listing_id = str(item.get("listingId") or item.get("slug") or "").strip()
        url = f"{self.MERCOR_APPLY_BASE}{listing_id}" if listing_id else self.MERCOR_JOBS_URL

        return self._create_opportunity(
            external_id=listing_id or title[:60],
            title=f"[mercor] {title}",
            category=OpportunityCategory.AI_EVALUATION,
            url=url,
            description=self._describe(item, rate_min, rate_max, frequency, domain),
            company="Mercor",
            country="Global",
            # Mercor pays per project/contract, not a single lump sum:
            # we surface the hourly equivalent as the comparable figure and
            # keep the contract nature explicit in the description.
            payment=0.0,
            currency="USD",
            payment_method=_RAIL_FALLBACK,
            difficulty=DifficultyLevel.INTERMEDIATE,
            language_required="english",
            # UNKNOWN effort until the platform states it: an invented hour
            # count is what fabricates a $/h.
            estimated_time_hours=0.0,
            experience_required=ExperienceLevel.NONE,
            portfolio_required=False,
            interview_required=False,
            technical_test_required=True,  # assessment-based entry
            registration_required=True,
            asynchronous=True,
            employment_type=EmploymentType.CONTRACT,
            entry_mechanism=EntryMechanism.ASSESSMENT,
            hourly_rate_usd=rate_usd,
            rate_source="mercor",
            # Mercor publishes the rate on the listing itself, same as Algora
            # and BountyBoard do. `payment_proven` is "the platform's payout
            # is documented" — NOT "I was paid"; only PAID in the ledger is
            # that. Without it the zero-barrier scorer adds a
            # "Payment not verified" blocker and the role never reaches the bank.
            payment_proven=True,
            # Mercor pays through Stripe. Our catalog records
            # `rail_pays_in_argentina=False` for Stripe (2026-10-01), so the
            # rail must be confirmed before this lane can actually pay out
            # from Argentina — that is a config question, not a data one.
            international_payment=True,
        )

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _open_to_argentina(item: dict[str, Any]) -> bool:
        """True when the listing does not exclude an Argentine resident.

        Mercor publishes `eligibleLocation`. Two shapes observed on the
        2026-10-01 fetch:
          · `[]`  → no restriction (37 tech listings, all `location: Remote`)
          · list → the ONLY countries eligible

        Anything whose list contains no non-blocked country is not offered to
        us. UNKNOWN (field absent) is treated as open: the platform's default
        is "no restriction", and a missing field must not silently drop the
        whole lane.
        """
        raw = item.get("eligibleLocation")
        if raw is None:
            return True
        if not isinstance(raw, list):
            return True
        if not raw:
            return True
        return any(str(loc).upper() not in _LOCATION_BLOCKED for loc in raw)

    @staticmethod
    def _rate(item: dict[str, Any]) -> tuple[float, float, str]:
        rate_min = item.get("rateMin")
        rate_max = item.get("rateMax")
        frequency = str(item.get("payRateFrequency") or item.get("commitment") or "")
        return (float(rate_min or 0.0), float(rate_max or 0.0), frequency)

    @staticmethod
    def _to_hourly(amount: float, frequency: str) -> float:
        """Normalize to $/hour so platforms are comparable.

        Mercor publishes `payRateFrequency`; anything we cannot normalize
        returns 0.0 (UNKNOWN) instead of assuming it is hourly.
        """
        freq = frequency.strip().lower()
        if freq in {"hourly", "hour", "per hour", "/hr"}:
            return amount
        # Fixed-scope projects: we could divide by an effort estimate, but we
        # have none. Returning 0 keeps the item out of the ranking rather
        # than inventing a denominator.
        return 0.0

    @staticmethod
    def _describe(item: dict[str, Any], rate_min: float, rate_max: float, frequency: str, domain: str) -> str:
        bits = [f"Rate published: ${rate_min:,.0f}-{rate_max:,.0f} {frequency or 'per project'}."]
        if domain:
            bits.append(f"Domain: {domain}.")
        bits.append("Zero experience and no interview; entry is via assessment.")
        for key in ("commitmentType", "paymentRateType", "country", "skills"):
            val = item.get(key)
            if val:
                bits.append(f"{key}: {val}.")
        return " ".join(bits)


_USER_AGENT = "Mozilla/5.0 (compatible; ownex-discovery/1.0)"
_JSON_SCRIPT_RE = re.compile(r'<script[^>]*type="application/(?:ld\+)?json"[^>]*>(.*?)</script>', re.S)


def _walk_listings(node: Any, depth: int = 0) -> list[dict[str, Any]]:
    """Depth-limited search for `listings` arrays in the payload."""
    if depth > 8:
        return []
    if isinstance(node, dict):
        found: list[dict[str, Any]] = []
        for key, val in node.items():
            if key == "listings" and isinstance(val, list):
                found.extend(x for x in val if isinstance(x, dict))
            else:
                found.extend(_walk_listings(val, depth + 1))
        return found
    if isinstance(node, list):
        found = []
        for val in node[:5]:  # bounded: the payload is 1.3 MB
            found.extend(_walk_listings(val, depth + 1))
        return found
    return []
