"""Intelligent Recommender — ranks opportunities by expected value, acceptance probability, and compatibility."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cores.direct_work_engine.models import (
    EmploymentType,
    ExperienceLevel,
    Opportunity,
    RankedOpportunity,
    UserProfile,
)
from cores.direct_work_engine.scoring import ZeroBarrierScorer

logger = logging.getLogger("ownex.direct_work_engine.recommendation")

# How each employment type maps to the "world" the opportunity lives in.
# Outcome-based worlds pay for the result (bounties, microtasks, prizes) and
# skip the classic selection process; the others keep a hiring funnel.
EMPLOYMENT_TYPE_MODEL: dict[EmploymentType, str] = {
    EmploymentType.FULL_TIME: "classic_employment",
    EmploymentType.PART_TIME: "classic_employment",
    EmploymentType.CONTRACT: "freelance",
    EmploymentType.FREELANCE: "freelance",
    EmploymentType.PROJECT: "freelance",
    EmploymentType.RETAINER: "freelance",
    EmploymentType.BOUNTY: "outcome_bounty",
    EmploymentType.OPEN_CALL: "outcome_bounty",
    EmploymentType.MICROTASK: "ai_task",
    EmploymentType.CHALLENGE: "competition",
    EmploymentType.PRIZE: "competition",
    EmploymentType.ROLLING: "rolling",
}

_OUTCOME_BASED_MODELS = frozenset({"outcome_bounty", "ai_task", "competition"})


def opportunity_model(employment_type: EmploymentType) -> str:
    """Classify an opportunity into its market model (see EMPLOYMENT_TYPE_MODEL)."""
    return EMPLOYMENT_TYPE_MODEL.get(employment_type, "freelance")


def is_outcome_based(employment_type: EmploymentType) -> bool:
    """True when the opportunity pays for the delivered result, not for the person."""
    return opportunity_model(employment_type) in _OUTCOME_BASED_MODELS


@dataclass(slots=True)
class RecommenderConfig:
    """Configuration for the recommendation engine."""

    # Weights for overall recommendation score
    weight_zero_barrier: float = 0.25
    weight_expected_value: float = 0.25
    weight_acceptance_probability: float = 0.20
    weight_compatibility: float = 0.15
    weight_speed: float = 0.10
    weight_reputation: float = 0.05

    # Thresholds
    min_zero_barrier_score: float = 30.0
    min_expected_value: float = 10.0
    min_acceptance_probability: float = 0.1
    min_compatibility: float = 0.3
    enforce_acceptance_floor: bool = False

    # Diversity
    max_per_platform: int = 3
    max_per_category: int = 5
    enforce_diversity: bool = True

    def validate(self) -> bool:
        total = (
            self.weight_zero_barrier
            + self.weight_expected_value
            + self.weight_acceptance_probability
            + self.weight_compatibility
            + self.weight_speed
            + self.weight_reputation
        )
        return abs(total - 1.0) < 0.001


DEFAULT_RECOMMENDER_CONFIG = RecommenderConfig()

# Fast Income Mode — Reward x Probability x Speed. Optimizes for short
# time-to-payment, high acceptance and reasonable reward over pure reward size.
_FAST_INCOME_CONFIG = RecommenderConfig(
    weight_expected_value=0.30,
    weight_acceptance_probability=0.25,
    weight_speed=0.25,
    weight_zero_barrier=0.10,
    weight_compatibility=0.05,
    weight_reputation=0.05,
    min_expected_value=0.0,
    min_zero_barrier_score=0.0,
)

FAST_INCOME_RECOMMENDER_CONFIG = _FAST_INCOME_CONFIG

# Max Success Mode — Success Maximizer. Weights acceptance probability above
# everything else and enforces a hard floor so low-success work never surfaces.
# Only recommends work the profile's real outcome history says is likely to win.
_MAX_SUCCESS_CONFIG = RecommenderConfig(
    weight_acceptance_probability=0.40,
    weight_zero_barrier=0.25,
    weight_expected_value=0.15,
    weight_compatibility=0.10,
    weight_reputation=0.10,
    weight_speed=0.0,
    min_zero_barrier_score=60.0,
    min_expected_value=20.0,
    min_acceptance_probability=0.5,
    enforce_acceptance_floor=True,
)

MAX_SUCCESS_RECOMMENDER_CONFIG = _MAX_SUCCESS_CONFIG

# Max Income Mode — maximize expected WEEKLY income across all work shapes
# (hourly streams, per-result bounties, fillers) rather than nominal rate.
# EV leads; acceptance and speed keep it realistic; barrier still matters
# because unentered platforms earn nothing this week.
_MAX_INCOME_CONFIG = RecommenderConfig(
    weight_expected_value=0.35,
    weight_acceptance_probability=0.25,
    weight_speed=0.15,
    weight_zero_barrier=0.15,
    weight_compatibility=0.05,
    weight_reputation=0.05,
)

MAX_INCOME_RECOMMENDER_CONFIG = _MAX_INCOME_CONFIG


def filter_zero_experience(opportunities: list[Opportunity]) -> list[Opportunity]:
    """Keep only opportunities doable WITHOUT prior experience in the category.

    Capability gates (assessment/training/test) are explicitly ALLOWED here —
    "Zero Experience does not mean Zero Barrier". Only a hard experience
    requirement (REQUIRED, incl. legacy MID/SENIOR depth) excludes.
    """
    return [o for o in opportunities if o.is_zero_experience]


def filter_zero_barrier_strict(opportunities: list[Opportunity]) -> list[Opportunity]:
    """Strict zero-barrier: nothing at all between you and paid work.

    Excludes any application gate: assessment, training, test, interview,
    portfolio, approval/invitation. Use when the user wants to start
    earning immediately even if it pays less.
    """
    return [o for o in opportunities if o.is_zero_barrier]


# PaymentMethod (DWE) -> method accepted by the PaymentCompatibilityEngine network.
# Methods without a curated account in the network stay unevaluated (neutral).
_PAYMENT_METHOD_MAP: dict[str, str] = {
    "paypal": "paypal",
    "bank_wire": "wire",
    "crypto": "crypto",
    "stablecoin": "crypto",
}


class IntelligentRecommender:
    """Ranks and recommends opportunities based on multiple factors.

    Prioritizes:
    1. Highest expected value
    2. Highest acceptance probability
    3. Lowest barrier (highest zero barrier score)
    4. Highest user compatibility
    5. Fastest payment
    6. Highest reputation
    """

    def __init__(
        self,
        config: RecommenderConfig | None = None,
        scorer: ZeroBarrierScorer | None = None,
    ):
        self.config = config or DEFAULT_RECOMMENDER_CONFIG
        self.scorer = scorer or ZeroBarrierScorer()
        if not self.config.validate():
            raise ValueError("Recommender config weights must sum to 1.0")

    def recommend(
        self,
        opportunities: list[Opportunity],
        profile: UserProfile,
        limit: int = 10,
        mode: str = "balanced",
        zero_experience_only: bool = False,
        zero_barrier_strict: bool = False,
    ) -> list[RankedOpportunity]:
        """Generate ranked recommendations for a user profile.

        ``mode="fast_income"`` swaps the config to the Fast Income preset
        (Reward x Probability x Speed): it optimizes for short time-to-payment,
        high acceptance probability and reasonable reward over pure reward size.

        ``mode="max_success"`` swaps the config to the Success Maximizer preset:
        acceptance probability is weighted highest (0.40) and a hard floor is
        enforced so low-success work never surfaces.

        ``mode="max_income"`` maximizes expected weekly income across ALL work
        shapes (hourly streams, bounties, fillers) — not just nominal rate.

        Keyword filters (independent of mode):

        ``zero_experience_only`` drops opportunities requiring prior experience
        in the category, but KEEPS capability-assessed entries (assessment
        != experience). ``zero_barrier_strict`` keeps only direct-entry work:
        no assessment/interview/portfolio/approval of any kind.

        Any other mode (or no mode) restores the balanced preset, so a previous
        preset call never leaks into later ones.
        """
        if mode == "fast_income":
            self.config = _FAST_INCOME_CONFIG
        elif mode == "max_success":
            self.config = _MAX_SUCCESS_CONFIG
        elif mode == "max_income":
            self.config = _MAX_INCOME_CONFIG
        else:
            self.config = DEFAULT_RECOMMENDER_CONFIG
        if zero_experience_only:
            opportunities = filter_zero_experience(opportunities)
        if zero_barrier_strict:
            opportunities = filter_zero_barrier_strict(opportunities)
        return self.__recommend(opportunities, profile, limit=limit)

    def filter_by_success_floor(
        self,
        opportunities: list[Opportunity],
        profile: UserProfile,
    ) -> list[Opportunity]:
        """Keep only opportunities whose real acceptance probability meets the floor.

        Uses the same ``_calculate_acceptance_probability`` path as ``__recommend``
        (profile outcome history, never invented), so the floor is measured on
        actual success data. Returns only the opportunities that pass.
        """
        if not self.config.enforce_acceptance_floor:
            return opportunities
        kept: list[Opportunity] = []
        for opp in opportunities:
            if opp.zero_barrier_score is None:
                opp.zero_barrier_score = self.scorer.score(opp)
            ranked = RankedOpportunity(opportunity=opp, zero_barrier_score=opp.zero_barrier_score)
            if self._calculate_acceptance_probability(ranked, profile) >= self.config.min_acceptance_probability:
                kept.append(opp)
        return kept

    def __recommend(
        self,
        opportunities: list[Opportunity],
        profile: UserProfile,
        limit: int = 10,
    ) -> list[RankedOpportunity]:
        if not opportunities:
            return []

        # 0. Apply profile preferences as hard filters (caller-supplied profile
        #    governs what the user is actually looking for): drop excluded
        #    categories and rewards below the minimum the user will take on.
        opportunities = self._apply_profile_filter(opportunities, profile)

        # 1. Score all opportunities with zero barrier score
        scored_opps = self._score_opportunities(opportunities)

        # 1b. Evaluate payment compatibility (can OWNEX collect the payout?)
        for opp in scored_opps:
            self._apply_payment_compatibility(opp)

        # 2. Calculate acceptance probability per opportunity
        for opp in scored_opps:
            opp.acceptance_probability = self._calculate_acceptance_probability(opp, profile)

        # 2b. Hard success floor (Success Maximizer): drop any opportunity whose
        #     real acceptance probability is below the configured floor.
        if self.config.enforce_acceptance_floor:
            scored_opps = [
                opp for opp in scored_opps if opp.acceptance_probability >= self.config.min_acceptance_probability
            ]
            if not scored_opps:
                return []

        # 3. Calculate compatibility score
        for opp in scored_opps:
            opp.compatibility_score = self._calculate_compatibility(opp, profile)

        # 4. Calculate speed score (inverse of time to payment)
        for opp in scored_opps:
            opp.speed_score = self._calculate_speed_score(opp)

        # 5. Calculate reputation score
        for opp in scored_opps:
            opp.reputation_score = self._calculate_reputation_score(opp)

        # 6. Calculate risk score
        for opp in scored_opps:
            opp.risk_score = self._calculate_risk_score(opp)

        # 7. Calculate expected value
        for opp in scored_opps:
            opp.expected_value = self._calculate_expected_value(opp)

        # 7b. Calculate HTROI (Human-Time Adjusted ROI) — Fase C
        for opp in scored_opps:
            opp.htroi = self._calculate_htroi(opp)

        # 8. Calculate overall recommendation score
        for opp in scored_opps:
            opp.overall_recommendation_score = self._calculate_overall_score(opp)

        # 9. Generate strategy for top opportunities
        for ranked_opp in scored_opps:
            ranked_opp.strategy = self._generate_strategy(ranked_opp, profile)
            ranked_opp.recommendation_reasoning = self._generate_reasoning(ranked_opp, profile)

        # 10. Sort by overall score (descending)
        ranked = sorted(scored_opps, key=lambda o: o.overall_recommendation_score, reverse=True)

        # 11. Apply diversity constraints
        if self.config.enforce_diversity:
            ranked = self._apply_diversity(ranked)

        # 12. Assign ranks and limit
        for i, opp in enumerate(ranked[:limit]):
            opp.rank = i + 1

        return ranked[:limit]

    def _apply_profile_filter(self, opportunities: list[Opportunity], profile: UserProfile) -> list[Opportunity]:
        """Apply profile preferences as hard filters before scoring.

        Excluded categories never surface. Rewards below the user's floor are
        dropped. When no preference is set the profile is a no-op, so legacy
        callers keep their exact behavior.
        """
        excluded = {c.value if hasattr(c, "value") else str(c) for c in profile.excluded_categories}
        if not excluded and profile.min_payment <= 0.0:
            return opportunities

        filtered: list[Opportunity] = []
        for opp in opportunities:
            if opp.category.value in excluded:
                continue
            if profile.min_payment > 0.0 and opp.payment < profile.min_payment:
                continue
            filtered.append(opp)
        return filtered

    def _score_opportunities(self, opportunities: list[Opportunity]) -> list[RankedOpportunity]:
        """Score opportunities and convert to RankedOpportunity."""
        ranked: list[RankedOpportunity] = []

        for opp in opportunities:
            # Ensure zero barrier score exists
            if opp.zero_barrier_score is None:
                opp.zero_barrier_score = self.scorer.score(opp)

            # Filter by minimum threshold
            if opp.zero_barrier_score.total < self.config.min_zero_barrier_score:
                continue

            ranked.append(
                RankedOpportunity(
                    opportunity=opp,
                    zero_barrier_score=opp.zero_barrier_score,
                )
            )

        return ranked

    def _apply_payment_compatibility(self, ranked: RankedOpportunity) -> None:
        """Evaluate whether OWNEX can actually collect the payout (0-100).

        Uses the deterministic PaymentCompatibilityEngine (cores.payment_compat)
        with lazy import: if the engine is unavailable the score stays neutral
        (100.0) so legacy callers keep their exact behavior.
        """
        opp = ranked.opportunity
        try:
            from cores.payment_compat.engine import PaymentRequirement, get_payment_engine

            method = _PAYMENT_METHOD_MAP.get(opp.payment_method.value)
            if method is None:
                ranked.payment_compat_notes.append(
                    f"Método {opp.payment_method.value}: sin cuenta curada en la red de pagos (no evaluado)."
                )
                return
            verdict = get_payment_engine().evaluate(
                PaymentRequirement(
                    method=method,
                    currency="USDC" if method == "crypto" else "USD",
                    region="global",
                    amount=opp.payment,
                )
            )
            ranked.payment_compat_score = verdict.score
            if verdict.compatible:
                ranked.payment_compat_notes.append("Pago cobrable con las cuentas configuradas de OWNEX.")
            elif verdict.matches:
                ranked.payment_compat_notes.append(
                    f"Pago parcialmente viable ({verdict.score:.0f}/100): " + "; ".join(verdict.missing[:2])
                )
            else:
                ranked.payment_compat_notes.append(
                    f"Pago NO cobrable ({verdict.score:.0f}/100): "
                    + "; ".join(verdict.missing[:2] or verdict.honest_notes[:1])
                )
        except Exception:
            ranked.payment_compat_notes.append("Evaluación de pago no disponible (motor no responde).")

    def _calculate_acceptance_probability(self, ranked: RankedOpportunity, profile: UserProfile) -> float:
        """Estimate probability of acceptance based on profile match."""
        opp = ranked.opportunity
        zb = ranked.zero_barrier_score

        if not zb:
            return 0.1

        # Base probability from zero barrier score
        base_prob = zb.total / 100.0

        # Adjust for experience match
        exp_match = self._experience_match(opp, profile)
        base_prob *= 0.5 + 0.5 * exp_match

        # Adjust for skill match
        skill_match = self._skill_match(opp, profile)
        base_prob *= 0.6 + 0.4 * skill_match

        # Adjust for platform history
        platform_hist = profile.platform_success_rates.get(opp.platform.value, 0.5)
        base_prob *= 0.7 + 0.3 * platform_hist

        # Adjust for category history
        cat_hist = profile.category_success_rates.get(opp.category.value, 0.5)
        base_prob *= 0.8 + 0.2 * cat_hist

        return max(0.01, min(0.95, base_prob))

    def _calculate_compatibility(self, ranked: RankedOpportunity, profile: UserProfile) -> float:
        """Calculate user-opportunity compatibility score (0-1)."""
        opp = ranked.opportunity
        score = 0.0
        factors = 0

        # Skill match
        skill_match = self._skill_match(opp, profile)
        score += skill_match
        factors += 1

        # Experience level match
        exp_match = self._experience_match(opp, profile)
        score += exp_match
        factors += 1

        # Language match
        lang_match = 1.0 if opp.language_required.lower() in [lang.lower() for lang in profile.languages] else 0.3
        score += lang_match
        factors += 1

        # Remote preference
        remote_match = 1.0 if (not profile.remote_only or opp.remote) else 0.0
        score += remote_match
        factors += 1

        # Payment method preference
        payment_match = 1.0 if opp.payment_method in profile.preferred_payment_methods else 0.5
        score += payment_match
        factors += 1

        # Currency preference
        currency_match = 1.0 if opp.currency in profile.preferred_currencies else 0.5
        score += currency_match
        factors += 1

        # Employment type preference
        emp_match = 1.0 if opp.employment_type in profile.preferred_employment_types else 0.5
        score += emp_match
        factors += 1

        # Async preference
        async_match = 1.0 if (not profile.async_preferred or opp.asynchronous) else 0.5
        score += async_match
        factors += 1

        # AI tools preference
        ai_match = 1.0 if (profile.accepts_ai_tools or not opp.accepts_ai_tools) else 0.5
        score += ai_match
        factors += 1

        return score / factors if factors > 0 else 0.5

    def _experience_match(self, opp: Opportunity, profile: UserProfile) -> float:
        """Match opportunity experience requirement to user level."""
        opp_exp = opp.experience_required
        user_exp = profile.experience_level

        # Map to numeric for comparison
        exp_values = {
            ExperienceLevel.NONE: 0,
            ExperienceLevel.JUNIOR: 1,
            ExperienceLevel.MID: 2,
            ExperienceLevel.SENIOR: 3,
        }

        opp_val = exp_values.get(opp_exp, 1)
        user_val = exp_values.get(user_exp, 0)

        if user_val >= opp_val:
            return 1.0  # User meets or exceeds requirement
        elif user_val == opp_val - 1:
            return 0.7  # One level below
        else:
            return 0.3  # Significantly below

    def _skill_match(self, opp: Opportunity, profile: UserProfile) -> float:
        """Match opportunity technology tags to user skills."""
        if not opp.technology_tags:
            return 0.5

        user_skills_lower = {s.lower() for s in profile.skills}
        matches = sum(1 for tag in opp.technology_tags if tag.lower() in user_skills_lower)

        if matches == 0:
            return 0.2
        elif matches >= len(opp.technology_tags):
            return 1.0
        else:
            return 0.4 + 0.6 * (matches / len(opp.technology_tags))

    def _calculate_speed_score(self, ranked: RankedOpportunity) -> float:
        """Calculate speed score (higher = faster payment)."""
        opp = ranked.opportunity
        if opp.time_to_payout_days is None:
            return 0.5
        if opp.time_to_payout_days <= 7:
            return 1.0
        elif opp.time_to_payout_days <= 14:
            return 0.8
        elif opp.time_to_payout_days <= 30:
            return 0.6
        elif opp.time_to_payout_days <= 60:
            return 0.4
        else:
            return 0.2

    def _calculate_reputation_score(self, ranked: RankedOpportunity) -> float:
        """Calculate platform/company reputation score."""
        opp = ranked.opportunity
        return (opp.reputation + opp.payment_proven * 0.5 + opp.stability) / 2.5

    def _calculate_risk_score(self, ranked: RankedOpportunity) -> float:
        """Calculate risk score (higher = more risky)."""
        opp = ranked.opportunity
        return opp.risk

    def _calculate_expected_value(self, ranked: RankedOpportunity) -> float:
        """Money expectation via the economics SSOT (FASE 3, P0-3).

        Numeric behavior preserved for legacy inputs; task availability is
        UNKNOWN until adapters provide a live signal (never assumed).
        Calibration (Fase D): platforms with measured over/under-promise
        history get their EV scaled by the recorded factor — neutral 1.0
        until MIN_SAMPLES resolved outcomes exist.
        """
        from cores.direct_work_engine.economics import compute_expected_value
        from cores.direct_work_engine.models import PAYMENT_RELIABILITY

        opp = ranked.opportunity
        reliability = PAYMENT_RELIABILITY.get(opp.payment_method, 0.5)

        ev = compute_expected_value(
            payment=opp.payment,
            acceptance_probability=ranked.acceptance_probability,
            payment_reliability=reliability,
        ).ev_usd

        try:
            from cores.direct_work_engine.calibration import get_calibration_engine

            platform_key = str(getattr(opp.platform, "value", opp.platform))
            factor, _conf = get_calibration_engine().platform_factor(platform_key)
            ev = round(ev * factor, 2)
        except Exception:  # calibration is an enhancement, never a breaker
            pass

        return ev

    def _calculate_htroi(self, ranked: RankedOpportunity) -> HumanTimeAdjustedROI | None:
        """Compute Human-Time Adjusted ROI for an opportunity (Fase C, Income Multiplier).

        Uses the economics SSOT: expected_income / human_hours, with confidence
        adjustment and optional automation compression. Returns None when
        human_hours is unknown or zero (honest signaling).
        """
        from cores.direct_work_engine.economics import compute_htroi

        opp = ranked.opportunity

        # Determine income base: hourly stream or one-shot payment
        hourly_rate = opp.hourly_rate_usd if opp.hourly_rate_usd and opp.hourly_rate_usd > 0 else None
        human_hours = opp.estimated_time_hours if opp.estimated_time_hours and opp.estimated_time_hours > 0 else None

        # Confidence = acceptance probability * payment compatibility
        confidence = ranked.acceptance_probability * (ranked.payment_compat_score / 100.0)

        # Automation hours from execution planner if available
        automation_hours = getattr(opp, "automation_hours", None)

        try:
            return compute_htroi(
                expected_income_usd=opp.payment,
                human_hours=human_hours or 0,
                confidence=confidence,
                automation_hours=automation_hours,
            )
        except Exception:
            return None

    def _calculate_overall_score(self, ranked: RankedOpportunity) -> float:
        """Calculate weighted overall recommendation score."""
        c = self.config
        zb = ranked.zero_barrier_score

        zero_barrier_norm = zb.total / 100.0 if zb else 0.0
        expected_value_norm = min(1.0, ranked.expected_value / 10000.0)  # Normalize to $10k
        acceptance_norm = ranked.acceptance_probability
        compatibility_norm = ranked.compatibility_score
        speed_norm = ranked.speed_score
        reputation_norm = ranked.reputation_score

        score = (
            c.weight_zero_barrier * zero_barrier_norm
            + c.weight_expected_value * expected_value_norm
            + c.weight_acceptance_probability * acceptance_norm
            + c.weight_compatibility * compatibility_norm
            + c.weight_speed * speed_norm
            + c.weight_reputation * reputation_norm
        )

        # Risk penalty
        score *= 1.0 - 0.3 * ranked.risk_score

        # Payment compatibility factor: cannot collect -> recommendation drops
        payment_factor = ranked.payment_compat_score / 100.0 if ranked.payment_compat_score > 0 else 0.3
        score *= payment_factor

        return round(score * 100, 1)  # 0-100 scale

    def _generate_strategy(self, ranked: RankedOpportunity, profile: UserProfile) -> str:
        """Generate personalized action strategy."""
        opp = ranked.opportunity
        zb = ranked.zero_barrier_score

        steps: list[str] = []

        if zb and zb.total < 50:
            steps.append("⚠️ High barrier — prepare thoroughly before applying")

        if opp.portfolio_required and not profile.has_portfolio:
            steps.append("📁 Build minimal portfolio first (1-2 relevant projects)")

        if opp.technical_test_required:
            steps.append("🧪 Prepare for technical test — review common patterns for this category")

        if opp.interview_required:
            steps.append("🎤 Practice interview — focus on remote work async communication")

        if opp.registration_required:
            steps.append("📝 Register on platform — verify payment method setup")

        # Add category-specific advice
        if opp.category.value == "game_development":
            steps.append("🎮 Highlight game programming projects (not art) in application")

        if opp.category.value in ["bug_bounty", "security_research"]:
            steps.append("🔒 Emphasize responsible disclosure history and report quality")

        if is_outcome_based(opp.employment_type):
            steps.append("🎯 Outcome-based: deliver the result, no selection process")

        if not steps:
            steps.append("✅ Low barrier — apply directly with tailored cover letter")

        return " → ".join(steps)

    def _generate_reasoning(self, ranked: RankedOpportunity, profile: UserProfile) -> list[str]:
        """Generate human-readable reasoning for recommendation."""
        zb = ranked.zero_barrier_score
        reasons: list[str] = []

        reasons.append(f"Overall Score: {ranked.overall_recommendation_score}/100")
        reasons.append(f"Expected Value: ${ranked.expected_value:.0f}")
        reasons.append(f"Acceptance Probability: {ranked.acceptance_probability:.0%}")
        reasons.append(f"Compatibility: {ranked.compatibility_score:.0%}")
        reasons.append(f"Zero Barrier: {zb.total if zb else 'N/A'}/100 ({zb.barrier_label if zb else 'unknown'})")
        reasons.append(f"Speed Score: {ranked.speed_score:.0%}")
        reasons.append(f"Reputation: {ranked.reputation_score:.0%}")
        reasons.append(f"Risk: {ranked.risk_score:.0%}")
        reasons.append(f"Model: {opportunity_model(ranked.opportunity.employment_type)}")
        if ranked.payment_compat_notes:
            reasons.append("💳 " + ranked.payment_compat_notes[0])

        if zb:
            if zb.enablers:
                reasons.append("✅ " + "; ".join(zb.enablers[:3]))
            if zb.blockers:
                reasons.append("⚠️ " + "; ".join(zb.blockers[:3]))

        return reasons

    def _apply_diversity(self, ranked: list[RankedOpportunity]) -> list[RankedOpportunity]:
        """Apply diversity constraints to avoid over-concentration."""
        platform_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        diversified: list[RankedOpportunity] = []

        for opp in ranked:
            platform = opp.opportunity.platform.value
            category = opp.opportunity.category.value

            platform_count = platform_counts.get(platform, 0)
            category_count = category_counts.get(category, 0)

            if platform_count >= self.config.max_per_platform:
                continue
            if category_count >= self.config.max_per_category:
                continue

            diversified.append(opp)
            platform_counts[platform] = platform_count + 1
            category_counts[category] = category_count + 1

        return diversified


def recommend_opportunities(
    opportunities: list[Opportunity],
    profile: UserProfile,
    limit: int = 10,
    config: RecommenderConfig | None = None,
) -> list[RankedOpportunity]:
    """Convenience function for recommendations."""
    recommender = IntelligentRecommender(config=config)
    return recommender.recommend(opportunities, profile, limit)
