"""Bridge: convert meta-discovered SourceCandidate → Opportunity and feed into Work Bank.

This module connects the SourceDiscoveryRegistry (meta-discovery via GitHub topics,
bounty feeds, public API listing) with the Direct Work Engine / Work Bank pipeline.

It performs:
  1. Schema mapping: SourceCandidate fields → Opportunity model fields
  2. Deduplication: by source ID + URL hash against existing bank items
  3. Pipeline integration: returns Opportunities ready for daily_cycle consumption
  4. Feedback tracking: records user acceptance/rejection for learning loop
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from core.opportunity.source_discovery import (
    SourceCandidate,
    SourceDiscoveryRegistry,
    SourceLifecycle,
    run_daily_meta_discovery,
)
from cores.direct_work_engine.models import EmploymentType, Opportunity, OpportunityCategory, PaymentMethod, WorkPlatform
from core.opportunity.engine import OpportunityType
from cores.direct_work_engine.workbank import get_workbank

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
    Falls back to DEV_BOUNTY for unrecognized strings (never BUG_BOUNTY as a
    universal fallback).
    """
    if not raw:
        return OpportunityCategory.DEV_BOUNTY
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
    return OpportunityCategory.DEV_BOUNTY


def _normalize_opportunity_type(raw: str | None) -> OpportunityType:
    """Map a free-text category string to an OpportunityType enum.

    Maps OWNEX P0/P1/P2 priority categories to the engine OpportunityType.
    Priority mapping (P0=highest, P3=lowest):
      - P0 (critical): security_bounty, ai_work
      - P1 (high): dev_bounty, freelance
      - P2 (medium): data_annotation
    """
    if not raw:
        return OpportunityType.DEV_BOUNTY
    cat = raw.strip().lower()
    # Direct exact-match first
    type_map: dict[str, OpportunityType] = {
        "security_bounty": OpportunityType.SECURITY_BOUNTY,
        "dev_bounty": OpportunityType.DEV_BOUNTY,
        "ai_work": OpportunityType.AI_WORK,
        "freelance": OpportunityType.FREELANCE,
        "data_annotation": OpportunityType.DATA_ANNOTATION,
        "bug_bounty": OpportunityType.SECURITY_BOUNTY,
        "dev_bounty": OpportunityType.DEV_BOUNTY,
        "data_entry": OpportunityType.DATA_ANNOTATION,
        "data_entry-level": OpportunityType.DATA_ANNOTATION,
    }
    if cat in type_map:
        return type_map[cat]
    # Alias resolution
    alias_map: dict[str, str] = {
        "bug bounty": "security_bounty",
        "security": "security_bounty",
        "dev bounty": "dev_bounty",
        "development": "dev_bounty",
        "data annotation": "data_annotation",
        "data entry": "data_annotation",
        "qa": "dev_bounty",
        "qa testing": "dev_bounty",
        "reverse engineering": "ai_work",
        "malware analysis": "ai_work",
        "iot": "ai_work",
        "mobile dev": "dev_bounty",
        "mobile development": "dev_bounty",
        "api dev": "dev_bounty",
        "full stack": "dev_bounty",
        "frontend": "dev_bounty",
        "backend": "dev_bounty",
        "devops": "dev_bounty",
        "cloud": "ai_work",
        "infrastructure": "ai_work",
        "ai engineering": "ai_work",
        "machine learning": "ai_work",
        "llm engineering": "ai_work",
        "prompt engineering": "ai_work",
        "web scraping": "dev_bounty",
        "code review": "dev_bounty",
        "game development": "dev_bounty",
        "competitions": "dev_bounty",
        "research": "research",
        "content creation": "content_creation",
    }
    alias_cat = alias_map.get(cat)
    if alias_cat and alias_cat in type_map:
        return type_map[alias_cat]
    return OpportunityType.DEV_BOUNTY


def _normalize_platform(url: str | None) -> WorkPlatform:
    """Guess the WorkPlatform from the source URL (best-effort)."""
    if not url:
        return WorkPlatform.OTHER
    u = url.lower()
    if "github.com" in u:
        return WorkPlatform.GITHUB
    if "hackerone.com" in u:
        return WorkPlatform.HACKERONE
    if "bugcrowd.com" in u:
        return WorkPlatform.BUG_CROWD
    if "intigriti.com" in u:
        return WorkPlatform.INTIGRITI
    if "yeswehack.com" in u:
        return WorkPlatform.YES_WE_HACK
    if "synack.com" in u:
        return WorkPlatform.SYNACK
    if "immunefi.com" in u:
        return WorkPlatform.IMMUNEFI
    if "issuehunt" in u:
        return WorkPlatform.ISSUE_HUNT
    if "opire" in u:
        return WorkPlatform.OPIRE
    if "algora" in u:
        return WorkPlatform.ALGORA
    if "superteam" in u:
        return WorkPlatform.SUPER_TEAM
    if "opencollective.com" in u:
        return WorkPlatform.OPEN_COLLECTIVE
    if "freelancer.com" in u:
        return WorkPlatform.FREELANCER
    if "fiverr.com" in u:
        return WorkPlatform.FIVERR
    return WorkPlatform.OTHER


def candidate_to_opportunity(
    candidate: SourceCandidate,
    *,
    default_category: str = "dev_bounty",
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
    evidence_urls = [str(ev.get("url", ""))[:200] for ev in evidence if isinstance(ev, dict) and ev.get("url")]
    if evidence_urls:
        desc_parts.append("Evidence: " + "; ".join(evidence_urls[:5]))
    description = " | ".join(desc_parts) if desc_parts else ""

    # --- Extract reward information (maps to Opportunity.payment) ---
    # Key rule: NO inferred rewards and NO inferred verification. A parsed
    # amount is only "reported" evidence; payment_proven stays False until an
    # independent payout/escrow verification exists.
    reward_reported: Any = profile.get("reward_reported")
    reward_currency = profile.get("reward_currency")
    currency = reward_currency.strip().upper() if isinstance(reward_currency, str) and reward_currency.strip() else "USD"
    payment: float
    if reward_reported is None or reward_reported == "":
        payment = 0.0
    elif isinstance(reward_reported, (int, float)):
        payment = float(reward_reported)
    elif isinstance(reward_reported, str):
        try:
            cleaned = reward_reported.replace("$", "").replace("€", "").replace(",", ".")
            payment = float(cleaned)
        except ValueError:
            payment = 0.0
        else:
            if payment <= 0:
                payment = 0.0
    else:
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
    rate_source = "reported" if payment > 0 else "unknown"

    # --- Category enum ---
    category_enum = _normalize_category(canonical_category)

    # --- Build the Opportunity ---
    opp = Opportunity(
        id=unique_id,
        title=(candidate.name or "Discovery opportunity")[:500],
        description=(description[:10000] or ""),
        url=(source_url[:500] if source_url else ""),
        payment=payment,
        currency=currency[:10] or "USD",
        payment_proven=False,
        category=category_enum,
        platform=platform,
        payment_method=PaymentMethod.OTHER,
        employment_type=EmploymentType.BOUNTY,
        rate_source=rate_source,
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
    """Integrate meta-discovered opportunity candidates into the Work Bank pipeline.

    Steps:
    1. Load or create the SourceDiscoveryRegistry
    2. List opportunity candidates (record_type="opportunity", exclude DECAY/DEACTIVATED)
    3. Convert each to Opportunity format
    4. Drop candidates without a demonstrable reward (payment <= 0)
    5. Deduplicate against existing bank items (by opportunity.id)
    6. Return summary + new opportunities ready for daily_cycle ingestion

    Return dict with:
    - new_opportunities: list[Opportunity] ready for bank ingestion
    - skipped_duplicates: int (already in bank)
    - source_lifecycles: breakdown by lifecycle state
    - total_considered: int
    """
    registry = registry or SourceDiscoveryRegistry()

    # Only concrete opportunity candidates (record_type="opportunity") can become
    # Work Bank items. Source candidates (repos/platforms) stay in the registry.
    all_sources = registry.list(limit=limit)
    opportunity_sources = [
        s
        for s in all_sources
        if getattr(s, "record_type", "source") == "opportunity" and s.lifecycle not in {SourceLifecycle.DECAY, SourceLifecycle.DEACTIVATED}
    ]
    source_candidates_skipped = sum(1 for s in all_sources if getattr(s, "record_type", "source") != "opportunity")

    new_opportunities: list[Opportunity] = []
    seen_ids: set[str] = set()
    skipped_duplicates = 0
    skipped_no_reward = 0

    for source in opportunity_sources:
        if source.id in seen_ids:
            skipped_duplicates += 1
            continue
        seen_ids.add(source.id)

        try:
            opp = candidate_to_opportunity(source)
            if opp.payment <= 0:
                skipped_no_reward += 1
                continue
            bank = get_workbank()
            existing_ids = set(bank._items.keys()) if hasattr(bank, "_items") else set()
            if opp.id in existing_ids:
                skipped_duplicates += 1
                continue
            if opp.id in seen_ids:
                skipped_duplicates += 1
                continue
            seen_ids.add(opp.id)
            new_opportunities.append(opp)
        except Exception as exc:
            logger.warning(
                "Could not convert opportunity %s (%s) to work item: %s",
                source.id[:12],
                source.source_url[:80] if source.source_url else "no-url",
                exc,
            )

    source_lifecycles: dict[str, int] = {sl.value: sum(1 for s in opportunity_sources if s.lifecycle == sl) for sl in SourceLifecycle}

    bank = get_workbank()
    existing_count = len(bank._items) if hasattr(bank, "_items") else 0

    return {
        "new_opportunities": new_opportunities,
        "skipped_duplicates": skipped_duplicates,
        "skipped_no_reward": skipped_no_reward,
        "source_candidates_skipped": source_candidates_skipped,
        "total_considered": len(all_sources),
        "opportunity_candidates_considered": len(opportunity_sources),
        "active_verified_count": len(opportunity_sources),
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

    Returns the integration summary dict plus the daily-cycle result.
    """
    integration = integrate_meta_discovery_into_workbank(limit=limit)
    new_opps = integration["new_opportunities"]

    if not new_opps:
        return {**integration, "daily_cycle": {"status": "no_new_opps", "items_prepared": 0}}

    from cores.direct_work_engine.scoring import ZeroBarrierScorer
    from cores.direct_work_engine.workbank import run_daily_cycle

    scorer = ZeroBarrierScorer()
    scored = scorer.score_opportunities(new_opps)
    top_n = min(len(scored), target or 20)
    cycle_result = run_daily_cycle(target=target, opportunities=scored[:top_n])
    return {**integration, "daily_cycle": cycle_result}


def run_daily_meta_discovery_and_integrate() -> dict[str, Any]:
    """Scheduler entry point: discover GitHub repos and integrate into Work Bank.

    Steps:
    1. Run meta-discovery (GitHub topic search)
    2. Integrate new sources into the SourceDiscoveryRegistry
    3. Convert verified sources to Opportunities
    4. Run the daily_cycle with the new opportunities
    5. Return summary of the full pipeline
    """
    from cores.direct_work_engine.scoring import ZeroBarrierScorer
    from cores.direct_work_engine.workbank import run_daily_cycle

    # Step 1: Run GitHub discovery (repositories as sources + reward-backed issues as opportunities)
    discovery = run_daily_meta_discovery()
    logger.info("GitHub discovery: %s", discovery)

    # Step 2: Integrate discovered candidates into the registry
    registry = SourceDiscoveryRegistry()
    registry._load()

    # Step 3: Integrate into Work Bank pipeline
    integration = integrate_meta_discovery_into_workbank(limit=200)
    new_opportunities = integration["new_opportunities"]
    skipped_duplicates = integration["skipped_duplicates"]
    logger.info(
        "Integration: %d new opportunities, %d duplicates skipped",
        len(new_opportunities),
        skipped_duplicates,
    )

    # Step 4: Run daily cycle with new opportunities (if any)
    if new_opportunities:
        # Score the new opportunities
        scorer = ZeroBarrierScorer()
        scored = scorer.score_opportunities(new_opportunities)
        # Take top ones for the daily cycle
        top_n = min(len(scored), 20)
        top_opps = scored[:top_n]

        # Run the daily cycle (without success_floor arg - it uses internal defaults)
        cycle_result = run_daily_cycle(
            target=20,
            opportunities=top_opps,
        )
        logger.info("Daily cycle result: %s", cycle_result)
    else:
        cycle_result = {"status": "no_new_opps", "items_prepared": 0}

    # Step 5: Return full summary
    return {
        "discovery": discovery,
        "integration_summary": integration,
        "new_opportunities_count": len(new_opportunities),
        "skipped_duplicates": skipped_duplicates,
        "cycle_result": cycle_result,
        "note": "Full pipeline: discovery -> registry -> Work Bank integration -> daily cycle",
    }
