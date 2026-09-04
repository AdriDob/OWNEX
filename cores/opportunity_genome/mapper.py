"""Mappers — Convert legacy models to OpportunityGenome.

Each mapper converts from a specific legacy model to the unified genome.
No business logic — pure data transformation with validation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from cores.opportunity_genome.models import (
    BarrierLevel,
    DifficultyLevel,
    EmploymentType,
    EntryMechanism,
    ExperienceLevel,
    GenomeSource,
    GenomeStatus,
    OpportunityCategory,
    OpportunityGenome,
    PaymentMethod,
    WorkPlatform,
    WorkStream,
    ZeroBarrierScore,
)


def _gen_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


# =============================================================================
# Mapper: DWE Opportunity → Genome
# =============================================================================


def map_dwe_opportunity_to_genome(dwe_opp: Any) -> OpportunityGenome:
    """Convert cores.direct_work_engine.models.Opportunity → OpportunityGenome."""
    # Determine category from enum or string
    category = getattr(dwe_opp, "category", OpportunityCategory.DEV_BOUNTY)
    if hasattr(category, "value"):
        category = category.value

    # Determine work stream
    work_stream = _category_to_work_stream(category)

    # Payment method
    payment_method = getattr(dwe_opp, "payment_method", PaymentMethod.OTHER)
    if hasattr(payment_method, "value"):
        payment_method = payment_method.value

    # Employment type
    employment_type = getattr(dwe_opp, "employment_type", EmploymentType.CONTRACT)
    if hasattr(employment_type, "value"):
        employment_type = employment_type.value

    # Experience
    experience_required = getattr(dwe_opp, "experience_required", ExperienceLevel.NONE)
    if hasattr(experience_required, "value"):
        experience_required = experience_required.value

    experience_requirement = getattr(dwe_opp, "experience_requirement", None)
    if experience_requirement and hasattr(experience_requirement, "value"):
        experience_requirement = experience_requirement.value

    # Entry mechanism
    entry_mechanism = getattr(dwe_opp, "entry_mechanism", EntryMechanism.DIRECT)
    if hasattr(entry_mechanism, "value"):
        entry_mechanism = entry_mechanism.value

    # Difficulty
    difficulty = getattr(dwe_opp, "difficulty", DifficultyLevel.INTERMEDIATE)
    if hasattr(difficulty, "value"):
        difficulty = difficulty.value

    # Platform
    platform = getattr(dwe_opp, "platform", WorkPlatform.OTHER)
    if hasattr(platform, "value"):
        platform = platform.value

    # Zero barrier score
    zb_score = getattr(dwe_opp, "zero_barrier_score", None)
    if zb_score:
        if hasattr(zb_score, "total"):
            barrier_level_raw = getattr(zb_score, "barrier_level", BarrierLevel.HIGH)
            if isinstance(barrier_level_raw, str):
                try:
                    barrier_level = BarrierLevel(barrier_level_raw.lower())
                except ValueError:
                    barrier_level = BarrierLevel.HIGH
            else:
                barrier_level = barrier_level_raw
            zb = ZeroBarrierScore(
                total=zb_score.total,
                factors=getattr(zb_score, "factors", {}),
                weights=getattr(zb_score, "weights", {}),
                barrier_level=barrier_level,
                reasoning=getattr(zb_score, "reasoning", []),
                enablers=getattr(zb_score, "enablers", []),
                blockers=getattr(zb_score, "blockers", []),
            )
        else:
            zb = None
    else:
        zb = None

    return OpportunityGenome(
        id=getattr(dwe_opp, "id", _gen_id()),
        external_id=_extract_external_id(dwe_opp),
        source=GenomeSource.DIRECT_WORK,
        platform=platform,
        title=getattr(dwe_opp, "title", "") or getattr(dwe_opp, "name", ""),
        description=getattr(dwe_opp, "description", ""),
        url=getattr(dwe_opp, "url", ""),
        category=category,
        subcategory=getattr(dwe_opp, "subcategory", None),
        work_stream=work_stream,
        reward=float(getattr(dwe_opp, "payment", 0.0) or 0.0),
        currency=getattr(dwe_opp, "currency", "USD"),
        payment_method=payment_method,
        time_to_payout_days=getattr(dwe_opp, "time_to_payout_days", None),
        zero_barrier_score=zb,
        expected_value=float(getattr(dwe_opp, "expected_value", 0.0) or 0.0),
        acceptance_probability=float(getattr(dwe_opp, "acceptance_probability", 0.0) or 0.0),
        risk_score=float(getattr(dwe_opp, "risk", 0.5) or 0.5),
        barrier_score=float(zb.total if zb else 0.0),
        experience_required=experience_required,
        experience_requirement=getattr(dwe_opp, "experience_requirement", None),
        entry_mechanism=entry_mechanism,
        portfolio_required=bool(getattr(dwe_opp, "portfolio_required", False)),
        interview_required=bool(getattr(dwe_opp, "interview_required", False)),
        technical_test_required=bool(getattr(dwe_opp, "technical_test_required", False)),
        registration_required=bool(getattr(dwe_opp, "registration_required", False)),
        technology_tags=list(getattr(dwe_opp, "technology_tags", []) or []),
        language_required=getattr(dwe_opp, "language_required", ""),
        estimated_time_hours=float(getattr(dwe_opp, "estimated_time_hours", 0.0) or 0.0),
        difficulty=difficulty,
        status=GenomeStatus.DISCOVERED,
        employment_type=employment_type,
        metadata={
            "dwe_original_id": getattr(dwe_opp, "id", None),
            "company": getattr(dwe_opp, "company", ""),
            "country": getattr(dwe_opp, "country", ""),
            "reputation": float(getattr(dwe_opp, "reputation", 0.5) or 0.5),
            "stability": float(getattr(dwe_opp, "stability", 0.5) or 0.5),
            "compatibility": float(getattr(dwe_opp, "compatibility", 0.5) or 0.5),
            "accepts_beginner": bool(getattr(dwe_opp, "accepts_beginner", True)),
            "accepts_freelancers": bool(getattr(dwe_opp, "accepts_freelancers", True)),
            "accepts_individuals": bool(getattr(dwe_opp, "accepts_individuals", True)),
            "accepts_ai_tools": bool(getattr(dwe_opp, "accepts_ai_tools", True)),
            "asynchronous": bool(getattr(dwe_opp, "asynchronous", True)),
            "specialization": getattr(dwe_opp, "specialization", None),
            "hourly_rate_usd": getattr(dwe_opp, "hourly_rate_usd", None),
            "time_to_first_work_hours": getattr(dwe_opp, "time_to_first_work_hours", None),
            "rate_source": getattr(dwe_opp, "rate_source", "unknown"),
        },
    )


# =============================================================================
# Mapper: Legacy Intel Opportunity → Genome
# =============================================================================


def map_legacy_opportunity_to_genome(legacy_opp: Any) -> OpportunityGenome:
    """Convert cores.opportunity.models.Opportunity → OpportunityGenome."""
    category = getattr(legacy_opp, "category", "dev_bounty")
    platform = getattr(legacy_opp, "platform", "unknown")

    # Try to map platform to WorkPlatform enum
    try:
        work_platform = WorkPlatform(platform.lower())
    except ValueError:
        work_platform = WorkPlatform.OTHER

    # Map legacy score to zero barrier score
    score = getattr(legacy_opp, "score", None)
    zb = None
    if score:
        overall = getattr(score, "overall", 0.5)
        zb = ZeroBarrierScore(
            total=overall * 100,
            factors={"legacy_overall": overall},
            weights={"legacy_overall": 1.0},
            barrier_level=_score_to_barrier_level(overall),
        )

    return OpportunityGenome(
        id=getattr(legacy_opp, "id", _gen_id()),
        external_id=getattr(legacy_opp, "id", ""),
        source=GenomeSource.LEGACY_INTEL,
        platform=work_platform.value,
        title=getattr(legacy_opp, "name", ""),
        description="",
        url=getattr(legacy_opp, "public_url", "") or "",
        category=category,
        subcategory=getattr(legacy_opp, "subcategory", None),
        work_stream=_category_to_work_stream(category),
        reward=float(getattr(legacy_opp, "reward", 0.0) or 0.0),
        currency="USD",
        payment_method=PaymentMethod.OTHER,
        time_to_payout_days=None,
        zero_barrier_score=zb,
        expected_value=float(getattr(score, "expected_value", 0.0) if score else 0.0),
        acceptance_probability=float(getattr(score, "acceptance_probability", 0.0) if score else 0.0),
        risk_score=float(getattr(score, "risk", 0.5) if score else 0.5),
        barrier_score=float(zb.total if zb else 0.0),
        experience_required=ExperienceLevel.NONE,
        technology_tags=list(getattr(legacy_opp, "technology_tags", []) or []),
        language_required="english",
        estimated_time_hours=float(getattr(legacy_opp, "estimated_effort_hours", 0.0) or 0.0),
        difficulty=DifficultyLevel.INTERMEDIATE,
        status=GenomeStatus.DISCOVERED,
        employment_type=EmploymentType.CONTRACT,
        metadata={
            "legacy_original_id": getattr(legacy_opp, "id", None),
            "legacy_confidence": float(getattr(legacy_opp, "confidence", 0.5)),
            "legacy_priority": getattr(legacy_opp, "priority", "medium"),
            "legacy_source_type": getattr(legacy_opp, "source", {}).get("type", "unknown")
            if hasattr(getattr(legacy_opp, "source", None), "get")
            else "unknown",
            "legacy_source_name": getattr(legacy_opp, "source", {}).get("name", "")
            if hasattr(getattr(legacy_opp, "source", None), "get")
            else "",
            "legacy_scope_summary": getattr(legacy_opp, "scope_summary", None),
            "legacy_reward_info": getattr(legacy_opp, "reward_info", None),
            "legacy_metadata": getattr(legacy_opp, "metadata", {}),
        },
    )


# =============================================================================
# Mapper: Database Models → Genome
# =============================================================================


def map_finding_to_genome(finding: Any, target: Any | None = None, report: Any | None = None) -> OpportunityGenome:
    """Convert database/models.Finding → OpportunityGenome (for bug bounty findings)."""
    target = target or getattr(finding, "target", None)
    report = report or getattr(finding, "report", None)

    # Determine category from finding type
    vuln_type = getattr(finding, "vulnerability_type", "unknown")
    category = _vuln_type_to_category(vuln_type)

    # Payment from report
    reward = 0.0
    currency = "USD"
    if report:
        reward = float(getattr(report, "confirmed_reward", getattr(report, "estimated_reward", 0.0)) or 0.0)
        currency = getattr(report, "currency", "USD")

    # Time to payout
    time_to_payout = None
    if report and getattr(report, "created_at", None):
        if hasattr(finding, "created_at") and finding.created_at:
            delta = report.created_at - finding.created_at
            time_to_payout = delta.total_seconds() / 86400

    return OpportunityGenome(
        id=_gen_id(),
        external_id=str(getattr(finding, "id", _gen_id())),
        source=GenomeSource.DATABASE,
        platform="bug_bounty",  # Will be refined with program info
        title=getattr(finding, "title", "Untitled Finding"),
        description=getattr(finding, "description", "") or "",
        url="",
        category=category,
        subcategory=vuln_type,
        work_stream=WorkStream.BUG_BOUNTY,
        reward=reward,
        currency=currency,
        payment_method=PaymentMethod.OTHER,
        time_to_payout_days=time_to_payout,
        zero_barrier_score=None,
        expected_value=reward * 0.3,  # Conservative EV for findings
        acceptance_probability=0.3,
        risk_score=0.5,
        barrier_score=50.0,
        experience_required=ExperienceLevel.MID,
        technology_tags=[vuln_type],
        language_required="english",
        estimated_time_hours=8.0,
        difficulty=DifficultyLevel.INTERMEDIATE,
        status=GenomeStatus.DISCOVERED,
        employment_type=EmploymentType.BOUNTY,
        metadata={
            "db_finding_id": getattr(finding, "id", None),
            "db_target_id": getattr(target, "id", None) if target else None,
            "db_report_id": getattr(report, "id", None) if report else None,
            "severity": getattr(finding, "severity", "medium"),
            "finding_status": getattr(finding, "status", "open"),
            "target_name": getattr(target, "name", "") if target else "",
            "target_domain": getattr(target, "domain", "") if target else "",
        },
    )


# =============================================================================
# Mapper: WorkItem / WorkBank → Genome
# =============================================================================


def map_work_item_to_genome(work_item: Any) -> OpportunityGenome:
    """Convert cores.direct_work_engine.workbank.WorkItem → OpportunityGenome."""
    opp = getattr(work_item, "opportunity", None)
    if opp:
        return map_dwe_opportunity_to_genome(opp)

    # Fallback if no opportunity attached
    return OpportunityGenome(
        id=getattr(work_item, "id", _gen_id()),
        external_id=str(getattr(work_item, "id", _gen_id())),
        source=GenomeSource.DIRECT_WORK,
        platform=getattr(work_item, "platform", WorkPlatform.OTHER),
        title=getattr(work_item, "title", "Work Item"),
        description=getattr(work_item, "description", ""),
        url=getattr(work_item, "url", ""),
        category=getattr(work_item, "category", OpportunityCategory.DEV_BOUNTY),
        subcategory=None,
        work_stream=_category_to_work_stream(getattr(work_item, "category", OpportunityCategory.DEV_BOUNTY)),
        reward=float(getattr(work_item, "reward", 0.0) or 0.0),
        currency="USD",
        payment_method=PaymentMethod.PLATFORM_CREDIT,
        time_to_payout_days=None,
        zero_barrier_score=None,
        expected_value=float(getattr(work_item, "reward", 0.0) or 0.0),
        acceptance_probability=0.5,
        risk_score=0.5,
        barrier_score=50.0,
        experience_required=ExperienceLevel.NONE,
        technology_tags=[],
        language_required="english",
        estimated_time_hours=0.0,
        difficulty=DifficultyLevel.INTERMEDIATE,
        status=_work_item_state_to_genome(getattr(work_item, "state", "discovered")),
        employment_type=EmploymentType.BOUNTY,
        metadata={
            "work_item_id": getattr(work_item, "id", None),
            "deliverables": getattr(work_item, "deliverables", []),
            "state": getattr(work_item, "state", "discovered"),
        },
    )


# =============================================================================
# Mapper: UserProfile → Genome (for compatibility scoring)
# =============================================================================


def map_user_profile_to_genome(user_profile: Any) -> dict[str, Any]:
    """Extract compatibility-relevant fields from UserProfile for scoring."""
    return {
        "skills": list(getattr(user_profile, "skills", []) or []),
        "experience_level": getattr(user_profile, "experience_level", ExperienceLevel.NONE).value
        if hasattr(getattr(user_profile, "experience_level", None), "value")
        else str(getattr(user_profile, "experience_level", ExperienceLevel.NONE)),
        "languages": list(getattr(user_profile, "languages", {"es", "en"}) or {"es", "en"}),
        "country": getattr(user_profile, "country", "Argentina"),
        "remote_only": bool(getattr(user_profile, "remote_only", True)),
        "accepts_ai_tools": bool(getattr(user_profile, "accepts_ai_tools", True)),
        "availability_hours": float(getattr(user_profile, "availability_hours", 40.0) or 40.0),
        "has_portfolio": bool(getattr(user_profile, "has_portfolio", False)),
        "preferred_payment_methods": [
            pm.value if hasattr(pm, "value") else str(pm)
            for pm in getattr(user_profile, "preferred_payment_methods", [])
        ],
        "preferred_currencies": list(getattr(user_profile, "preferred_currencies", ["USD"]) or ["USD"]),
        "preferred_employment_types": [
            et.value if hasattr(et, "value") else str(et)
            for et in getattr(user_profile, "preferred_employment_types", [])
        ],
        "platform_success_rates": dict(getattr(user_profile, "platform_success_rates", {}) or {}),
        "category_success_rates": dict(getattr(user_profile, "category_success_rates", {}) or {}),
        "total_earnings": float(getattr(user_profile, "total_earnings", 0.0) or 0.0),
        "applications_submitted": int(getattr(user_profile, "applications_submitted", 0) or 0),
        "applications_accepted": int(getattr(user_profile, "applications_accepted", 0) or 0),
        "avg_time_to_payment_days": float(getattr(user_profile, "avg_time_to_payment_days", 0.0) or 0.0),
    }


# =============================================================================
# Helpers
# =============================================================================


def _extract_external_id(obj: Any) -> str:
    """Extract platform-specific external ID from various object types."""
    for attr in ("external_id", "ext_id", "program_id", "contest_id", "bounty_id", "report_id", "finding_id"):
        if hasattr(obj, attr) and getattr(obj, attr):
            return str(getattr(obj, attr))
    return str(getattr(obj, "id", _gen_id()))


def _category_to_work_stream(category: str) -> str:
    """Map OpportunityCategory to WorkStream."""
    category = category.lower().replace("-", "_")

    bug_bounty_cats = {
        "bug_bounty",
        "security_research",
        "oss_bounties",
        "reverse_engineering",
        "malware_analysis",
        "smart_contracts",
        "competitions",
    }
    dev_bounty_cats = {
        "dev_bounty",
        "software_engineering",
        "backend",
        "frontend",
        "full_stack",
        "devops",
        "cloud",
        "infrastructure",
        "api_development",
        "sdk_development",
        "browser_automation",
        "qa_automation",
        "web_scraping",
        "code_review",
        "mobile_development",
        "desktop_development",
        "embedded",
        "iot",
        "blockchain_development",
    }
    ai_work_cats = {
        "ai_evaluation",
        "data_annotation",
        "synthetic_data",
        "ai_engineering",
        "ml_engineering",
        "llm_engineering",
        "prompt_engineering",
    }
    game_dev_cats = {"game_development"}
    open_source_cats = {"open_source", "oss_bounties"}
    tech_content_cats = {"technical_writing", "documentation", "code_review"}

    if category in bug_bounty_cats:
        return WorkStream.BUG_BOUNTY
    if category in dev_bounty_cats:
        return WorkStream.DEV_BOUNTY
    if category in ai_work_cats:
        return WorkStream.AI_WORK
    if category in game_dev_cats:
        return WorkStream.GAME_DEV
    if category in open_source_cats:
        return WorkStream.OPEN_SOURCE
    if category in tech_content_cats:
        return WorkStream.TECH_CONTENT
    return WorkStream.DEV_BOUNTY


def _vuln_type_to_category(vuln_type: str) -> str:
    """Map vulnerability type to OpportunityCategory."""
    vt = vuln_type.lower()
    if vt in ("idor", "broken_access_control"):
        return OpportunityCategory.BUG_BOUNTY
    if vt in ("xss", "csrf"):
        return OpportunityCategory.BUG_BOUNTY
    if vt in ("sqli", "sql_injection"):
        return OpportunityCategory.BUG_BOUNTY
    if vt in ("ssrf",):
        return OpportunityCategory.BUG_BOUNTY
    if vt in ("rce", "remote_code_execution"):
        return OpportunityCategory.SECURITY_RESEARCH
    if vt in ("smart_contract", "reentrancy", "defi"):
        return OpportunityCategory.SMART_CONTRACTS
    return OpportunityCategory.BUG_BOUNTY


def _score_to_barrier_level(score: float) -> BarrierLevel:
    """Map 0-1 score to BarrierLevel."""
    if score >= 0.9:
        return BarrierLevel.ZERO
    if score >= 0.75:
        return BarrierLevel.VERY_LOW
    if score >= 0.5:
        return BarrierLevel.LOW
    if score >= 0.25:
        return BarrierLevel.MEDIUM
    return BarrierLevel.HIGH


def _work_item_state_to_genome(state: str) -> str:
    """Map WorkItem state to GenomeStatus."""
    mapping = {
        "discovered": GenomeStatus.DISCOVERED,
        "qualified": GenomeStatus.QUALIFIED,
        "selected": GenomeStatus.SELECTED,
        "prepared": GenomeStatus.PREPARED,
        "executing": GenomeStatus.EXECUTING,
        "validating": GenomeStatus.VALIDATING,
        "delivering": GenomeStatus.DELIVERING,
        "delivered": GenomeStatus.LEARNED,
        "paid": GenomeStatus.PAID,
        "archived": GenomeStatus.ARCHIVED,
        "rejected": GenomeStatus.ARCHIVED,
    }
    return mapping.get(state.lower(), GenomeStatus.DISCOVERED)
