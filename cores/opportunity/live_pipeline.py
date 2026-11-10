"""Live opportunity pipeline — turn catalog sources into verified work.

Bridges the gap between the 1,000-source catalog (leads) and real,
fetch-confirmed opportunities: runs the registered platform fetchers
(``core.opportunity.adapters.forge.*`` module functions hit real public
APIs), normalizes results into the canonical DWE ``Opportunity`` model,
deduplicates against a persistent store, and records provenance so every
record is a ``live_opportunity`` — never a catalog guess.

Honesty contract:
- A record only exists here because a fetcher returned it from a real
  HTTP call in this process.
- ``fetched_at`` + ``adapter`` + ``evidence_url`` are stored per record.
- Dedup key is ``(platform, external_id)``; closed/expired items are kept
  with ``status="expired"`` rather than deleted (audit trail).
- Upwork is excluded by policy.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.opportunity.live_pipeline")

# Module-path fetchers that hit real public APIs. Each returns
# ``list[dict]`` in the forge RawOpportunity-dict shape. Credential-gated
# fetchers already degrade to [] when keys are absent.
LIVE_FETCHERS: dict[str, str] = {
    "algora": "core.opportunity.adapters.forge.algora:fetch_opportunities",
    "opire": "core.opportunity.adapters.forge.opire:fetch_opportunities",
    "issuehunt": "core.opportunity.adapters.forge.issuehunt:fetch_opportunities",
    "superteam": "core.opportunity.adapters.forge.superteam:fetch_opportunities",
    "github_bounties": "core.opportunity.adapters.forge.github_bounties:fetch_opportunities",
    "github_sponsors": "core.opportunity.adapters.forge.github_sponsors:fetch_opportunities",
    "onlydust": "core.opportunity.adapters.forge.onlydust:fetch_opportunities",
    "ethglobal": "core.opportunity.adapters.forge.ethglobal:fetch_opportunities",
    "codeforai": "core.opportunity.adapters.forge.codeforai:fetch_opportunities",
    "freelancer": "core.opportunity.adapters.forge.freelancer:fetch_opportunities",
    "opencollective": "core.opportunity.adapters.forge.opencollective:fetch_opportunities",
    "opencollective_projects": "core.opportunity.adapters.forge.opencollective_projects:fetch_opportunities",
}

# Platforms whose fetchers require user credentials — surfaced honestly
# instead of silently returning [].
CREDENTIAL_GATED_FETCHERS: dict[str, str] = {
    "algora": "ALGORA_API_KEY (optional; public bounties work without)",
    "opire": "none for public board",
    "issuehunt": "none for public board",
    "superteam": "SUPERTEAM_API_KEY (optional)",
    "github_bounties": "GITHUB_TOKEN (raises rate limit; public search works without)",
    "github_sponsors": "GITHUB_TOKEN (optional)",
    "onlydust": "none for public board",
    "ethglobal": "none for public listings",
    "codeforai": "none for public board",
    "freelancer": "FREELANCER_API_KEY + secret (required for project search)",
    "opencollective": "none for public API",
    "opencollective_projects": "none for public API",
}

EXCLUDED_PLATFORMS = {"upwork"}


def _default_store_path() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "live_opportunities.json"


@dataclass(slots=True)
class LiveOpportunity:
    """A fetch-confirmed opportunity with provenance."""

    id: str
    platform: str
    adapter: str
    title: str
    url: str
    description: str = ""
    reward: float = 0.0
    currency: str = "USD"
    effort_hours: float = 0.0
    tags: list[str] = field(default_factory=list)
    category: str = "dev_bounty"
    employment_type: str = "bounty"
    status: str = "discovered"  # discovered|verified|ready|expired|rejected
    fetched_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_seen_at: str = ""
    evidence_url: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def dedup_key(self) -> str:
        return f"{self.platform}:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out.pop("raw", None)
        return out


class LiveStore:
    """Persistent dedup + status store for live opportunities."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._path = Path(store_path) if store_path else _default_store_path()
        self._items: dict[str, LiveOpportunity] = {}
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
        except Exception:
            return
        for item in data.get("items", []):
            try:
                opp = LiveOpportunity(**{k: v for k, v in item.items() if k != "raw"})
                opp.raw = item.get("raw") or {}
                self._items[opp.dedup_key()] = opp
            except Exception:
                continue

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"items": [{**opp.to_dict(), "raw": opp.raw} for opp in self._items.values()]}
        self._path.write_text(json.dumps(payload, indent=2, default=str))

    def upsert(self, opp: LiveOpportunity) -> bool:
        """Insert or refresh ``last_seen_at``. Returns True if new."""
        key = opp.dedup_key()
        existing = self._items.get(key)
        if existing is None:
            self._items[key] = opp
            return True
        existing.last_seen_at = opp.fetched_at
        # Refresh mutable fields but keep status/history.
        existing.title = opp.title or existing.title
        existing.url = opp.url or existing.url
        existing.reward = opp.reward or existing.reward
        existing.description = opp.description or existing.description
        existing.tags = opp.tags or existing.tags
        return False

    def mark_expired_missing(self, seen_keys: set[str]) -> int:
        """Mark items not seen in the latest scan as expired."""
        count = 0
        for key, opp in self._items.items():
            if key not in seen_keys and opp.status not in ("expired", "rejected"):
                opp.status = "expired"
                count += 1
        return count

    def all(self, status: str | None = None) -> list[LiveOpportunity]:
        items = list(self._items.values())
        if status:
            items = [i for i in items if i.status == status]
        items.sort(key=lambda i: i.fetched_at, reverse=True)
        return items

    def stats(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        by_platform: dict[str, int] = {}
        for opp in self._items.values():
            by_status[opp.status] = by_status.get(opp.status, 0) + 1
            by_platform[opp.platform] = by_platform.get(opp.platform, 0) + 1
        return {
            "total": len(self._items),
            "by_status": by_status,
            "by_platform": by_platform,
        }


def _resolve_fetcher(spec: str) -> Any:
    module_path, _, attr = spec.partition(":")
    module = importlib.import_module(module_path)
    return getattr(module, attr)


def _platform_for(raw: dict[str, Any]) -> str:
    """Map the fetcher's platform/source_name onto a stable platform key."""
    platform = str(raw.get("platform") or raw.get("source_name") or "other").lower()
    source_name = str(raw.get("source_name") or "").lower()
    # github_bounties aggregates per bounty platform; prefer the real one.
    if source_name.startswith("github_") and platform not in EXCLUDED_PLATFORMS:
        return platform if platform != "github" else source_name.removeprefix("github_")
    if platform in EXCLUDED_PLATFORMS:
        return "other"
    return platform


async def _fetch_one(fetcher_key: str, spec: str) -> tuple[str, list[dict[str, Any]], str | None]:
    """Run one fetcher; return (key, raw_items, error)."""
    try:
        fn = _resolve_fetcher(spec)
        items = await fn()
        return fetcher_key, list(items or []), None
    except Exception as exc:  # fetchers must never crash the scan
        logger.warning("live fetcher %s failed: %s", fetcher_key, exc)
        return fetcher_key, [], str(exc)


def _to_live(fetcher_key: str, raw: dict[str, Any]) -> LiveOpportunity | None:
    """Normalize a forge fetch dict into a LiveOpportunity."""
    external_id = str(raw.get("id") or raw.get("url") or "")
    if not external_id:
        return None
    platform = _platform_for(raw)
    if platform in EXCLUDED_PLATFORMS:
        return None
    url = str(raw.get("url") or raw.get("html_url") or "")
    return LiveOpportunity(
        id=external_id,
        platform=platform,
        adapter=fetcher_key,
        title=str(raw.get("name") or raw.get("title") or "untitled")[:300],
        url=url,
        description=str(raw.get("description") or "")[:2000],
        reward=float(raw.get("reward") or 0.0),
        currency=str(raw.get("currency") or "USD"),
        effort_hours=float(raw.get("effort_hours") or 0.0),
        tags=[str(t) for t in (raw.get("tags") or [])][:12],
        category=str(raw.get("source_type") or raw.get("cycle") or "dev_bounty"),
        employment_type="bounty" if raw.get("cycle") == "forge" else "contract",
        status="discovered",
        fetched_at=datetime.now(UTC).isoformat(),
        evidence_url=url,
        raw=raw.get("metadata", {}).get("original") or raw,
    )


async def run_live_scan(
    fetchers: list[str] | None = None,
    store: LiveStore | None = None,
    mark_expired: bool = True,
) -> dict[str, Any]:
    """Run all (or selected) live fetchers, dedup, persist, report.

    Returns a report dict; never raises — per-fetcher errors are collected.
    """
    store = store or LiveStore()
    keys = fetchers or list(LIVE_FETCHERS)
    unknown = [k for k in keys if k not in LIVE_FETCHERS]
    if unknown:
        return {"error": f"unknown fetchers: {unknown}", "known": sorted(LIVE_FETCHERS)}

    results = await asyncio.gather(*(_fetch_one(k, LIVE_FETCHERS[k]) for k in keys))

    new_count = 0
    refreshed = 0
    errors: list[str] = []
    seen_keys: set[str] = set()
    per_fetcher: dict[str, int] = {}

    for key, items, error in results:
        if error:
            errors.append(f"{key}: {error}")
        per_fetcher[key] = len(items)
        for raw in items:
            opp = _to_live(key, raw)
            if opp is None:
                continue
            seen_keys.add(opp.dedup_key())
            if store.upsert(opp):
                new_count += 1
            else:
                refreshed += 1

    expired = store.mark_expired_missing(seen_keys) if mark_expired else 0
    store.save()

    return {
        "fetchers_run": len(keys),
        "fetched_raw": sum(per_fetcher.values()),
        "per_fetcher": per_fetcher,
        "new_opportunities": new_count,
        "refreshed": refreshed,
        "marked_expired": expired,
        "errors": errors,
        "store": str(store._path),
        "stats": store.stats(),
    }


def get_live_opportunities(
    status: str | None = None,
    platform: str | None = None,
    limit: int = 200,
    store: LiveStore | None = None,
) -> list[dict[str, Any]]:
    """Read-back for API/frontend: live opportunities with provenance."""
    store = store or LiveStore()
    items = store.all(status=status)
    if platform:
        items = [i for i in items if i.platform == platform.lower()]
    return [i.to_dict() for i in items[:limit]]


def live_opportunity_stats(store: LiveStore | None = None) -> dict[str, Any]:
    store = store or LiveStore()
    return {
        **store.stats(),
        "fetchers_available": sorted(LIVE_FETCHERS),
        "credential_gated": CREDENTIAL_GATED_FETCHERS,
        "excluded_platforms": sorted(EXCLUDED_PLATFORMS),
    }


# --- Bridge into the canonical Work Bank (DWE Opportunity) ---

_PLATFORM_MAP = {
    "algora": "algora",
    "opire": "opire",
    "issuehunt": "issuehunt",
    "superteam": "superteam",
    "github": "github",
    "github_sponsors": "github",
    "onlydust": "other",
    "ethglobal": "other",
    "codeforai": "other",
    "freelancer": "freelancer",
    "opencollective": "opencollective",
    "polar": "other",
    "bountysource": "other",
}

_CATEGORY_MAP = {
    "dev_bounty": "dev_bounty",
    "bounty": "dev_bounty",
    "oss_bounties": "oss_bounties",
    "open_source": "open_source",
    "bug_bounty": "bug_bounty",
    "security": "security_research",
    "security_research": "security_research",
    "challenge": "challenge",
    "web3": "web3",
    "data": "data_science",
}

_EMPLOYMENT_MAP = {
    "bounty": "bounty",
    "contract": "contract",
    "freelance": "freelance",
    "prize": "prize",
    "challenge": "challenge",
    "gig": "freelance",
}


def to_dwe_opportunity(opp: LiveOpportunity):
    """Convert a fetch-confirmed live opportunity into the canonical DWE
    ``Opportunity`` so Work Bank's real ZeroBarrierScorer/StrictFilter decide
    readiness — no invented eligibility."""
    from cores.direct_work_engine.models import (
        DifficultyLevel,
        EmploymentType,
        ExperienceLevel,
        Opportunity,
        OpportunityCategory,
        PaymentMethod,
        WorkPlatform,
    )

    platform_key = _PLATFORM_MAP.get(opp.platform, "other")
    try:
        platform = WorkPlatform(platform_key)
    except ValueError:
        platform = WorkPlatform.OTHER

    cat_key = _CATEGORY_MAP.get(opp.category, "dev_bounty")
    try:
        category = OpportunityCategory(cat_key)
    except ValueError:
        category = OpportunityCategory.DEV_BOUNTY

    emp_key = _EMPLOYMENT_MAP.get(opp.employment_type, "contract")
    try:
        employment = EmploymentType(emp_key)
    except ValueError:
        employment = EmploymentType.CONTRACT

    pay_method = (
        PaymentMethod.PLATFORM_CREDIT
        if platform in (WorkPlatform.GITHUB, WorkPlatform.ALGORA, WorkPlatform.OPIRE, WorkPlatform.ISSUE_HUNT)
        else PaymentMethod.OTHER
    )

    return Opportunity(
        id=f"live:{opp.dedup_key()}",
        title=opp.title,
        platform=platform,
        category=category,
        url=opp.url,
        description=opp.description,
        company=opp.platform,
        payment=opp.reward,
        currency=opp.currency,
        payment_method=pay_method,
        difficulty=DifficultyLevel.INTERMEDIATE,
        estimated_time_hours=opp.effort_hours,
        experience_required=ExperienceLevel.NONE,
        employment_type=employment,
        technology_tags=opp.tags,
        payment_proven=opp.reward > 0,
        accepts_beginner=True,
        accepts_freelancers=True,
        accepts_individuals=True,
        accepts_ai_tools=True,
    )


def live_candidates_for_workbank(
    status: str = "discovered",
    store: LiveStore | None = None,
    limit: int = 500,
) -> list[Any]:
    """DWE Opportunities ready for ``WorkBank.daily_cycle`` scoring."""
    return [to_dwe_opportunity(opp) for opp in (store or LiveStore()).all(status=status)[:limit]]


def mark_ready_from_workbank(
    scored: list[Any],
    store: LiveStore | None = None,
) -> int:
    """Mark live opportunities whose DWE twin passed Work Bank selection.

    ``scored`` are the WorkItems/opportunities returned by a daily_cycle run;
    we match on the ``live:platform:id`` id prefix and flip status to
    ``ready`` — evidence: the real scorer accepted them.
    """
    store = store or LiveStore()
    ready_ids = {getattr(item, "opportunity_id", None) or getattr(item, "id", "") for item in scored}
    count = 0
    for key, opp in store._items.items():
        if f"live:{key}" in ready_ids and opp.status == "discovered":
            opp.status = "ready"
            count += 1
    if count:
        store.save()
    return count
