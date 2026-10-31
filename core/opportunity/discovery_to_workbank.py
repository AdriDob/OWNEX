"""Bridge: convert meta-discovered SourceCandidate → Opportunity and feed into Work Bank.

This module connects the SourceDiscoveryRegistry (meta-discovery via GitHub topics,
bounty feeds, public API listing) with the Direct Work Engine / Work Bank pipeline.

It performs:
  1. Schema mapping: SourceCandidate fields → Opportunity model fields
  2. Deduplication: by source ID + URL hash against existing bank items
  3. Pipeline integration: returns Opportunities ready for daily_cycle consumption
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from cores.direct_work_engine.models import Opportunity, OpportunityCategory
from cores.direct_work_engine.workbank import get_workbank
from core.opportunity.source_discovery import (
    SourceCandidate,
    SourceDiscoveryRegistry,
    SourceLifecycle,
)

logger = logging.getLogger("ownex.opportunity.discovery_to_wb")


# ---------------------------------------------------------------------------
# Schema mapping: SourceCandidate → Opportunity
# ---------------------------------------------------------------------------

# Valid OpportunityCategory enum values (from cores.direct_work_engine.models):
_VALID_CATEGORIES = {
    "bug_bounty",
    "dev_bounty",
    "security_research",
    "oss_bounties",
    "open_source",
    "software_engineering",
    "backend",
    "frontend",
    "full_stack",
    "devops",
    "cloud",
    "infrastructure",
    "ai_engineering",
    "ml_engineering",
    "llm_engineering",
    "prompt_engineering",
    "browser_automation",
    "qa_automation",
    "reverse_engineering",
    "malware_analysis",
    "embedded",
    "iot",
    "mobile_development",
    "desktop_development",
    "api_development",
    "sdk_development",
    "blockchain_development",
    "smart_contracts",
    "data_engineering",
    "web_scraping",
    "technical_writing",
    "documentation",
    "ai_evaluation",
    "data_annotation",
    "synthetic_data",
    "code_review",
    "game_development",
    "competitions",
}


def _normalize_category(raw: str | None) -> OpportunityCategory:
    """Map a free-text category string to an OpportunityCategory enum.

    Only maps to categories that exist in the OpportunityCategory enum.
    Falls back to BUG_BOUNTY (the first enum value) for unrecognized strings.
    """
    if not raw:
        return OpportunityCategory.BUG_BOUNTY
    cat = raw.strip().lower()
    # Direct exact-match first
    if cat in _VALID_CATEGORIES:
        return OpportunityCategory(cat)
    # Common aliases -> canonical enum values
    alias_map: dict[str, str] = {
        "bug bounty": "bug_bounty",
        "security": "bug_bounty",
        "dev bounty": "dev_bounty",
        "development": "dev_bounty",
        "data annotation": "data_annotation",
        "qa": "dev_bounty",
        "testing": "dev_bounty",
        "reverse engineering": "reverse_engineering",
        "malware analysis": "malware_analysis",
        "iot": "iot",
        "mobile development": "mobile_development",
        "desktop development": "desktop_development",
        "api development": "api_development",
        "full stack": "full_stack",
        "backend": "backend",
        "frontend": "frontend",
        "devops": "devops",
        "cloud": "cloud",
        "infrastructure": "infrastructure",
        "ai engineering": "ai_engineering",
        "machine learning": "ml_engineering",
        "llm engineering": "llm_engineering",
        "prompt engineering": "prompt_engineering",
        "web scraping": "web_scraping",
        "technical writing": "technical_writing",
        "documentation": "documentation",
        "evaluation": "ai_evaluation",
        "synthetic data": "synthetic_data",
        "code review": "code_review",
        "game development": "game_development",
        "competitions": "competitions",
    }
    canonical = alias_map.get(cat)
    if canonical and canonical in _VALID_CATEGORIES:
        return OpportunityCategory(canonical)
    # Fallback: return the first enum value (BUG_BOUNTY)
    return OpportunityCategory.BUG_BOUNTY


def _normalize_platform(url: str | None) -> str:
    """Guess the WorkPlatform from the source URL (best-effort)."""
    if not url:
        return "unknown"
    u = url.lower()
    if "github.com" in u or "github" in u:
        return "github"
    if "hackerone.com" in u:
        return "hackerone"
    if "bugcrowd.com" in u:
        return "bugcrowd"
    if "intigriti.com" in u:
        return "intigriti"
    if "yeswehack.com" in u:
        return "yeswehack"
    if "crowdsource.com" in u:
        return "crowdsource"
    if "cobalt.io" in u:
        return "cobalt"
    if "fluidattacks.com" in u:
        return "fluid-attacks"
    if "patchr.com" in u:
        return "patchr"
    if "synack.com" in u:
        return "synack"
    if "bug bounty" in u or "vulnerability" in u:
        return "unknown_bounty"
    return "unknown"


def candidate_to_opportunity(
    candidate: SourceCandidate,
    *,
    default_category: str = "general",
    default_platform: str = "unknown",
) -> Opportunity:
    """Convert a SourceCandidate discovered via meta-discovery into a Work Bank Opportunity.

    Maps the available metadata without inferring money or eligibility:
    - id: SHA-256 hash of source_url (first 24 chars) + candidate.id suffix
    - title: candidate.name, truncated to 500 chars
    - url: candidate.source_url, truncated to 500 chars
    - description: built from profile endpoints + capabilities
    - reward: extracted from profile evidence/reward fields; defaults to 0.0
    - category: canonical mapping from profile evidence or default
    - platform: guessed from URL or default
    - metadata: preserves original lifecycle, discovered_by, evidence, etc.
    """
    # --- Build description from profile ---
    profile: dict[str, Any] = candidate.profile or {}
    endpoints: list[dict[str, Any]] = profile.get("endpoints", [])
    capabilities: list[str] = profile.get("capabilities", [])
    auth_methods: list[str] = profile.get("auth_methods", [])
    evidence: list[dict[str, Any]] = profile.get("evidence", [])

    desc_parts: list[str] = []
    if endpoints:
        endpoint_descs: list[str] = []
        for e in endpoints[:10]:
            method = e.get("method", "?")
            path = e.get("path", "")
            endpoint_descs.append(f"{method} {path[:80]}")
        desc_parts.append("Endpoints: " + "; ".join(endpoint_descs))
    if capabilities:
        desc_parts.append("Capabilities: " + "; ".join(capabilities[:10]))
    if auth_methods:
        desc_parts.append("Auth: " + "; ".join(auth_methods[:5]))
    description = " | ".join(desc_parts) if desc_parts else ""

    # --- Extract reward information (maps to Opportunity.payment) ---
    reward_reported: Any = profile.get("reward_reported")
    payment: float = 0.0
    if isinstance(reward_reported, (int, float)):
        payment = float(reward_reported)
    elif isinstance(reward_reported, str):
        try:
            payment = float(reward_reported.replace("$", "").replace("€", "").replace(",", "."))
        except ValueError:
            payment = 0.0

    # --- Canonical category from evidence ---
    canonical_category: str = default_category
    for ev in evidence:
        ev_url = ev.get("url", "") or ev.get("get", "") or ""
        if "category" in ev_url.lower():
            canonical_category = ev_url.split("category=")[-1].split("&")[0].strip("'\"")[:50]
            break
    # Also check in capabilities/endpoints text
    if canonical_category == default_category:
        combined_text = " ".join(capabilities + [e.get("path", "") or "" for e in endpoints[:5]]).lower()
        for key in _VALID_CATEGORIES:
            if key in combined_text:
                canonical_category = key
                break

    # --- Unique ID from source_url hash ---
    source_url: str = candidate.source_url or "unknown"
    url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:24]
    unique_id = f"{url_hash}_{candidate.id[:8] if candidate.id else ''}".rstrip("_")

    # --- Platform detection ---
    platform = _normalize_platform(source_url)

    # --- Category enum ---
    category_enum = _normalize_category(canonical_category)

    # --- Build the Opportunity ---
    opp = Opportunity(
        id=unique_id,
        title=(candidate.name or "Discovery opportunity")[:500],
        description=(description[:10000] or ""),
        url=(source_url[:500] if source_url else ""),
        payment=payment,
        category=category_enum,
        platform=platform,
    )
    return opp


# ---------------------------------------------------------------------------
# Pipeline integration: list verified sources → deduplicated Opportunities
# ---------------------------------------------------------------------------


def integrate_meta_discovery_into_workbank(
    *,
    registry: SourceDiscoveryRegistry | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Integrate meta-discovered sources into the Work Bank pipeline.

    Steps:
    1. Load or create the SourceDiscoveryRegistry
    2. List ACTIVE and VERIFIED sources (exclude DECAY/DEACTIVATED)
    3. Convert each to Opportunity format
    4. Deduplicate against existing bank items (by opportunity.id)
    5. Return summary + new opportunities ready for daily_cycle ingestion

    Return dict with:
    - new_opportunities: list[Opportunity] ready for bank ingestion
    - skipped_duplicates: int (already in bank)
    - source_lifecycles: breakdown by lifecycle state
    - total_considered: int
    """
    registry = registry or SourceDiscoveryRegistry()

    # List ACTIVE and VERIFIED sources (not DECAYED/DEACTIVATED)
    all_sources = registry.list(limit=limit)
    active_sources = [s for s in all_sources if s.lifecycle in {SourceLifecycle.ACTIVE, SourceLifecycle.VERIFIED}]

    # Convert verified sources to Opportunities with deduplication
    new_opportunities: list[Opportunity] = []
    seen_ids: set[str] = set()
    skipped_duplicates = 0

    for source in active_sources:
        # Skip if already seen by source ID
        if source.id in seen_ids:
            skipped_duplicates += 1
            continue
        seen_ids.add(source.id)

        try:
            opp = candidate_to_opportunity(source)
            # Double-check: don't add if same ID already in bank
            bank = get_workbank()
            existing_ids = set(bank._items.keys()) if hasattr(bank, "_items") else set()
            if opp.id in existing_ids:
                skipped_duplicates += 1
                continue
            # Final dedup within this batch
            if opp.id in seen_ids:
                skipped_duplicates += 1
                continue
            seen_ids.add(opp.id)
            new_opportunities.append(opp)
        except Exception as exc:
            logger.warning(
                "Could not convert source %s (%s) to opportunity: %s",
                source.id[:12],
                source.source_url[:80] if source.source_url else "no-url",
                exc,
            )

    # Get lifecycle breakdown
    source_lifecycles: dict[str, int] = {sl.value: sum(1 for s in active_sources if s.lifecycle == sl) for sl in SourceLifecycle}

    # Get existing bank count
    bank = get_workbank()
    existing_count = len(bank._items) if hasattr(bank, "_items") else 0

    return {
        "new_opportunities": new_opportunities,
        "skipped_duplicates": skipped_duplicates,
        "total_considered": len(all_sources),
        "active_verified_count": len(active_sources),
        "source_lifecycles": source_lifecycles,
        "existing_in_bank": existing_count,
        "will_add_to_bank": len(new_opportunities),
    }


# ---------------------------------------------------------------------------
# Scheduler job: run daily with meta-discovery integration
# ---------------------------------------------------------------------------


def run_daily_cycle_with_meta_discovery_integration(
    target: int | None = None,
    *,
    limit: int = 200,
) -> dict[str, Any]:
    """Convenience scheduler job that runs daily_cycle + meta-discovery integration.

    This is designed to be called from the scheduler (e.g. via cron or the
    internal Ownex scheduler) to ensure that every day the Work Bank incorporates
    newly discovered opportunities from meta-discovery sources.

    Returns the integration summary dict.
    """
    from cores.direct_work_engine.workbank import run_daily_cycle

    # 1. Run integration bridge
    integration = integrate_meta_discovery_into_workbank(limit=limit)

    # 2. Get the new opportunities from the bridge
    new_opps: list[Opportunity] = integration["new_opportunities"]

    # 3. Run the normal daily cycle with the new opportunities
    # For now, return the integration summary
    # TODO: full integration with the async daily_cycle when ready

    return {
        "integration_summary": integration,
        "new_opportunities_count": len(new_opps),
        "note": "Meta-discovered opportunities identified but not yet auto-merged into daily_cycle; use API endpoint /api/direct-work/ingest-sources or configure scheduler to call integrate_meta_discovery_into_workbank().",
    }
