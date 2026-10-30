"""ONE BEST ACTION — Single, actionable next step for the user.

Given ranked opportunities, user profile, availability, and work bank state,
this engine selects the ONE best action the user should take RIGHT NOW.

It answers: "What should I do in the next hour to maximize my income?"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from cores.direct_work_engine.availability import get_availability_engine
from cores.direct_work_engine.models import (
    DifficultyLevel,
    EmploymentType,
    EntryMechanism,
    ExperienceLevel,
    ExperienceRequirement,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    RankedOpportunity,
    UserProfile,
    WorkPlatform,
    ZeroBarrierScore,
)
from cores.direct_work_engine.recommendation import (
    MAX_INCOME_RECOMMENDER_CONFIG,
    IntelligentRecommender,
)
from cores.direct_work_engine.workbank import WorkBank, WorkItem, get_workbank

logger = logging.getLogger("ownex.one_best_action")


class ActionType(StrEnum):
    """Types of actionable next steps."""

    DELIVER_NOW = "deliver_now"  # WorkItem ready_to_deliver → prepare + submit
    PREPARE_DELIVERY = "prepare_delivery"  # WorkItem needs prep → generate package
    CLAIM_OPPORTUNITY = "claim_opportunity"  # New opportunity → claim/start work
    COMPLETE_ONBOARDING = "complete_onboarding"  # Platform needs setup → finish onboarding
    LEARN_SKILL = "learn_skill"  # Skill gap for top opportunity → study
    WAIT_FOR_PAYMENT = "wait_for_payment"  # Work submitted → track payout
    RUN_WORKBANK_CYCLE = "run_workbank_cycle"  # Refresh opportunities


class Urgency(StrEnum):
    IMMEDIATE = "immediate"
    TODAY = "today"
    THIS_WEEK = "this_week"
    FLEXIBLE = "flexible"


@dataclass(slots=True)
class OneBestAction:
    """The single best action the user should take now."""

    action_type: ActionType
    title: str
    description: str
    why_now: str
    platform: str
    opportunity_id: str | None = None
    work_item_id: str | None = None
    estimated_human_hours: float = 0.0
    expected_value_usd: float = 0.0
    acceptance_probability: float = 0.0
    cash_speed_days: int | None = None
    urgency: Urgency = Urgency.TODAY
    prerequisites: list[str] = field(default_factory=list)
    url: str | None = None
    next_step_instruction: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "title": self.title,
            "description": self.description,
            "why_now": self.why_now,
            "platform": self.platform,
            "opportunity_id": self.opportunity_id,
            "work_item_id": self.work_item_id,
            "estimated_human_hours": self.estimated_human_hours,
            "expected_value_usd": self.expected_value_usd,
            "acceptance_probability": round(self.acceptance_probability, 2),
            "cash_speed_days": self.cash_speed_days,
            "urgency": self.urgency.value,
            "prerequisites": self.prerequisites,
            "url": self.url,
            "next_step_instruction": self.next_step_instruction,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class OneBestActionContext:
    """Context for generating the ONE BEST ACTION."""

    profile: UserProfile
    available_hours_today: float
    available_hours_this_week: float
    workbank: WorkBank
    ranked_opportunities: list[RankedOpportunity]
    current_time: datetime = field(default_factory=lambda: datetime.now(UTC))


class OneBestActionEngine:
    """Selects the single best next action from all available options."""

    def __init__(self) -> None:
        self.recommender = IntelligentRecommender(config=MAX_INCOME_RECOMMENDER_CONFIG)
        self.availability = get_availability_engine()
        self.workbank = get_workbank()

    def get_one_best_action(
        self,
        profile: UserProfile | None = None,
        limit: int = 10,
    ) -> OneBestAction:
        """Generate the ONE BEST ACTION for the current context."""

        if profile is None:
            profile = self._get_default_profile()

        # Get availability snapshot
        snap = self.availability.get_snapshot()
        available_today = snap.hours_today
        available_week = snap.hours_this_week

        # Get work bank state
        wb = self.workbank
        ready_to_deliver = [item for item in wb._items.values() if item.status == "ready_to_deliver"]
        needs_access = [item for item in wb._items.values() if item.status == "needs_access"]

        # Get ranked opportunities from workbank items
        opportunities = list(wb._items.values())
        opps_for_ranking = [self._workitem_to_opportunity(item) for item in opportunities]
        ranked = self.recommender.recommend(opps_for_ranking, profile, limit=limit, mode="max_income")

        # Build context
        ctx = OneBestActionContext(
            profile=profile,
            available_hours_today=available_today,
            available_hours_this_week=available_week,
            workbank=wb,
            ranked_opportunities=ranked,
        )

        # Priority 1: Something ready to DELIVER right now (cash on table)
        if ready_to_deliver:
            return self._build_deliver_now_action(ctx, ready_to_deliver[0])

        # Priority 2: Something needs PREPARATION (package generation)
        if needs_access:
            return self._build_prepare_delivery_action(ctx, needs_access[0])

        # Priority 3: High-value opportunity that can be CLAIMED now
        if ranked:
            top = ranked[0]
            if top.opportunity.employment_type in (
                EmploymentType.BOUNTY,
                EmploymentType.OPEN_CALL,
                EmploymentType.MICROTASK,
                EmploymentType.CHALLENGE,
            ):
                return self._build_claim_action(ctx, top)

        # Priority 4: Platform onboarding blocking high-value work
        if needs_access:
            return self._build_onboarding_action(ctx, needs_access[0])

        # Priority 5: Skill gap for top opportunity
        if ranked:
            top = ranked[0]
            skill_gap = self._identify_skill_gap(top, profile)
            if skill_gap:
                return self._build_learn_action(ctx, top, skill_gap)

        # Priority 6: Run work bank cycle to refresh opportunities
        return self._build_refresh_action(ctx)

    def _get_default_profile(self) -> UserProfile:
        from cores.direct_work_engine.profile_builder import IntelligentProfileBuilder

        builder = IntelligentProfileBuilder()
        return builder.build().profile

    def _workitem_to_opportunity(self, item: WorkItem) -> Opportunity:
        """Convert WorkItem to Opportunity for ranking."""
        platform = WorkPlatform(item.platform) if item.platform in WorkPlatform.__members__ else WorkPlatform.OTHER
        category = (
            OpportunityCategory(item.category)
            if item.category in OpportunityCategory.__members__
            else OpportunityCategory.SOFTWARE_ENGINEERING
        )
        employment_type = (
            EmploymentType(item.employment_type)
            if item.employment_type in EmploymentType.__members__
            else EmploymentType.CONTRACT
        )
        payment_method = (
            PaymentMethod(item.payout_method)
            if item.payout_method in PaymentMethod.__members__
            else PaymentMethod.CRYPTO
        )

        opp = Opportunity(
            id=item.id,
            title=item.title,
            platform=platform,
            category=category,
            url=item.url,
            description=item.description,
            payment=item.reward,
            currency="USDC",
            payment_method=payment_method,
            company="",
            employment_type=employment_type,
            estimated_time_hours=0.0,  # WorkItem doesn't have this; use 0 and let scorer handle
            difficulty=DifficultyLevel.INTERMEDIATE,
            experience_required=ExperienceLevel.NONE,
            portfolio_required=False,
            interview_required=False,
            technical_test_required=False,
            registration_required=False,
            time_to_payout_days=None,
            reputation=0.5,
            risk=0.5,
            payment_proven=False,
            stability=0.5,
            compatibility=0.5,
            accepts_beginner=True,
            accepts_freelancers=True,
            accepts_individuals=True,
            accepts_ai_tools=True,
            asynchronous=True,
            specialization=None,
            technology_tags=[],
            hourly_rate_usd=None,
            time_to_first_work_hours=None,
            rate_source="unknown",
            entry_mechanism=EntryMechanism.DIRECT,
            experience_requirement=ExperienceRequirement.NONE,
            zero_barrier_score=None,
            international_payment=True,
        )
        # Set zero_barrier_score from item.barrier_score
        if item.barrier_score:
            opp.zero_barrier_score = ZeroBarrierScore(total=item.barrier_score)
        return opp

    def _build_deliver_now_action(self, ctx: OneBestActionContext, item: WorkItem) -> OneBestAction:
        cash_speed = 7
        return OneBestAction(
            action_type=ActionType.DELIVER_NOW,
            title=f"Entregar: {item.title}",
            description=f"Trabajo completado listo para entregar en {item.platform}. Recompensa: ${item.reward:.0f}",
            why_now="El trabajo está 100% preparado. Entregar ahora = cobrar ahora. No hay razón para esperar.",
            platform=item.platform,
            work_item_id=item.id,
            estimated_human_hours=0.5,
            expected_value_usd=item.reward,
            acceptance_probability=0.95,
            cash_speed_days=cash_speed,
            urgency=Urgency.IMMEDIATE,
            prerequisites=["Revisar deliverables", "Confirmar submission URL"],
            url=item.url,
            next_step_instruction=f"1. Ejecuta POST /direct-work/workbank/{item.id}/deliver/prepare\n2. Revisa el paquete generado\n3. Ejecuta POST /direct-work/workbank/{item.id}/deliver/approve",
            metadata={"item_status": item.status, "payout_method": getattr(item, "payout_method", "crypto")},
        )

    def _build_prepare_delivery_action(self, ctx: OneBestActionContext, item: WorkItem) -> OneBestAction:
        cash_speed = 7
        return OneBestAction(
            action_type=ActionType.PREPARE_DELIVERY,
            title=f"Preparar entrega: {item.title}",
            description=f"Generar paquete de entrega para {item.platform}. Luego solo queda aprobar.",
            why_now="El trabajo está listo. Preparar el paquete toma 15 min y deja todo listo para enviar.",
            platform=item.platform,
            work_item_id=item.id,
            estimated_human_hours=0.25,
            expected_value_usd=item.reward,
            acceptance_probability=0.9,
            cash_speed_days=cash_speed,
            urgency=Urgency.TODAY,
            prerequisites=["Generar paquete con deliver/prepare"],
            url=item.url,
            next_step_instruction=f"Ejecuta POST /direct-work/workbank/{item.id}/deliver/prepare para generar README + proposal + work.md",
            metadata={"item_status": item.status, "access_status": item.access_status},
        )

    def _build_claim_action(self, ctx: OneBestActionContext, ranked: RankedOpportunity) -> OneBestAction:
        opp = ranked.opportunity
        human_hours = opp.estimated_time_hours or 2.0
        can_fit, _remaining = self.availability.can_accommodate(human_hours, "today")

        cash_speed = int(opp.time_to_payout_days) if opp.time_to_payout_days else None

        return OneBestAction(
            action_type=ActionType.CLAIM_OPPORTUNITY,
            title=f"Reclamar: {opp.title}",
            description=f"Oportunidad de {opp.platform} ({opp.category}) — ${opp.payment:.0f} · {human_hours:.1f}h · {ranked.acceptance_probability:.0%} éxito",
            why_now=self._why_claim_now(ranked, ctx),
            platform=str(opp.platform.value) if hasattr(opp.platform, "value") else str(opp.platform),
            opportunity_id=opp.id,
            estimated_human_hours=human_hours,
            expected_value_usd=opp.payment * ranked.acceptance_probability,
            acceptance_probability=ranked.acceptance_probability,
            cash_speed_days=cash_speed,
            urgency=Urgency.TODAY if can_fit else Urgency.THIS_WEEK,
            prerequisites=self._claim_prerequisites(opp),
            url=opp.url,
            next_step_instruction=self._claim_instruction(opp),
            metadata={
                "overall_score": round(ranked.overall_recommendation_score, 2),
                "zero_barrier_score": ranked.zero_barrier_score.total if ranked.zero_barrier_score else 0,
                "payment_compat_score": getattr(ranked, "payment_compat_score", 100),
            },
        )

    def _build_onboarding_action(self, ctx: OneBestActionContext, item: WorkItem) -> OneBestAction:
        return OneBestAction(
            action_type=ActionType.COMPLETE_ONBOARDING,
            title=f"Configurar acceso: {item.platform}",
            description=f"Necesitas {item.access_requirement} para acceder a trabajos en {item.platform}",
            why_now=f"Hay {len([w for w in ctx.workbank._items.values() if w.platform == item.platform])} trabajos bloqueados esperando esta configuración",
            platform=item.platform,
            work_item_id=item.id,
            estimated_human_hours=1.0,
            expected_value_usd=0.0,
            acceptance_probability=0.0,
            cash_speed_days=None,
            urgency=Urgency.THIS_WEEK,
            prerequisites=[item.access_requirement],
            url=item.url,
            next_step_instruction=f"Completa el onboarding en {item.platform} → luego el trabajo pasa a 'ready_to_deliver'",
            metadata={"access_status": item.access_status, "blocked_reward": item.reward},
        )

    def _build_learn_action(self, ctx: OneBestActionContext, ranked: RankedOpportunity, skill: str) -> OneBestAction:
        return OneBestAction(
            action_type=ActionType.LEARN_SKILL,
            title=f"Aprender: {skill}",
            description=f"Skill gap para '{ranked.opportunity.title}' en {ranked.opportunity.platform}. Inversión: ~10-20h para desbloquear ${ranked.opportunity.payment:.0f}/semana",
            why_now=f"Esta skill desbloquea la oportunidad #1 (${ranked.opportunity.payment:.0f}) y mejora tu aceptación en {ranked.opportunity.category}",
            platform=str(ranked.opportunity.platform.value)
            if hasattr(ranked.opportunity.platform, "value")
            else str(ranked.opportunity.platform),
            opportunity_id=ranked.opportunity.id,
            estimated_human_hours=15.0,
            expected_value_usd=ranked.opportunity.payment * 0.3,
            acceptance_probability=0.5,
            cash_speed_days=None,
            urgency=Urgency.THIS_WEEK,
            prerequisites=[f"Curso/práctica de {skill}"],
            url=None,
            next_step_instruction=f"Busca tutoriales de {skill} → practica 1h/día → actualiza Profile Kit",
            metadata={"skill_gap": skill, "unlocks_platform": str(ranked.opportunity.platform)},
        )

    def _build_refresh_action(self, ctx: OneBestActionContext) -> OneBestAction:
        last_cycle = getattr(ctx.workbank, "_last_cycle", None)
        return OneBestAction(
            action_type=ActionType.RUN_WORKBANK_CYCLE,
            title="Actualizar Work Bank",
            description="Ejecutar ciclo de descubrimiento para traer nuevas oportunidades cero-barrera",
            why_now="No hay trabajos listos para entregar ni oportunidades reclamables ahora mismo. Un ciclo fresco traerá nuevas opciones.",
            platform="workbank",
            estimated_human_hours=0.1,
            expected_value_usd=0.0,
            acceptance_probability=1.0,
            cash_speed_days=None,
            urgency=Urgency.TODAY,
            prerequisites=[],
            url=None,
            next_step_instruction="Ejecuta POST /direct-work/workbank/cycle (target: 10) y revisa el brief de mañana",
            metadata={"last_cycle": last_cycle.isoformat() if last_cycle else "never"},
        )

    def _why_claim_now(self, ranked: RankedOpportunity, ctx: OneBestActionContext) -> str:
        parts = []
        if ranked.acceptance_probability >= 0.7:
            parts.append(f"Alta probabilidad de éxito ({ranked.acceptance_probability:.0%})")
        zb_score = ranked.zero_barrier_score.total if ranked.zero_barrier_score else 0
        if zb_score >= 80:
            parts.append("Barrera mínima (sin entrevista/portfolio)")
        if ranked.opportunity.payment >= 500:
            parts.append(f"Alta recompensa (${ranked.opportunity.payment:.0f})")
        if ctx.available_hours_today >= (ranked.opportunity.estimated_time_hours or 2):
            parts.append("Cabe en tu disponibilidad de hoy")
        if not parts:
            parts.append("Mejor opción disponible según tu perfil")
        return " · ".join(parts)

    def _claim_prerequisites(self, opp: Opportunity) -> list[str]:
        prereqs = []
        if opp.interview_required:
            prereqs.append("Entrevista requerida")
        if opp.portfolio_required:
            prereqs.append("Portfolio requerido")
        if opp.technical_test_required:
            prereqs.append("Test técnico requerido")
        if opp.registration_required:
            prereqs.append("Registro en plataforma")
        if not prereqs:
            prereqs.append("Sin requisitos previos (entrada directa)")
        return prereqs

    def _claim_instruction(self, opp: Opportunity) -> str:
        if opp.employment_type in (EmploymentType.BOUNTY, EmploymentType.OPEN_CALL):
            return (
                f"1. Abre {opp.url}\n2. Lee requisitos\n3. Envía solución/claim\n4. Marca como 'claimed' en Work Bank"
            )
        return f"1. Abre {opp.url}\n2. Completa aplicación\n3. Haz seguimiento en Work Bank"

    def _identify_skill_gap(self, ranked: RankedOpportunity, profile: UserProfile) -> str | None:
        user_skills = {s.lower() for s in profile.skills}
        opp = ranked.opportunity

        required_skills = []
        if opp.technology_tags:
            required_skills.extend([s.lower() for s in opp.technology_tags])
        if opp.category == OpportunityCategory.SECURITY_RESEARCH and "burp" not in user_skills:
            required_skills.append("burp")
        if opp.category == OpportunityCategory.API_DEVELOPMENT and "postman" not in user_skills:
            required_skills.append("postman")
        if opp.category == OpportunityCategory.SMART_CONTRACTS and "solidity" not in user_skills:
            required_skills.append("solidity")

        for skill in required_skills:
            if skill not in user_skills:
                return skill
        return None


# ── Convenience functions ──

_one_best_action_engine: OneBestActionEngine | None = None


def get_one_best_action_engine() -> OneBestActionEngine:
    global _one_best_action_engine
    if _one_best_action_engine is None:
        _one_best_action_engine = OneBestActionEngine()
    return _one_best_action_engine


def get_one_best_action(profile: UserProfile | None = None) -> OneBestAction:
    """Get the single best action for the user right now."""
    return get_one_best_action_engine().get_one_best_action(profile)
