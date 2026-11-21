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
from types import SimpleNamespace
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
    "makefun": "core.opportunity.adapters.forge.makefun:fetch_opportunities",
    # Agent-native markets (class-based adapters, public read-only APIs).
    # Registration/claim/submission stays blocked on user authorization.
    "taskmarket": "core.opportunity.adapters.agent_markets:TaskmarketAdapter",
    "agent_hansa": "core.opportunity.adapters.agent_markets:AgentHansaAdapter",
    "agentics": "core.opportunity.adapters.agent_markets:AgenticsAdapter",
}

# Class-based security adapters (OpportunityAdapter → list[RawOpportunity]).
# Spec format: "module.path:ClassName". Many work unauthenticated via public
# program listings; credential-gated ones degrade gracefully.
SECURITY_FETCHERS: dict[str, str] = {
    "hackerone": "cores.opportunity.adapters.security.hackerone:HackerOneAdapter",
    "bugcrowd": "cores.opportunity.adapters.security.bugcrowd:BugcrowdAdapter",
    "intigriti": "cores.opportunity.adapters.security.intigriti:IntigritiAdapter",
    "yeswehack": "cores.opportunity.adapters.security.yeswehack:YesWeHackAdapter",
    "immunefi": "cores.opportunity.adapters.security.immunefi:ImmunefiAdapter",
    "synack": "cores.opportunity.adapters.security.synack:SynackAdapter",
    "cantina": "cores.opportunity.adapters.security.cantina:CantinaAdapter",
    "sherlock": "cores.opportunity.adapters.security.sherlock:SherlockAdapter",
    "code4rena": "cores.opportunity.adapters.security.code4rena:Code4renaAdapter",
    "codehawks": "cores.opportunity.adapters.security.codehawks:CodeHawksAdapter",
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
    # Agent markets: discovery is public; acting on tasks requires the
    # user's own account registration on each platform.
    "taskmarket": "TASKMARKET agent registration (user authorization required)",
    "agent_hansa": "AGENT_HANSA account registration (user authorization required)",
    "agentics": "per-origin market registration via agentics.page (user authorization required)",
    # Security platforms: public program listings work without auth;
    # researcher API tokens unlock private/triage data.
    "hackerone": "HACKERONE_API_USERNAME + HACKERONE_API_TOKEN (optional enrichment)",
    "bugcrowd": "BUGCROWD_API_TOKEN (optional)",
    "intigriti": "INTIGRITI_API_TOKEN (optional)",
    "yeswehack": "YESWEHACK_API_TOKEN (optional)",
    "immunefi": "IMMUNEFI_API_TOKEN (optional)",
    "synack": "SYNCACK credentials via application (invite-only platform)",
    "cantina": "none for public contests",
    "sherlock": "none for public contests",
    "code4rena": "none for public contests",
    "codehawks": "none for public contests",
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
    # discovered|eligibility_checked|ready|in_progress|submitted|accepted|
    # paid|rejected|expired — external states require evidence (see
    # EXTERNAL_TRANSITIONS); advertised reward is never income.
    status: str = "discovered"
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
        # Reappeared in a fresh fetch → live evidence again.
        if existing.status == "expired":
            existing.status = "discovered"
        return False

    def mark_expired_missing(self, seen_keys: set[str], scanned_adapters: set[str] | None = None) -> int:
        """Mark items not seen in the latest scan as expired.

        Only items produced by adapters that actually ran are eligible —
        a partial scan must not expire platforms it never queried.
        """
        count = 0
        for key, opp in self._items.items():
            if scanned_adapters is not None and opp.adapter not in scanned_adapters:
                continue
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
    """Resolve ``module:attr`` to a zero-arg async callable.

    Supports both module-level ``fetch_opportunities`` functions and
    class-based ``OpportunityAdapter`` implementations (``module:ClassName``
    → instantiate, then call ``fetch_opportunities()``).
    """
    module_path, _, attr = spec.partition(":")
    module = importlib.import_module(module_path)
    target = getattr(module, attr)
    if isinstance(target, type):
        adapter = target()

        async def _call() -> list[Any]:
            items = await adapter.fetch_opportunities()
            return [_raw_to_dict(i) for i in items]

        return _call
    return target


def _raw_to_dict(item: Any) -> dict[str, Any]:
    """Normalize RawOpportunity dataclass (or dict) into a plain dict."""
    if isinstance(item, dict):
        return item
    if hasattr(item, "__dataclass_fields__"):
        from dataclasses import asdict

        return asdict(item)
    return dict(vars(item)) if hasattr(item, "__dict__") else {"id": str(item)}


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


def _best_category(raw: dict[str, Any]) -> str:
    """Pick the most specific known category from cycle/source_type/platform."""
    for key in (raw.get("cycle"), raw.get("source_type"), raw.get("platform")):
        k = str(key or "").lower()
        if k in _CATEGORY_MAP:
            return k
        if k in ("security", "platform"):
            return "bug_bounty"  # security-cycle items are vulnerability work
    return "dev_bounty"


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
        category=_best_category(raw),
        employment_type="bounty" if raw.get("cycle") == "forge" else "contract",
        status="discovered",
        fetched_at=datetime.now(UTC).isoformat(),
        evidence_url=url,
        raw=(raw.get("metadata") or {}).get("original") or raw,
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
    registry = {**LIVE_FETCHERS, **SECURITY_FETCHERS}
    keys = fetchers or list(registry)
    unknown = [k for k in keys if k not in registry]
    if unknown:
        return {"error": f"unknown fetchers: {unknown}", "known": sorted(registry)}

    results = await asyncio.gather(*(_fetch_one(k, registry[k]) for k in keys))

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

    # Only expire items from adapters that ran successfully — a failed or
    # unscanned fetcher must not mass-expire its platform's items.
    healthy_adapters = {key for key, _, error in results if error is None}
    expired = store.mark_expired_missing(seen_keys, scanned_adapters=healthy_adapters) if mark_expired else 0
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
        "fetchers_available": sorted({**LIVE_FETCHERS, **SECURITY_FETCHERS}),
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
        if platform
        in (
            WorkPlatform.GITHUB,
            WorkPlatform.ALGORA,
            WorkPlatform.OPIRE,
            WorkPlatform.ISSUE_HUNT,
        )
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
    status: str | set[str] | None = None,
    store: LiveStore | None = None,
    limit: int = 500,
) -> list[Any]:
    """DWE Opportunities ready for ``WorkBank.daily_cycle`` scoring.

    Defaults to all actionable states (``discovered`` +
    ``eligibility_checked``) — ``ready``/``expired``/``rejected`` are
    terminal-ish and excluded.
    """
    store = store or LiveStore()
    statuses = {status} if isinstance(status, str) else (status or {"discovered", "eligibility_checked"})
    items = [opp for opp in store.all() if opp.status in statuses][:limit]
    return [to_dwe_opportunity(opp) for opp in items]


def promote_live_to_workbank(
    store: LiveStore | None = None,
    target: int | None = None,
) -> dict[str, Any]:
    """Run the canonical Work Bank cycle over live opportunities.

    ``WorkBank.daily_cycle`` applies the real ZeroBarrierScorer +
    StrictFilter and creates WorkItems (``ready_to_deliver`` /
    ``needs_access``). Live items that land ``ready_to_deliver`` are
    marked ``ready`` in the live store — evidence: the real scorer and
    access-check accepted them. Never raises.
    """
    store = store or LiveStore()
    try:
        from cores.direct_work_engine.workbank import get_workbank

        candidates = live_candidates_for_workbank(store=store)
        if not candidates:
            return {"promoted": 0, "reason": "no_candidates"}
        bank = get_workbank()
        summary = bank.daily_cycle(candidates, target=target or len(candidates))
        ready_ids = {item_id for item_id, item in bank._items.items() if getattr(item, "ready_to_deliver", False)}
        marked = mark_ready_from_workbank([SimpleNamespace(id=i) for i in ready_ids], store)
        ledger_sync = _sync_advertised_to_ledger(store)
        return {
            "candidates": len(candidates),
            "workbank_summary": summary if isinstance(summary, dict) else str(summary),
            "ready_to_deliver": len(ready_ids),
            "marked_ready": marked,
            "ledger_advertised": ledger_sync,
        }
    except Exception as exc:
        logger.warning("promote_live_to_workbank failed: %s", exc)
        return {"error": str(exc)}


def _sync_advertised_to_ledger(store: LiveStore) -> int:
    """Record advertised rewards in the Revenue Ledger (never as income).

    Only items with a numeric reward and an actionable status get an
    ``advertised`` entry — estimates stay in the advertised bucket.
    """
    try:
        from cores.opportunity.revenue_ledger import RevenueLedger

        ledger = RevenueLedger()
        count = 0
        for key, opp in store._items.items():
            if opp.status in ("expired", "rejected"):
                continue
            reward = opp.reward
            if not isinstance(reward, (int, float)) or reward <= 0:
                continue
            item_id = f"live:{key}"
            existing = ledger._store.get(item_id)
            latest = ((existing or {}).get("payload") or {}).get("finance", {}).get("latest", {})
            if "advertised" in latest:
                continue
            res = ledger.record_amount(
                item_id,
                "advertised",
                float(reward),
                currency=opp.currency or "USD",
                evidence={"source": "live_pipeline", "url": opp.url},
            )
            if "entry" in res:
                count += 1
        return count
    except Exception as exc:
        logger.warning("ledger advertised sync failed: %s", exc)
        return -1


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
        if f"live:{key}" in ready_ids and opp.status in (
            "discovered",
            "eligibility_checked",
        ):
            opp.status = "ready"
            count += 1
    if count:
        store.save()
    return count


# --- Eligibility evaluation (evidence-based, unknown stays unknown) ---

# Platform key → likely catalog source names (fuzzy match fallback).
_PLATFORM_SOURCE_HINTS: dict[str, list[str]] = {
    "algora": ["Algora"],
    "opire": ["Opire"],
    "issuehunt": ["IssueHunt"],
    "superteam": ["Superteam Earn", "Superteam"],
    "github": ["GitHub"],
    "github_sponsors": ["GitHub Sponsors"],
    "onlydust": ["OnlyDust"],
    "ethglobal": ["ETHGlobal", "DoraHacks"],
    "codeforai": ["Code4AI", "CodeForAI"],
    "freelancer": ["Freelancer"],
    "opencollective": ["Open Collective", "OpenCollective"],
    "polar": ["Polar"],
    "bountysource": ["BountySource"],
    "hackerone": ["HackerOne"],
    "bugcrowd": ["Bugcrowd"],
    "intigriti": ["Intigriti"],
    "yeswehack": ["YesWeHack"],
    "immunefi": ["Immunefi"],
    "synack": ["Synack"],
    "cantina": ["Cantina"],
    "sherlock": ["Sherlock"],
    "code4rena": ["Code4rena", "Code4RENA"],
    "codehawks": ["CodeHawks", "Cyfrin"],
    "makefun": ["make.fun"],
}


def _catalog_index() -> dict[str, Any]:
    """name-lowered → SourceDefinition from the canonical catalog."""
    try:
        from cores.opportunity.sources_expansion import get_all_sources

        return {s.name.strip().lower(): s for s in get_all_sources()}
    except Exception:
        return {}


def _match_source(opp: LiveOpportunity, index: dict[str, Any]) -> Any | None:
    for hint in _PLATFORM_SOURCE_HINTS.get(opp.platform, []):
        src = index.get(hint.lower())
        if src is not None:
            return src
    # Fallback: substring match on platform name
    for name, src in index.items():
        if opp.platform in name or name in opp.platform:
            return src
    return None


def evaluate_eligibility(opp: LiveOpportunity, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate one live opportunity against catalog eligibility metadata.

    Returns per-dimension status: ``yes`` / ``no`` / ``unknown`` — unknown
    is never collapsed into no. Evidence cites the catalog source used.
    """
    catalog = catalog if catalog is not None else _catalog_index()
    src = _match_source(opp, catalog)

    def _tri(state: bool | None) -> str:
        return "unknown" if state is None else ("yes" if state else "no")

    report: dict[str, Any] = {
        "opportunity_id": opp.dedup_key(),
        "platform": opp.platform,
        "argentina_compatible": "unknown",
        "payment_method": "unknown",
        "requires_account": "unknown",
        "requires_interview": "unknown",
        "requires_experience": "unknown",
        "requires_portfolio": "unknown",
        "requires_assessment": "unknown",
        "blockers": [],
        "evidence": "no_catalog_match",
    }
    if src is None:
        return report

    report["evidence"] = f"catalog:{src.name}"
    report["argentina_compatible"] = _tri(getattr(src, "argentina_ok", None))
    report["requires_account"] = _tri(getattr(src, "requires_account", None))
    report["requires_interview"] = _tri(getattr(src, "requires_interview", None))
    report["requires_experience"] = _tri(getattr(src, "requires_experience", None))
    report["requires_portfolio"] = _tri(getattr(src, "requires_portfolio", None))
    report["requires_assessment"] = _tri(getattr(src, "requires_assessment", None))

    # Payment fallback evidence from expansion metadata (keyed by
    # lowercase source name; value is a dict with a "fallback" strategy).
    try:
        from cores.opportunity.sources_expansion import PAYMENT_FALLBACKS

        fb = PAYMENT_FALLBACKS.get(src.name.lower())
        if fb:
            report["payment_method"] = "fallback_available"
            report["payment_fallbacks"] = fb
        elif getattr(src, "argentina_ok", False):
            report["payment_method"] = "platform_supported"
    except Exception:
        pass

    if report["argentina_compatible"] == "no" and report["payment_method"] == "unknown":
        report["blockers"].append("no_argentina_path")
    return report


def run_eligibility_check(store: LiveStore | None = None, limit: int = 1000) -> dict[str, Any]:
    """Evaluate eligibility for all discovered opportunities; persist results.

    Transitions ``discovered`` → ``eligibility_checked`` only when a catalog
    match produced evidence; unmatched items stay ``discovered``.
    """
    store = store or LiveStore()
    catalog = _catalog_index()
    checked = 0
    matched = 0
    for opp in store.all(status="discovered")[:limit]:
        report = evaluate_eligibility(opp, catalog)
        opp.raw["eligibility"] = report
        if report["evidence"] != "no_catalog_match":
            matched += 1
            opp.status = "eligibility_checked"
            checked += 1
    store.save()
    return {
        "evaluated": len(store.all(status="discovered")) + checked,
        "catalog_matched": matched,
        "moved_to_eligibility_checked": checked,
        "catalog_size": len(catalog),
    }


async def scheduled_live_scan() -> dict[str, Any]:
    """Scheduler entry point: full live scan + eligibility refresh.

    Runs all fetchers, dedups, then re-evaluates eligibility for items
    still in ``discovered``. Never raises — failures are in the report.
    """
    try:
        report = await run_live_scan()
        report["ethics_screen"] = screen_store()
        elig = run_eligibility_check()
        report["eligibility"] = elig
        return report
    except Exception as exc:  # pragma: no cover - scheduler safety
        logger.exception("scheduled_live_scan failed")
        return {"error": str(exc)}


# --- Ethics screen + execution preparation ---

# Patterns that disqualify an opportunity regardless of reward: abuse,
# evasion, or work OWNEX must never automate.
# Substrings that mark abuse/evasion work. Kept specific: generic terms
# like "bypass" or "spam" appear legitimately in security assessments.
ETHICS_BLOCKLIST: tuple[str, ...] = (
    "solve captcha",
    "captcha solving",
    "solve hcaptcha",
    "solve recaptcha",
    "hcaptcha",
    "hcapcha",
    "recaptcha",
    "auto solve",
    "credential stuffing",
    "account takeover",
    "ddos attack",
    "astroturf",
    "fake reviews",
    "evade detection",
    "bypass paywall",
    "scrape.*bypass",
)


def ethics_screen(opp: LiveOpportunity) -> list[str]:
    """Return block reasons; empty list = passes the ethics screen."""
    haystack = f"{opp.title} {opp.description} {' '.join(opp.tags)}".lower()
    return [p for p in ETHICS_BLOCKLIST if p in haystack]


def screen_store(store: LiveStore | None = None) -> dict[str, Any]:
    """Reject stored items that fail the ethics screen (auditable)."""
    store = store or LiveStore()
    rejected = 0
    for opp in store.all():
        if opp.status in ("expired", "rejected"):
            continue
        reasons = ethics_screen(opp)
        if reasons:
            opp.status = "rejected"
            opp.raw["rejection"] = {"reason": "ethics_screen", "matched": reasons}
            rejected += 1
    store.save()
    return {"rejected": rejected}


def _default_workspaces_dir() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "workspaces"


_GITHUB_ISSUE_RE = __import__("re").compile(r"github\.com/([^/]+/[^/]+)/(?:issues|pull)/(\d+)", __import__("re").I)


async def _fetch_github_issue(url: str) -> dict[str, Any] | None:
    """Fetch public GitHub issue/PR metadata (no auth needed for public repos)."""
    import httpx

    m = _GITHUB_ISSUE_RE.search(url)
    if not m:
        return None
    repo, number = m.group(1), m.group(2)
    kind = "issues" if "/issues/" in url else "pulls"
    api = f"https://api.github.com/repos/{repo}/{kind}/{number}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(api, headers={"Accept": "application/vnd.github+json"})
            if resp.status_code != 200:
                return {
                    "error": f"github_api_{resp.status_code}",
                    "repo": repo,
                    "number": number,
                }
            data = resp.json()
            return {
                "repo": repo,
                "number": int(number),
                "kind": kind,
                "title": data.get("title"),
                "body": (data.get("body") or "")[:8000],
                "state": data.get("state"),
                "labels": [label.get("name") for label in data.get("labels", [])],
                "html_url": data.get("html_url"),
                "comments": data.get("comments"),
                "created_at": data.get("created_at"),
                "bounty_hint": _extract_bounty_amount(data.get("body") or ""),
            }
    except Exception as exc:
        return {"error": str(exc), "repo": repo, "number": number}


def _extract_bounty_amount(text: str) -> float | None:
    """Best-effort bounty amount from issue body (USD markers)."""
    import re

    for pat in (r"\$\s?(\d[\d,]*)", r"(\d[\d,]*)\s?(?:USD|usd|dollars)"):
        m = re.search(pat, text)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


_DIFFICULTY_SIGNALS = {
    "easy": (
        "good first issue",
        "good-first-issue",
        "documentation",
        "typo",
        "beginner",
    ),
    "hard": ("security", "crypto", "performance", "refactor", "breaking"),
}


def estimate_task(opp: LiveOpportunity, issue: dict[str, Any] | None = None) -> dict[str, Any]:
    """Heuristic difficulty/effort/reward estimate — honest guess, not a promise."""
    labels = " ".join((issue or {}).get("labels") or []).lower()
    title = f"{opp.title} {opp.description}".lower()
    haystack = f"{labels} {title}"
    if any(s in haystack for s in _DIFFICULTY_SIGNALS["hard"]):
        difficulty = "hard"
    elif any(s in haystack for s in _DIFFICULTY_SIGNALS["easy"]):
        difficulty = "easy"
    else:
        difficulty = "medium"
    effort_hours = {"easy": 1.0, "medium": 4.0, "hard": 12.0}[difficulty]
    reward = opp.reward if isinstance(opp.reward, (int, float)) else None
    bounty = (issue or {}).get("bounty_hint")
    effective_reward = bounty if isinstance(bounty, (int, float)) else reward
    return {
        "difficulty": difficulty,
        "estimated_effort_hours": effort_hours,
        "advertised_reward": reward,
        "currency": opp.currency,
        "bounty_hint": bounty,
        "effective_reward_usd": effective_reward,
        "note": "heuristic estimate — actual effort depends on codebase; reward is advertised, not confirmed",
    }


async def _fetch_github_repo(repo: str) -> dict[str, Any] | None:
    """Public repo metadata for execution planning (no auth)."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}",
                headers={"Accept": "application/vnd.github+json"},
            )
            if resp.status_code != 200:
                return {"error": f"github_api_{resp.status_code}", "repo": repo}
            d = resp.json()
            return {
                "repo": repo,
                "language": d.get("language"),
                "default_branch": d.get("default_branch"),
                "stars": d.get("stargazers_count"),
                "open_issues": d.get("open_issues_count"),
                "archived": d.get("archived"),
                "clone_url": d.get("clone_url"),
            }
    except Exception as exc:
        return {"error": str(exc), "repo": repo}


async def _clone_repo(clone_url: str, dest: Path, timeout: int = 120) -> dict[str, Any]:
    """Shallow-clone a public repo into the workspace (read-only prep step).

    Never raises — clone failure is evidence, not a crash. Uses
    ``--depth 1`` to keep it fast; no credentials, public repos only.
    """
    import asyncio

    if dest.exists() and any(dest.iterdir()):
        return {"cloned": True, "path": str(dest), "note": "already present"}
    dest.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        "git",
        "clone",
        "--depth",
        "1",
        clone_url,
        str(dest),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        return {"cloned": False, "error": f"clone timeout after {timeout}s"}
    if proc.returncode != 0:
        return {
            "cloned": False,
            "error": (stderr or b"").decode(errors="replace")[:300],
        }
    return {"cloned": True, "path": str(dest)}


async def prepare_execution(
    opportunity_key: str,
    store: LiveStore | None = None,
    workspaces_dir: str | Path | None = None,
    clone: bool = True,
) -> dict[str, Any]:
    """Prepare a READY/verified opportunity for assisted execution.

    Fetches public issue metadata when the URL is a GitHub issue/PR,
    creates an isolated workspace with the evidence pack, and marks the
    opportunity ``in_progress``. No submission, claim, or external write
    happens here — delivery requires explicit human approval.
    """
    store = store or LiveStore()
    opp = store._items.get(opportunity_key)
    if opp is None:
        return {"error": f"unknown opportunity: {opportunity_key}"}
    if opp.status in ("expired", "rejected"):
        return {"error": f"opportunity is {opp.status}", "key": opportunity_key}

    reasons = ethics_screen(opp)
    if reasons:
        opp.status = "rejected"
        opp.raw["rejection"] = {"reason": "ethics_screen", "matched": reasons}
        store.save()
        return {"error": "ethics_screen", "matched": reasons}

    ws_root = Path(workspaces_dir) if workspaces_dir else _default_workspaces_dir()
    ws_dir = ws_root / opportunity_key.replace(":", "_").replace("/", "_")
    ws_dir.mkdir(parents=True, exist_ok=True)

    evidence: dict[str, Any] = {"url": opp.url, "platform": opp.platform}
    issue: dict[str, Any] | None = None
    repo_info: dict[str, Any] | None = None
    if "github.com" in opp.url:
        issue = await _fetch_github_issue(opp.url)
        evidence["github_issue"] = issue
        m = _GITHUB_ISSUE_RE.search(opp.url)
        if m and issue and not issue.get("error"):
            repo_info = await _fetch_github_repo(m.group(1))
            evidence["github_repo"] = repo_info
    estimate = estimate_task(opp, issue)

    # Assisted execution step 1: shallow-clone the target repo so the
    # executor/human works on real code, not just metadata.
    clone_result: dict[str, Any] | None = None
    if clone and repo_info and repo_info.get("clone_url") and not repo_info.get("archived"):
        clone_result = await _clone_repo(repo_info["clone_url"], ws_dir / "repo")
        evidence["clone"] = clone_result

    # Evidence pack — everything the executor/human needs, persisted.
    (ws_dir / "opportunity.json").write_text(__import__("json").dumps({**opp.to_dict(), "raw_keys": list(opp.raw.keys())}, indent=2, default=str))
    lines = [
        f"# {opp.title}",
        "",
        f"- Platform: {opp.platform}",
        f"- Reward (advertised): {opp.reward} {opp.currency}",
        f"- URL: {opp.url}",
        f"- Status: {opp.status}",
        f"- Prepared at: {datetime.now(UTC).isoformat()}",
        "",
        "## Description",
        "",
        opp.description or "(none)",
        "",
    ]
    if issue and not issue.get("error"):
        lines += [
            "## GitHub Issue (fetched)",
            "",
            f"- Repo: {issue['repo']} · #{issue['number']} ({issue['kind']})",
            f"- State: {issue['state']} · Labels: {', '.join(issue.get('labels') or [])}",
            f"- Bounty hint in body: {issue.get('bounty_hint')}",
            "",
            "### Body",
            "",
            issue.get("body") or "(empty)",
            "",
        ]
    if repo_info and not repo_info.get("error"):
        lines += [
            "## Repository (fetched)",
            "",
            f"- Repo: {repo_info['repo']} · Language: {repo_info.get('language')} · Branch: {repo_info.get('default_branch')}",
            f"- Stars: {repo_info.get('stars')} · Open issues: {repo_info.get('open_issues')} · Archived: {repo_info.get('archived')}",
            f"- Clone: `{repo_info.get('clone_url')}`",
            "",
        ]
    if clone_result:
        lines += [
            "## Workspace clone",
            "",
            f"- Status: {'cloned' if clone_result.get('cloned') else 'FAILED'}",
            f"- Path: `{clone_result.get('path', 'n/a')}`",
            f"- Error: {clone_result.get('error', 'none')}",
            "",
        ]
    lines += [
        "## Execution plan",
        "",
        f"- Estimated difficulty: **{estimate['difficulty']}** (~{estimate['estimated_effort_hours']}h heuristic)",
        f"- Advertised reward: {estimate['advertised_reward']} {estimate['currency']} (bounty hint: {estimate['bounty_hint']}) — NOT confirmed income",
        "",
        "1. Clone repo / access platform",
        "2. Reproduce or understand the task",
        "3. Implement minimal fix/feature",
        "4. Run tests",
        "5. Prepare delivery (PR/issue comment/proposal)",
        "6. **Human approval required before any submission**",
        "",
    ]
    (ws_dir / "ISSUE.md").write_text("\n".join(lines))
    (ws_dir / "PLAN.md").write_text(
        __import__("json").dumps(
            {
                "estimate": estimate,
                "steps": [
                    "clone_or_access",
                    "reproduce",
                    "implement",
                    "test",
                    "prepare_delivery",
                    "human_approval",
                    "submit",
                ],
            },
            indent=2,
        )
    )

    opp.status = "in_progress"
    opp.raw["execution"] = {
        "workspace": str(ws_dir),
        "prepared_at": datetime.now(UTC).isoformat(),
        "evidence": evidence,
        "estimate": estimate,
        "clone": clone_result,
        "approval_required": True,
        "approval": {"approved": False},
    }
    store.save()
    return {
        "key": opportunity_key,
        "workspace": str(ws_dir),
        "status": "in_progress",
        "estimate": estimate,
        "clone": clone_result,
        "github_issue": issue,
        "github_repo": repo_info,
        "approval_required": True,
    }


async def analyze_workspace(
    opportunity_key: str,
    run_tests: bool = False,
    store: LiveStore | None = None,
) -> dict[str, Any]:
    """Analyze the cloned repo in a prepared workspace.

    Reuses the canonical ``RepoAnalyzer`` (language, test/build commands,
    frameworks, entry points) and optionally ``TestRunner``. Results are
    persisted to ``ANALYSIS.md``/``TEST_RESULTS.md`` in the workspace and
    into ``execution.analysis`` — real evidence, no claims.
    """
    store = store or LiveStore()
    opp = store._items.get(opportunity_key)
    if opp is None:
        return {"error": f"unknown opportunity: {opportunity_key}"}
    execution = (opp.raw or {}).get("execution") or {}
    ws = execution.get("workspace")
    repo = Path(ws) / "repo" if ws else None
    if not repo or not repo.exists():
        return {"error": "no cloned repo in workspace", "key": opportunity_key}

    from core.autonomy.repo_analyzer import RepoAnalyzer
    from core.autonomy.test_runner import TestRunner

    analyzer = RepoAnalyzer()
    info = await analyzer.analyze_repo(repo)
    analysis = {
        "language": info.language,
        "package_manager": info.package_manager,
        "test_command": info.test_command,
        "build_command": info.build_command,
        "framework": info.framework,
        "git_remote": info.git_remote,
        "test_files": len(info.test_files or []),
        "entry_points": (info.entry_points or [])[:10],
    }

    test_summary = None
    if run_tests:
        runner = TestRunner({"timeout": 120})
        summary = await runner.run_tests(repo, repo_info=info)
        test_summary = {
            "overall_success": summary.overall_success,
            "duration_s": round(summary.total_duration, 2),
            "best": (
                {
                    "command": summary.best_result.command,
                    "returncode": summary.best_result.returncode,
                    "passed": summary.best_result.passed,
                    "failed": summary.best_result.failed,
                    "skipped": summary.best_result.skipped,
                }
                if summary.best_result
                else None
            ),
            "commands_tried": summary.test_commands_tried,
        }

    ws_path = Path(ws)
    (ws_path / "ANALYSIS.md").write_text("# Repo analysis\n\n" + "\n".join(f"- {k}: {v}" for k, v in analysis.items()) + "\n")
    if test_summary:
        import json as _json

        (ws_path / "TEST_RESULTS.md").write_text(_json.dumps(test_summary, indent=2))

    execution["analysis"] = analysis
    if test_summary:
        execution["tests"] = test_summary
    opp.raw["execution"] = execution
    store.save()
    return {
        "key": opportunity_key,
        "analysis": analysis,
        "tests": test_summary,
        "workspace": ws,
    }


# External lifecycle states that require platform evidence to enter.
# ``prepared``/``in_progress`` are local; everything past them must cite
# an external source (URL, API response id, message screenshot ref).
EXTERNAL_TRANSITIONS: dict[str, set[str]] = {
    "in_progress": {"submitted", "rejected", "expired"},
    "submitted": {"accepted", "rejected", "expired"},
    "accepted": {"paid"},
    "ready": {"in_progress", "rejected", "expired"},
    "eligibility_checked": {"ready", "in_progress", "rejected", "expired"},
    "discovered": {"in_progress", "rejected", "expired"},
}


def record_external_status(
    opportunity_key: str,
    status: str,
    evidence: dict[str, Any],
    store: LiveStore | None = None,
    amount: float | None = None,
    currency: str | None = None,
) -> dict[str, Any]:
    """Record an externally-observed lifecycle transition.

    ``submitted``/``accepted``/``paid``/``rejected`` (external) require
    non-empty ``evidence`` — e.g. ``{"url": "...", "external_id": "..."}``
    or ``{"api_response": {...}}``. A transition to ``paid`` additionally
    requires evidence AND mirrors into the Revenue Ledger ``paid`` bucket
    (which itself refuses evidence-free entries).
    """
    store = store or LiveStore()
    opp = store._items.get(opportunity_key)
    if opp is None:
        return {"error": f"unknown opportunity: {opportunity_key}"}
    if status not in {"submitted", "accepted", "rejected", "paid", "expired"}:
        return {"error": f"invalid external status: {status}"}
    if not evidence:
        return {"error": "external status requires evidence", "status": status}
    allowed = EXTERNAL_TRANSITIONS.get(opp.status, set())
    if status not in allowed:
        return {
            "error": f"invalid transition {opp.status} → {status}",
            "allowed": sorted(allowed),
        }
    opp.status = status
    opp.raw.setdefault("external_events", []).append(
        {
            "status": status,
            "evidence": evidence,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
    )
    store.save()

    ledger_note = None
    amount_source = None
    if status == "paid":
        try:
            from cores.opportunity.revenue_ledger import RevenueLedger

            # Paid amount: explicit param > evidence["amount"] > advertised
            # reward. Advertised fallback is flagged — it is NOT confirmed
            # income until the evidence itself states the amount.
            paid_amount = amount
            if paid_amount is None and isinstance(evidence.get("amount"), (int, float)):
                paid_amount = float(evidence["amount"])
            if paid_amount is not None:
                amount_source = "explicit"
            else:
                paid_amount = opp.reward if isinstance(opp.reward, (int, float)) else 0.0
                amount_source = "advertised_fallback"
            paid_currency = currency or opp.currency or "USD"
            res = RevenueLedger().record_amount(
                f"live:{opportunity_key}",
                "paid",
                float(paid_amount),
                currency=paid_currency,
                evidence={**evidence, "amount_source": amount_source},
                payout_method=evidence.get("payout_method"),
                paid_at=evidence.get("paid_at"),
            )
            ledger_note = "recorded" if "entry" in res else res.get("error")
        except Exception as exc:
            ledger_note = f"ledger_sync_failed: {exc}"
    return {
        "key": opportunity_key,
        "status": status,
        "ledger": ledger_note,
        "amount_source": amount_source,
        "note": "external status recorded with evidence",
    }


def draft_payment_inquiry(
    opportunity_key: str,
    store: LiveStore | None = None,
) -> dict[str, Any]:
    """Draft a private message asking the poster to confirm payment terms.

    Used when eligibility shows no verified Argentina payout path but a
    fallback (private_message/crypto/Payoneer) exists. The draft asks for
    amount, currency, fees, timing and method — per the rule: no paid
    work starts without written payment terms. Nothing is sent.
    """
    store = store or LiveStore()
    opp = store._items.get(opportunity_key)
    if opp is None:
        return {"error": f"unknown opportunity: {opportunity_key}"}
    elig = (opp.raw or {}).get("eligibility") or {}
    fallbacks_raw = elig.get("payment_fallbacks") or []
    fallbacks = [fallbacks_raw] if isinstance(fallbacks_raw, dict) else list(fallbacks_raw)
    advertised = opp.reward if isinstance(opp.reward, (int, float)) else "[CONFIRM]"
    currency = opp.currency or "[CONFIRM]"
    if fallbacks:
        fb0 = fallbacks[0] if isinstance(fallbacks[0], dict) else {}
        method = str(fb0.get("fallback") or fb0.get("notes") or fallbacks[0])
    else:
        method = "[CONFIRM — e.g. crypto/Payoneer/wire]"
    draft = f"""Hi — I'm interested in this opportunity ({opp.title}).

Before starting, could you confirm the payment terms in writing?

- Amount: {advertised} {currency} (advertised — please confirm final amount)
- Currency: {currency}
- Fees / who covers platform or transfer fees: [CONFIRM]
- Payment timing: [CONFIRM — e.g. on merge, Net-30, milestone]
- Payment method: {method}
- Any requirements on my side (invoice, ID, account type): [CONFIRM]

Thanks!
"""
    out: dict[str, Any] = {
        "key": opportunity_key,
        "platform": opp.platform,
        "advertised_reward": advertised,
        "currency": currency,
        "fallbacks": fallbacks,
        "draft": draft,
        "note": "draft only — nothing sent; send manually after human review",
    }
    ws = ((opp.raw or {}).get("execution") or {}).get("workspace")
    if ws and Path(ws).exists():
        (Path(ws) / "PAYMENT_INQUIRY.md").write_text(draft)
        out["saved_to"] = str(Path(ws) / "PAYMENT_INQUIRY.md")
    return out


def record_approval(
    opportunity_key: str,
    approved: bool,
    approved_by: str = "user",
    note: str = "",
    store: LiveStore | None = None,
) -> dict[str, Any]:
    """Record the human approval decision for a prepared opportunity.

    This is the ONLY gate before any future submission path. Approval is
    recorded with timestamp + actor; it does not submit anything itself.
    """
    store = store or LiveStore()
    opp = store._items.get(opportunity_key)
    if opp is None:
        return {"error": f"unknown opportunity: {opportunity_key}"}
    execution = opp.raw.get("execution") or {}
    if not execution.get("workspace"):
        return {"error": "opportunity not prepared", "key": opportunity_key}
    execution["approval"] = {
        "approved": bool(approved),
        "approved_by": approved_by,
        "note": note,
        "at": datetime.now(UTC).isoformat(),
    }
    opp.raw["execution"] = execution
    # Mirror approval into the workspace evidence pack.
    ws = Path(execution["workspace"])
    if ws.exists():
        (ws / "APPROVAL.json").write_text(__import__("json").dumps(execution["approval"], indent=2))
    store.save()
    return {
        "key": opportunity_key,
        "approved": bool(approved),
        "approved_by": approved_by,
        "note": "approval recorded; no submission performed",
    }


# ---------------------------------------------------------------------------
# Revenue-first prioritization (REVENUE_FIRST_ENGINEERING.md §3)
# ---------------------------------------------------------------------------

_TERMINAL_STATUSES = {"expired", "rejected", "paid", "withdrawn"}

_BARRIER_PENALTIES = {
    "requires_interview": 6.0,
    "requires_experience": 8.0,
    "requires_portfolio": 5.0,
    "requires_assessment": 6.0,
    "requires_account": 2.0,
}


def score_opportunity(
    opp: LiveOpportunity,
    eligibility: dict[str, Any] | None = None,
    estimate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Revenue-first viability score (0-100) with confidence.

    Rewards advertised value, Argentina/payment compatibility, low
    barriers and reward-per-hour — never raw bounty size alone.
    ``confidence`` is the fraction of evaluated dimensions that are
    definitive (yes/no); ``unknown`` lowers confidence, not the score.
    """
    eligibility = eligibility if eligibility is not None else evaluate_eligibility(opp)
    estimate = estimate if estimate is not None else estimate_task(opp)

    reward_usd = estimate.get("effective_reward_usd")
    if not isinstance(reward_usd, (int, float)) or reward_usd <= 0:
        reward_usd = opp.reward if isinstance(opp.reward, (int, float)) else 0.0
    effort = estimate.get("estimated_effort_hours") or opp.effort_hours or 4.0

    # Reward value: capped log-ish tiers — a $500 unknown-requirement task
    # must not outrank an accessible $40 one (§3).
    if reward_usd >= 200:
        reward_score = 25.0
    elif reward_usd >= 50:
        reward_score = 20.0
    elif reward_usd >= 20:
        reward_score = 15.0
    elif reward_usd > 0:
        reward_score = 10.0
    else:
        reward_score = 5.0

    ar = eligibility.get("argentina_compatible", "unknown")
    ar_score = {"yes": 20.0, "unknown": 8.0, "no": 0.0}[ar]

    pm = eligibility.get("payment_method", "unknown")
    pm_score = {
        "platform_supported": 15.0,
        "fallback_available": 12.0,
        "unknown": 6.0,
    }.get(pm, 0.0)

    barrier_score = 25.0
    for dim, penalty in _BARRIER_PENALTIES.items():
        state = eligibility.get(dim, "unknown")
        if state == "yes":
            barrier_score -= penalty
        elif state == "unknown":
            barrier_score -= 1.0
    barrier_score = max(0.0, barrier_score)

    # Competition saturation: winner-take-all pools with thousands of
    # entries have lower expected value than the advertised pot suggests.
    # Applies to competitions only; bounty/task platforms unaffected.
    saturation_factor = 1.0
    subs = opp.raw.get("submission_count")
    if isinstance(subs, (int, float)) and subs > 0:
        if subs >= 10000:
            saturation_factor = 0.5
        elif subs >= 2000:
            saturation_factor = 0.75
        elif subs >= 500:
            saturation_factor = 0.9
        reward_score = round(reward_score * saturation_factor, 1)

    rph = reward_usd / max(effort, 0.5)
    if rph >= 50:
        effort_score = 15.0
    elif rph >= 20:
        effort_score = 12.0
    elif rph >= 10:
        effort_score = 9.0
    elif reward_usd > 0:
        effort_score = 6.0
    else:
        effort_score = 3.0

    # Confidence: eligibility report dimensions + payment + AR.
    barrier_states = [eligibility.get(d) for d in _BARRIER_PENALTIES]
    definitive = sum(1 for s in barrier_states if s in ("yes", "no"))
    definitive += int(eligibility.get("argentina_compatible") in ("yes", "no"))
    definitive += int(eligibility.get("payment_method") != "unknown")
    total_dims = len(_BARRIER_PENALTIES) + 2
    confidence = round(definitive / total_dims, 2)

    total = round(reward_score + ar_score + pm_score + barrier_score + effort_score, 1)
    return {
        "opportunity_id": opp.dedup_key(),
        "platform": opp.platform,
        "status": opp.status,
        "score": total,
        "breakdown": {
            "reward": reward_score,
            "argentina_compatibility": ar_score,
            "payment_method": pm_score,
            "low_barriers": round(barrier_score, 1),
            "reward_per_hour_fit": effort_score,
            "competition_saturation": saturation_factor,
        },
        "estimated_reward_usd": round(float(reward_usd), 2),
        "estimated_effort_hours": effort,
        "estimated_net_per_hour_usd": round(rph, 2),
        "confidence": confidence,
        "blockers": list(eligibility.get("blockers") or []),
        "note": "score is a heuristic ranking aid — advertised reward is not confirmed income",
    }


def rank_opportunities(
    store: LiveStore | None = None,
    limit: int = 50,
    min_score: float = 0.0,
) -> dict[str, Any]:
    """Rank live opportunities by revenue-first viability.

    Terminal states (expired/rejected/paid/withdrawn) are excluded.
    Results are sorted by score desc; ties broken by confidence then
    advertised reward. ``min_score`` filters low-viability items.
    """
    store = store or LiveStore()
    ranked = []
    for opp in store._items.values():
        if opp.status in _TERMINAL_STATUSES:
            continue
        s = score_opportunity(opp)
        if s["score"] >= min_score:
            ranked.append(s)
    ranked.sort(
        key=lambda s: (s["score"], s["confidence"], s["estimated_reward_usd"]),
        reverse=True,
    )
    return {
        "ranked": ranked[:limit],
        "total_evaluated": len(ranked),
        "note": "heuristic ranking — verify eligibility and payment terms before executing",
    }
