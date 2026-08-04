"""Direct Work Engine API router.

Exposes the Zero Barrier / opportunity-intelligence engine so Mission Control
can consume it: score opportunities, get ranked recommendations, and fold real
outcomes back into the user profile (feedback loop). No auto-submission here —
sending personal information always requires approval elsewhere.
"""

from __future__ import annotations

import logging
from dataclasses import fields
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter
from cores.direct_work_engine.engine import DirectWorkEngine
from cores.direct_work_engine.extension import ExtensionEvaluator
from cores.direct_work_engine.feedback import LearningRecord, apply_learning
from cores.direct_work_engine.models import (
    DifficultyLevel,
    EmploymentType,
    ExperienceLevel,
    GameDevSpecialization,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    RankedOpportunity,
    UserProfile,
    WorkPlatform,
)
from cores.direct_work_engine.negotiation import TermAnalyzer
from cores.direct_work_engine.scoring import ZeroBarrierScorer
from cores.direct_work_engine.skill_gap import SkillAmplifier
from cores.direct_work_engine.workbank import get_workbank

logger = logging.getLogger("ownex.api.direct_work")

router = APIRouter(prefix="/direct-work", tags=["direct-work"])

_engine: DirectWorkEngine | None = None


def _ensure_default_adapters(engine: DirectWorkEngine) -> None:
    """Register real discovery sources the first time the engine is used.

    Idempotent and never raises: a broken adapter must not take the engine down.
    """
    from api.adapters.legacy import build_default_adapters

    for adapter in build_default_adapters():
        if adapter.source.platform not in engine.discovery.adapters:
            engine.register_adapter(adapter)
            logger.info("Registered real discovery adapter: %s", adapter.source.name)


def get_engine() -> DirectWorkEngine:
    """Get the process-wide Direct Work Engine singleton."""
    global _engine
    if _engine is None:
        _engine = DirectWorkEngine()
        _ensure_default_adapters(_engine)
    return _engine


# ---------------------------------------------------------------------------
# Serialization helpers (dict <-> DWE dataclasses, enum-aware)
# ---------------------------------------------------------------------------

_ENUM_FIELDS: dict[str, type[StrEnum]] = {
    "platform": WorkPlatform,
    "category": OpportunityCategory,
    "payment_method": PaymentMethod,
    "difficulty": DifficultyLevel,
    "experience_required": ExperienceLevel,
    "employment_type": EmploymentType,
    "specialization": GameDevSpecialization,
}

_PROFILE_ENUM_FIELDS: dict[str, type[StrEnum]] = {
    "experience_level": ExperienceLevel,
}

_PROFILE_LIST_ENUM_FIELDS: dict[str, type[StrEnum]] = {
    "preferred_payment_methods": PaymentMethod,
    "preferred_employment_types": EmploymentType,
    "preferred_categories": OpportunityCategory,
}


def _resolve(value: Any, enum_cls: type[StrEnum] | None) -> Any:
    if value is None or enum_cls is None:
        return value
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except ValueError:
        return value


def _opportunity_from_dict(data: dict[str, Any]) -> Opportunity:
    allowed = {f.name for f in fields(Opportunity)}
    kwargs: dict[str, Any] = {k: v for k, v in data.items() if k in allowed}
    for name, enum_cls in _ENUM_FIELDS.items():
        if name in kwargs:
            kwargs[name] = _resolve(kwargs[name], enum_cls)
    return Opportunity(**kwargs)


def _opportunity_to_dict(op: Opportunity) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in fields(Opportunity):
        value = getattr(op, f.name)
        if isinstance(value, StrEnum):
            value = value.value
        elif isinstance(value, list):
            value = [item.value if isinstance(item, StrEnum) else item for item in value]
        out[f.name] = value
    return out


def _profile_from_dict(data: dict[str, Any]) -> UserProfile:
    allowed = {f.name for f in fields(UserProfile)}
    kwargs: dict[str, Any] = {k: v for k, v in data.items() if k in allowed}
    if "languages" in kwargs and isinstance(kwargs["languages"], list):
        kwargs["languages"] = set(kwargs["languages"])
    if "skills" in kwargs and isinstance(kwargs["skills"], list):
        kwargs["skills"] = set(kwargs["skills"])
    for name, enum_cls in _PROFILE_ENUM_FIELDS.items():
        if name in kwargs:
            kwargs[name] = _resolve(kwargs[name], enum_cls)
    for name, enum_cls in _PROFILE_LIST_ENUM_FIELDS.items():
        if name in kwargs and isinstance(kwargs[name], list):
            kwargs[name] = [_resolve(item, enum_cls) for item in kwargs[name]]
    if "platform_success_rates" in kwargs and isinstance(kwargs["platform_success_rates"], dict):
        kwargs["platform_success_rates"] = {str(k): float(v) for k, v in kwargs["platform_success_rates"].items()}
    if "category_success_rates" in kwargs and isinstance(kwargs["category_success_rates"], dict):
        kwargs["category_success_rates"] = {str(k): float(v) for k, v in kwargs["category_success_rates"].items()}
    return UserProfile(**kwargs)


def _profile_to_dict(profile: UserProfile) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in fields(UserProfile):
        value = getattr(profile, f.name)
        if isinstance(value, StrEnum):
            value = value.value
        elif isinstance(value, set):
            value = sorted(value)
        elif isinstance(value, list):
            value = [item.value if isinstance(item, StrEnum) else item for item in value]
        out[f.name] = value
    return out


# Income-maximizing default profile for the daily surfaces (public reward work):
# outcome-based employment (bounties/microtasks/challenges/prizes, no hiring
# funnel), public reward categories, no interview/portfolio/experience, and a
# minimum credible reward floor. Selection-world work is excluded by preference.
_INCOME_MAX_DEFAULT_PROFILE: dict[str, Any] = {
    "name": "Adriel",
    "country": "Argentina",
    "languages": ["es", "en"],
    "skills": ["python", "go", "unity", "typescript"],
    "experience_level": "none",
    "remote_only": True,
    "accepts_ai_tools": True,
    "has_portfolio": False,
    "preferred_employment_types": ["bounty", "open_call", "microtask", "challenge", "prize"],
    "preferred_categories": [
        "bug_bounty",
        "dev_bounty",
        "security_research",
        "oss_bounties",
        "ai_evaluation",
        "data_annotation",
        "synthetic_data",
        "web_scraping",
    ],
    "excluded_categories": ["full_stack", "frontend", "backend", "cloud", "devops"],
    "min_payment": 10.0,
}


def _income_max_profile(profile: dict[str, Any] | None) -> UserProfile:
    """Merge a caller-supplied profile over the income-max defaults (caller wins)."""
    base = dict(_INCOME_MAX_DEFAULT_PROFILE)
    if profile:
        base.update(profile)
    return _profile_from_dict(base)


def _record_from_dict(data: dict[str, Any]) -> LearningRecord:
    category = data.get("category")
    return LearningRecord(
        platform=str(data.get("platform", "")),
        accepted=bool(data.get("accepted", False)),
        amount=float(data.get("amount", 0.0)),
        category=_resolve(category, OpportunityCategory) if category else None,
        time_to_payout_days=(
            float(data["time_to_payout_days"]) if data.get("time_to_payout_days") is not None else None
        ),
    )


def _ranked_to_dict(ranked: RankedOpportunity) -> dict[str, Any]:
    zb = ranked.zero_barrier_score
    return {
        "rank": ranked.rank,
        "opportunity": _opportunity_to_dict(ranked.opportunity),
        "zero_barrier_score": {
            "total": zb.total if zb else 0.0,
            "barrier_level": zb.barrier_label if zb else "unknown",
            "enablers": zb.enablers if zb else [],
            "blockers": zb.blockers if zb else [],
        },
        "expected_value": ranked.expected_value,
        "acceptance_probability": ranked.acceptance_probability,
        "compatibility_score": ranked.compatibility_score,
        "speed_score": ranked.speed_score,
        "reputation_score": ranked.reputation_score,
        "risk_score": ranked.risk_score,
        "overall_recommendation_score": ranked.overall_recommendation_score,
        "strategy": ranked.strategy,
        "recommendation_reasoning": ranked.recommendation_reasoning,
    }


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------


class ScoreRequest(BaseModel):
    opportunities: list[dict[str, Any]] = []


class RecommendRequest(BaseModel):
    profile: dict[str, Any]
    opportunities: list[dict[str, Any]] = []
    limit: int = 10
    mode: str = "balanced"


class LearnRequest(BaseModel):
    profile: dict[str, Any]
    records: list[dict[str, Any]] = []


class DiscoverRequest(BaseModel):
    limit: int = 20


class OpportunityOnlyRequest(BaseModel):
    opportunity: dict[str, Any]


class SkillGapRequest(BaseModel):
    opportunity: dict[str, Any]
    profile: dict[str, Any]


class WorkBankCycleRequest(BaseModel):
    opportunities: list[dict[str, Any]] = []
    target: int = 100
    profile: dict[str, Any] | None = None


class ExtensionRequest(BaseModel):
    name: str
    description: str
    proposed_by: str = "user"


class DailyBriefRequest(BaseModel):
    profile: dict[str, Any] | None = None
    limit: int = 5
    mode: str = "fast_income"


class DeliverPrepareRequest(BaseModel):
    item_id: str


class AnalysisCardRequest(BaseModel):
    opportunity: dict[str, Any]
    profile: dict[str, Any] | None = None


class IncomeProjectionRequest(BaseModel):
    work_income_usd_per_month: float
    savings_usd_per_month: float
    start_capital_usd: float = 0.0
    annual_return_rate: float = 0.10
    target_monthly_usd: float = 100_000.0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status")
async def direct_work_status() -> dict[str, Any]:
    """Engine status: running state, stats, registered platforms and sources."""
    return get_engine().get_status()


@router.post("/filter")
async def direct_work_filter(request: ScoreRequest) -> dict[str, Any]:
    """Strict filtering gate: which opportunities pass and why the rest are rejected.

    Deterministic hard-reject rules (unclear payment, non-remote, gift-card-only
    payout, hiring funnel). Quality over quantity: 10 excellent > 1000 useless.
    """
    from cores.direct_work_engine.filters import StrictFilter

    opportunities = [_opportunity_from_dict(o) for o in request.opportunities]
    rejected = StrictFilter().validate(opportunities)
    passed = [o.id for o in opportunities if o.id not in rejected]
    return {
        "analyzed": len(opportunities),
        "passed": len(passed),
        "rejected": len(rejected),
        "passed_ids": passed,
        "rejected_reasons": rejected,
    }


@router.post("/score")
async def direct_work_score(request: ScoreRequest) -> dict[str, Any]:
    """Score opportunities with the Zero Barrier spectrum and sort by it."""
    opportunities = [_opportunity_from_dict(o) for o in request.opportunities]
    scored = ZeroBarrierScorer().score_opportunities(opportunities)
    return {"scored": [_opportunity_to_dict(o) for o in scored]}


@router.post("/recommend")
async def direct_work_recommend(request: RecommendRequest) -> dict[str, Any]:
    """Rank opportunities for a user profile; returns ordered RankedOpportunities.

    When no opportunities are supplied, the engine discovers them from its
    registered real adapters first (Opire, IssueHunt, Freelancer).
    """
    profile = _profile_from_dict(request.profile)
    opportunities = [_opportunity_from_dict(o) for o in request.opportunities]
    if not opportunities:
        opportunities = await get_engine().discovery.discover_all()
    ranked = get_engine().recommender.recommend(opportunities, profile, limit=request.limit, mode=request.mode)
    return {"ranked": [_ranked_to_dict(r) for r in ranked]}


@router.post("/discover")
async def direct_work_discover(request: DiscoverRequest) -> dict[str, Any]:
    """Run a live scan of registered sources and return scored opportunities.

    Implements the "morning scan" flow: discover real opportunities from the
    registered adapters, score them by Zero Barrier, and return the top N.
    """
    engine = get_engine()
    opportunities = await engine.discovery.discover_all()
    scored = engine.scorer.score_opportunities(opportunities)
    return {
        "discovered": len(scored),
        "platforms": [p.value for p in engine.discovery.get_registered_platforms()],
        "opportunities": [_opportunity_to_dict(o) for o in scored[: request.limit]],
    }


@router.post("/negotiate")
async def direct_work_negotiate(request: OpportunityOnlyRequest) -> dict[str, Any]:
    """Assess an opportunity's commercial terms (rate, payment risk, payout)."""
    from dataclasses import asdict

    opportunity = _opportunity_from_dict(request.opportunity)
    assessment = TermAnalyzer().assess(opportunity)
    return asdict(assessment)


@router.post("/skill-gap")
async def direct_work_skill_gap(request: SkillGapRequest) -> dict[str, Any]:
    """Measure skill distance and build a learning plan for an opportunity."""
    from dataclasses import asdict

    opportunity = _opportunity_from_dict(request.opportunity)
    profile = _profile_from_dict(request.profile)
    report = SkillAmplifier().analyze(opportunity, profile)
    return asdict(report)


@router.post("/workbank/cycle")
async def direct_work_workbank_cycle(request: WorkBankCycleRequest) -> dict[str, Any]:
    """Run a work-bank cycle: discover + prepare zero-barrier jobs until delivery-ready."""
    engine = get_engine()
    opportunities = [_opportunity_from_dict(o) for o in request.opportunities]
    if not opportunities:
        opportunities = await engine.discovery.discover_all()
    bank = get_workbank()
    return bank.daily_cycle(opportunities, target=request.target, profile=_income_max_profile(request.profile))


@router.get("/workbank")
async def direct_work_workbank() -> dict[str, Any]:
    """Work-bank state: ready-to-deliver jobs, needs-access items, monthly projection."""
    return get_workbank().to_dict()


@router.post("/workbank/{item_id}/deliver/prepare")
async def direct_work_deliver_prepare(item_id: str) -> dict[str, Any]:
    """Prepare a delivery package for a work-bank item (files ready to submit on disk).

    Bridges the Work Bank into the existing AssistedExecutor: builds a platform
    package (README/proposal/work files), saves it to disk, and returns where it
    is plus one-click guidance. Does NOT submit anything.
    """
    from core.opportunity.executors.assisted_mode import AssistedExecutor

    item = get_workbank().get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Work-bank item not found")

    executor = AssistedExecutor(base_executor=None)
    opportunity = {
        "platform": str(item.platform),
        "id": item.id,
        "title": item.title,
        "description": item.description or " ".join(item.deliverables),
        "url": item.url or "",
    }
    prepared = await executor.prepare_work(opportunity)
    work_dir = await executor.save_work_to_disk(prepared)
    return {
        "item_id": item.id,
        "platform": str(item.platform),
        "title": item.title,
        "ready_to_deliver": item.ready_to_deliver,
        "need_user_action": "Subir los archivos generados y seguir la guía para entregar",
        "package_path": str(work_dir),
        "files": sorted(prepared.files.keys()),
        "submission_url": prepared.submission_url,
        "guide_url": prepared.guide_url,
        "deliverables": item.deliverables,
    }


@router.post("/workbank/{item_id}/deliver/approve")
async def direct_work_deliver_approve(item_id: str) -> dict[str, Any]:
    """Mark a work-bank item as delivered (user confirmed the submission landed).

    Closes the loop: the item moves to ``delivered`` and the outcome is folded
    into the user profile so future recommendations learn from it.
    """
    bank = get_workbank()
    item = bank.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Work-bank item not found")
    bank.mark_delivered(item_id)

    profile = UserProfile(
        name="Adriel",
        country="Argentina",
        languages={"es", "en"},
        skills={"python", "go", "unity", "typescript"},
        remote_only=True,
    )
    category = getattr(item, "category", None)
    record = LearningRecord(
        platform=str(item.platform),
        accepted=True,
        amount=float(item.reward or 0.0),
        category=_resolve(category, OpportunityCategory) if category else None,
        time_to_payout_days=None,
    )
    apply_learning(profile, [record])

    return {
        "item_id": item.id,
        "status": "delivered",
        "reward": item.reward,
        "message": "Entregado. El resultado se plegó al perfil para mejores recomendaciones.",
    }


@router.get("/deliver/pending")
async def direct_work_deliver_pending() -> dict[str, Any]:
    """Items ready to deliver right now (the assisted delivery queue)."""
    bank = get_workbank()
    ready = bank.best_ready(limit=50)
    return {
        "count": len(ready),
        "items": [
            {
                "id": i.id,
                "title": i.title,
                "platform": i.platform,
                "reward": i.reward,
                "deliverables": i.deliverables,
                "url": i.url,
            }
            for i in ready
        ],
    }


@router.post("/analysis-card")
async def direct_work_analysis_card(request: AnalysisCardRequest) -> dict[str, Any]:
    """The full intelligence picture for one opportunity — one object, no digging.

    Unifies every OWNEX analysis a single opportunity: identity fields, Zero
    Barrier score, recommendation ranking, commercial negotiation terms and the
    exact access requirement to actually deliver/collect on its platform.
    """
    from dataclasses import asdict
    from datetime import UTC, datetime

    from cores.direct_work_engine.workbank import PLATFORM_ACCESS, platform_tier

    engine = get_engine()
    opportunity = _opportunity_from_dict(request.opportunity)
    profile = _income_max_profile(request.profile)

    scored = engine.scorer.score(opportunity)
    ranked = engine.recommender.recommend([opportunity], profile, limit=1)
    rank = ranked[0] if ranked else None
    terms = TermAnalyzer().assess(opportunity)
    gap = SkillAmplifier().analyze(opportunity, profile)

    platform_key = opportunity.platform.value if hasattr(opportunity.platform, "value") else str(opportunity.platform)
    access_status, requirement = PLATFORM_ACCESS.get(
        platform_key, ("needs_manual_setup", "Configurar el acceso a la plataforma.")
    )

    source = engine.discovery.adapters.get(opportunity.platform)
    tier = source.source.tier if source else platform_tier(access_status)
    cadence = source.source.analysis_cadence_hours if source else 24

    return {
        "card_id": f"{platform_key}:{opportunity.id}",
        "generated_at": datetime.now(UTC).isoformat(),
        "opportunity": _opportunity_to_dict(opportunity),
        "zero_barrier_score": {
            "total": round(scored.total, 1),
            "barrier_label": scored.barrier_label,
            "enablers": scored.enablers,
            "blockers": scored.blockers,
            "reasoning": scored.reasoning,
        },
        "recommendation": _ranked_to_dict(rank) if rank else None,
        "negotiation": asdict(terms),
        "skill_gap": asdict(gap),
        "access": {
            "platform": platform_key,
            "status": access_status,
            "requirement": requirement,
            "tier": tier,
            "analysis_cadence_hours": cadence,
        },
    }


@router.post("/market-report")
async def direct_work_market_report() -> dict[str, Any]:
    """The Market Evolution Engine report (spec: daily market intelligence).

    Scores every curated ecosystem with OVOS (0-100), assigns the S/A/B/C/REJECT
    friction tier, applies Automatic Retirement, persists the knowledge base and
    returns the consolidated market report: new ecosystems discovered, high
    confidence opportunities, emerging categories, rejected platforms, highest
    EV and recommended actions.
    """
    from cores.direct_work_engine.market_evolution import get_market_evolution_engine

    report = get_market_evolution_engine().analyze()
    report.pop("ecosystems", None)
    return report


@router.post("/income-projector")
async def direct_work_income_projector(request: IncomeProjectionRequest) -> dict[str, Any]:
    """Honest time-to-income projection: work income → capital → portfolio income.

    Compounds real monthly savings at a conservative annual return and reports
    when portfolio income crosses the work income and then a target monthly USD
    figure (default $100k). No fabricated returns — the rate is an explicit input.
    """
    from cores.direct_work_engine.income_projection import IncomeProjector

    return IncomeProjector.project(
        work_income_usd_per_month=request.work_income_usd_per_month,
        savings_usd_per_month=request.savings_usd_per_month,
        start_capital_usd=request.start_capital_usd,
        annual_return_rate=request.annual_return_rate,
        target_monthly_usd=request.target_monthly_usd,
    ).to_dict()


@router.post("/income-dashboard")
async def direct_work_income_dashboard(request: IncomeProjectionRequest) -> dict[str, Any]:
    """One-pane financial snapshot: Work Bank + Revenue + Income Projector.

    Answers "does this system improve my money?" in a single call: jobs found /
    prepared / delivered, payouts collected + pending, per-platform ROI, and the
    time-to-target projection (same inputs as /income-projector).
    """
    from cores.direct_work_engine.income_dashboard import get_income_dashboard

    return get_income_dashboard().snapshot(
        work_income_usd_per_month=request.work_income_usd_per_month,
        savings_usd_per_month=request.savings_usd_per_month,
        start_capital_usd=request.start_capital_usd,
        annual_return_rate=request.annual_return_rate,
        target_monthly_usd=request.target_monthly_usd,
    )


@router.post("/plan/objective")
async def direct_work_plan_objective(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Universal request understanding: turn a loose request into a full blueprint.

    "Magic Experience Engine" — takes plain-language objectives ("create a
    website", "prepare a Fiverr delivery", "analyze this bug") and returns
    Goal → Requirements → Plan → Tools → Verification → Deliverable with an
    honest Time Compression estimate (normal hours vs OWNEX-optimized hours),
    the automation % and the human decisions that remain.
    """
    from cores.direct_work_engine.execution_planner import plan_objective

    objective = (payload or {}).get("objective", "")
    result = plan_objective(objective)
    return result.to_dict() if result.objective else {"error": result.error, "objective": objective}


@router.post("/plan/opportunity")
async def direct_work_plan_opportunity(
    payload: dict[str, Any] | None = None,
    success_probability: float | None = None,
) -> dict[str, Any]:
    """Execution plan for an existing opportunity: report + links + EV + roadmap.

    "Opportunity Execution Engine" — the missing answer to "what do I do, what
    does OWNEX do, how long, and what's the next button". Includes direct links
    (never force the user to search), human-vs-automation split, work-reduction
    model and EV = reward × success_probability / human_hours.
    """
    from cores.direct_work_engine.execution_planner import plan_execution

    opportunity = (payload or {}).get("opportunity", {})
    platform_url = (payload or {}).get("platform_url", "")
    if isinstance(opportunity, dict) and "id" in opportunity:
        # allow {id, platform_url} shortcut to pull from the work bank
        bank = get_workbank()
        item = bank.get_item(opportunity["id"])
        if item:
            opportunity = item
    plan = plan_execution(opportunity, platform_url=platform_url, success_probability=success_probability)
    return plan.to_dict()


@router.get("/access/explain")
async def direct_work_access_explain() -> dict[str, Any]:
    """Account integration guide: what each platform needs, why, and how to unlock it.

    Explains the exact blocking requirement per supported platform so the user
    can configure accounts in minutes instead of guessing — without leaking
    secrets or inventing access that does not exist yet (tiers: 1 public, 2
    needs API key, 3 manual setup).
    """
    from cores.direct_work_engine.workbank import PLATFORM_ACCESS, TIER_CADENCE_HOURS, platform_tier

    engine = get_engine()
    registered = {p.value for p in engine.discovery.get_registered_platforms()}
    platforms = []
    for platform_key, (status, requirement) in PLATFORM_ACCESS.items():
        tier = platform_tier(status)
        platforms.append(
            {
                "platform": platform_key,
                "tier": tier,
                "access_status": status,
                "requirement": requirement,
                "analysis_cadence_hours": TIER_CADENCE_HOURS.get(tier, 24),
                "registered": platform_key in registered,
                "explanation": _access_explanation(status, requirement),
            }
        )
    platforms.sort(key=lambda p: (p["tier"], p["platform"]))
    return {
        "tiers": {
            "1": "Public — discover, prepare and deliver fully autonomously.",
            "2": "Needs an API key — set it once, then autonomous.",
            "3": "Manual setup or long-cycle proposal — OWNEX prepares, the user submits.",
        },
        "platforms": platforms,
    }


def _access_explanation(access_status: str, requirement: str) -> str:
    """Human-readable reasoning for a platform's access requirement."""
    if access_status == "public":
        return "Este canal ya está conectado: OWNEX descubre, prepara y deja el trabajo listo para entregar sin configuración manual."
    if access_status == "needs_api_key":
        reason = requirement or "Configurar una API key en la plataforma para poder operar."
        return f"Falta una API key. {reason}"
    reason = requirement or "Completar el setup manual de la cuenta en la plataforma."
    return f"Requiere un paso manual único. {reason}"


@router.post("/extensions/evaluate")
async def direct_work_extensions_evaluate(request: ExtensionRequest) -> dict[str, Any]:
    """Reason about whether a proposed capability extension is worth acquiring."""
    from dataclasses import asdict

    proposal = ExtensionEvaluator().evaluate(request.name, request.description, request.proposed_by)
    return asdict(proposal)


@router.post("/daily-brief")
async def direct_work_daily_brief(request: DailyBriefRequest) -> dict[str, Any]:
    """Morning radar: the best opportunity for this user today, plus a learning plan.

    Answers "¿cuál es el trabajo digital con mayor probabilidad de generar ingresos
    hoy?" by ranking live opportunities with the OWNEX score and closing the skill
    gap of the top pick so preparation can start immediately.
    """
    from datetime import UTC, datetime

    engine = get_engine()
    profile = _income_max_profile(request.profile)
    opportunities = await engine.discovery.discover_all()
    ranked = engine.recommender.recommend(opportunities, profile, limit=request.limit, mode=request.mode)

    top = ranked[0] if ranked else None
    learning = None
    if top:
        gap = SkillAmplifier().analyze(top.opportunity, profile)
        learning = {"missing_skills": gap.missing_skills, "plan": gap.learning_plan}

    from cores.direct_work_engine.source_intel import SourceIntelEngine

    radar = SourceIntelEngine().analyze()
    best_sources: list[dict[str, Any]] = []
    for card in radar["sources"]:
        if card["recommendation"] != "DISCOVER":
            continue
        best_sources.append(
            {
                "name": card["name"],
                "url": card["url"],
                "category": card["category"],
                "trust_score": card["trust_score"],
                "earning_potential": card["earning_potential"],
                "average_reward": card["average_reward"],
            }
        )
        if len(best_sources) >= 5:
            break

    summary = f"Scanned {len(opportunities)} opportunities. " + (
        f"Top pick: {top.opportunity.title} (score {top.overall_recommendation_score:.0f}/100)."
        if top
        else "No zero-barrier opportunities found today."
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "scanned": len(opportunities),
        "summary": summary,
        "top_opportunity": _ranked_to_dict(top) if top else None,
        "ranked": [_ranked_to_dict(r) for r in ranked],
        "learning": learning,
        "best_sources": best_sources,
    }


@router.post("/learn")
async def direct_work_learn(request: LearnRequest) -> dict[str, Any]:
    """Fold verified outcomes into the profile (success rates, earnings)."""
    profile = _profile_from_dict(request.profile)
    records = [_record_from_dict(r) for r in request.records]
    apply_learning(profile, records)
    return {"profile": _profile_to_dict(profile)}


class EvolutionRequest(BaseModel):
    profile: dict[str, Any]
    records: list[dict[str, Any]] = []
    opportunities: list[dict[str, Any]] = []
    time_invested_hours: float = 0.0
    min_evidence: int | None = None


@router.post("/evolution")
async def direct_work_evolution(request: EvolutionRequest) -> dict[str, Any]:
    """Long-term intelligence report: what to learn, what to build, where you win.

    Self-improvement loop over the tracked history:
      * lessons       — lost opportunities -> skill evolution path (learn)
      * capabilities  — market demand the user does not cover -> expansion proposal (build)
      * performance   — conversion + ROI per platform/category (income intelligence)
    """
    from cores.direct_work_engine.evolution import (
        CapabilityExpansionDetector,
        PerformanceAnalyzer,
        SkillEvolutionEngine,
        evolve_analysis,
    )

    profile = _profile_from_dict(request.profile)
    records = [_record_from_dict(r) for r in request.records]
    opportunities = [_opportunity_from_dict(o) for o in request.opportunities]

    lessons = SkillEvolutionEngine().learn_from_lost(records, profile)
    proposals = CapabilityExpansionDetector().detect(opportunities, profile, min_evidence=request.min_evidence)
    performance = PerformanceAnalyzer().analyze(records, time_invested_hours=request.time_invested_hours)
    return evolve_analysis(lessons, proposals, performance)


class SourceIntelRequest(BaseModel):
    categories: list[str] = []
    query: str | None = None
    min_trust: float | None = None


@router.post("/source-intel")
async def direct_work_source_intel(request: SourceIntelRequest) -> dict[str, Any]:
    """Platform Analysis System — the OWNEX GLOBAL RADAR over the curated source database.

    For each of the 100+ curated platforms answers the spec question:
    "where does my next hour convert best?" — Argentina compatibility, payment method,
    entry barrier, task transparency, trust score, earning potential and an OWNEX
    recommendation (DISCOVER / CONSIDER / AVOID). Also flags DWE categories with no
    source yet so the knowledge base keeps expanding.
    """
    from cores.direct_work_engine.source_intel import SourceIntelEngine

    return SourceIntelEngine().analyze(
        categories=request.categories,
        query=request.query,
        min_trust=request.min_trust,
    )


def register_adapter(adapter: BaseDiscoveryAdapter) -> None:
    """Register a real discovery adapter into the engine singleton."""
    get_engine().register_adapter(adapter)
    logger.info("Registered discovery adapter: %s", adapter.source.name)
