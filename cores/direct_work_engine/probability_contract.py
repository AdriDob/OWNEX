"""Universal Probability Contract — OWNEX 100/100.

Single source of truth for all probability types, evidence labels,
estimates, and category funnels across ALL economic categories.

This is the SINGLE SOURCE OF TRUTH for probability semantics.
Every engine, every UI, every test must import from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Optional

# ────────────────────────────────────────────────────────────────
# Probability Types — Universal vocabulary for ALL categories
# ────────────────────────────────────────────────────────────────


class ProbabilityType(StrEnum):
    """Universal probability types across ALL economic categories.

    Each type represents a distinct, well-defined event in a category's funnel.
    The name MUST be stable — used as keys in storage, APIs, and contracts.
    """

    # ─── Bug Bounty ───
    P_VALID = "p_valid"  # Technical validity (real, reproducible, in scope)
    P_UNIQUE = "p_unique"  # Uniqueness (not duplicate, first to report)
    P_ACCEPT = "p_accept"  # Program acceptance (if valid+unique, will platform accept?)
    P_REWARD = "p_reward"  # Rewardability (if accepted, will it pay?)
    P_PAYMENT = "p_payment"  # Actual payout received

    # ─── Dev Bounty ───
    P_ELIGIBLE = "p_eligible"  # Meets requirements
    P_QUALIFIED = "p_qualified"  # Passes screening
    P_SELECTED = "p_selected"  # Chosen for task
    P_COMPLETION = "p_completion"  # Delivers working solution
    # Reuses: P_ACCEPT, P_PAYMENT

    # ─── AI Training / Data Annotation ───
    P_TASK_ASSIGNED = "p_task_assigned"  # Gets task assigned
    # Reuses: P_ELIGIBLE, P_QUALIFIED, P_COMPLETION, P_ACCEPT, P_PAYMENT

    # ─── Client Work ───
    P_LEAD = "p_lead"  # Lead is real
    P_REPLY = "p_reply"  # Client replies
    P_PROPOSAL = "p_proposal"  # Proposal accepted
    P_DELIVERY = "p_delivery"  # Delivers on time
    # Reuses: P_ELIGIBLE, P_QUALIFIED, P_ACCEPT, P_PAYMENT

    # ─── Employment ───
    P_APPLICATION = "p_application"  # Application submitted
    P_RESPONSE = "p_response"  # Employer responds
    P_INTERVIEW = "p_interview"  # Gets interview
    P_OFFER = "p_offer"  # Receives offer
    P_RETENTION = "p_retention"  # Stays beyond probation

    # ─── Investment ───
    P_THESIS = "p_thesis"  # Investment thesis holds
    P_EXECUTION = "p_execution"  # Can execute thesis
    P_RETURN = "p_return"  # Achieves target return
    P_RISK = "p_risk"  # Risk within tolerance
    P_DRAWDOWN = "p_drawdown"  # Drawdown within tolerance

    # ─── Cross-Category Reuse ───
    # P_ELIGIBLE, P_QUALIFIED, P_ACCEPT, P_PAYMENT, P_COMPLETION
    # are shared across categories — defined once, used everywhere.

    # ─── Category-Agnostic ───
    P_SUCCESS = "p_success"  # Generic success probability
    P_FAILURE = "p_failure"  # Generic failure probability


# ────────────────────────────────────────────────────────────────
# Evidence Labels — Honest about what we know
# ────────────────────────────────────────────────────────────────


class EvidenceLabel(StrEnum):
    """Evidence quality label — honest about epistemic state.

    NEVER inflate. If evidence is thin, label it thin.
    Values ordered lexicographically to match declaration order.
    """

    NO_EVIDENCE = "0_no_evidence"
    THIN_EVIDENCE = "1_thin_evidence"
    SUFFICIENT_EVIDENCE = "2_sufficient_evidence"
    HIGH_EVIDENCE = "3_high_evidence"


# ────────────────────────────────────────────────────────────────
# Probability Estimate — Single probability with full metadata
# ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ProbabilityEstimate:
    """Single probability estimate with FULL metadata.

    NEVER create a probability without this metadata.
    If you don't have the metadata, you don't have a probability.
    """

    probability_type: ProbabilityType
    estimate: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0 (Wilson lower bound)
    lower_bound: float  # Wilson lower bound at 95%
    upper_bound: float  # Wilson upper bound at 95%
    evidence_label: EvidenceLabel
    effective_sample_size: float
    raw_sample_size: int
    prior_type: str  # "external" | "personal" | "calibrated"
    prior_value: float  # The prior value used
    source: str  # "external_prior" | "personal_evidence" | "calibrated"
    segment: str  # platform|category|subcategory|task_type|skill|difficulty|surface
    last_updated: str  # ISO timestamp
    evidence_quality: float  # 0.0-1.0 composite

    @property
    def is_high_confidence_90(self) -> bool:
        """True iff lower_bound >= 0.90 AND evidence is sufficient."""
        return self.lower_bound >= 0.90 and self.evidence_label in (
            EvidenceLabel.SUFFICIENT_EVIDENCE,
            EvidenceLabel.HIGH_EVIDENCE,
        )

    @property
    def is_insufficient_for_high_confidence(self) -> bool:
        """True if we cannot legitimately claim HIGH_CONFIDENCE_90."""
        return (
            self.evidence_label in (EvidenceLabel.NO_EVIDENCE, EvidenceLabel.THIN_EVIDENCE) or self.lower_bound < 0.90
        )


# ────────────────────────────────────────────────────────────────
# Category Funnel — Declarative funnel per category
# ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CategoryFunnel:
    """Declarative funnel definition for a category.

    This REPLACES hardcoded funnel logic in recommendation.py and elsewhere.
    Every category MUST declare its funnel here.
    """

    category: str  # e.g., "bug_bounty", "dev_bounty"
    stages: tuple[str, ...]  # Ordered stage names
    probability_types: tuple[ProbabilityType, ...]  # One per transition
    outcome_mapping: dict[str, str]  # outcome string -> terminal state
    description: str = ""  # Human-readable description

    def __post_init__(self):
        if len(self.stages) != len(self.probability_types) + 1:
            raise ValueError(
                f"Funnel {self.category}: stages ({len(self.stages)}) "
                f"must be probability_types + 1 ({len(self.probability_types)} + 1)"
            )

    def stage_for_probability(self, prob_type: ProbabilityType) -> str:
        """Get the target stage for a probability type."""
        try:
            idx = self.probability_types.index(prob_type)
            return self.stages[idx + 1]
        except ValueError:
            raise ValueError(f"{prob_type} not in funnel {self.category}")


# ────────────────────────────────────────────────────────────────
# Category Funnel Registry — Single source of truth for funnels
# ────────────────────────────────────────────────────────────────

_CATEGORY_FUNNELS: dict[str, CategoryFunnel] = {}


def register_funnel(funnel: CategoryFunnel) -> None:
    """Register a category funnel. Call once at module import."""
    if funnel.category in _CATEGORY_FUNNELS:
        raise ValueError(f"Funnel for {funnel.category} already registered")
    _CATEGORY_FUNNELS[funnel.category] = funnel


def get_funnel(category: str) -> CategoryFunnel:
    """Get funnel for category. Raises if not registered."""
    try:
        return _CATEGORY_FUNNELS[category]
    except KeyError:
        raise KeyError(f"No funnel registered for category: {category}")


def get_all_funnels() -> dict[str, CategoryFunnel]:
    """Get all registered funnels."""
    return dict(_CATEGORY_FUNNELS)


def get_categories_with_funnels() -> list[str]:
    """List all categories with registered funnels."""
    return sorted(_CATEGORY_FUNNELS.keys())


# ────────────────────────────────────────────────────────────────
# Funnel Declarations — The canonical funnels for OWNEX
# ────────────────────────────────────────────────────────────────

# Bug Bounty: ELIGIBLE → VALID → UNIQUE → ACCEPT → REWARD → PAID
register_funnel(
    CategoryFunnel(
        category="bug_bounty",
        stages=("ELIGIBLE", "VALID", "UNIQUE", "ACCEPT", "REWARD", "PAID"),
        probability_types=(
            ProbabilityType.P_ELIGIBLE,
            ProbabilityType.P_VALID,
            ProbabilityType.P_UNIQUE,
            ProbabilityType.P_ACCEPT,
            ProbabilityType.P_REWARD,
        ),
        outcome_mapping={
            "accepted": "PAID",
            "rejected": "REJECTED",
            "duplicate": "DUPLICATE",
            "informative": "INFORMATIVE",
        },
        description="Bug bounty: scope → validity → uniqueness → program acceptance → reward → payout",
    )
)

# Dev Bounty: DISCOVERED → ELIGIBLE → QUALIFIED → SELECTED → ACCEPT → PAID
register_funnel(
    CategoryFunnel(
        category="dev_bounty",
        stages=("DISCOVERED", "ELIGIBLE", "QUALIFIED", "SELECTED", "ACCEPT", "PAID"),
        probability_types=(
            ProbabilityType.P_ELIGIBLE,
            ProbabilityType.P_QUALIFIED,
            ProbabilityType.P_SELECTED,
            ProbabilityType.P_ACCEPT,
            ProbabilityType.P_PAYMENT,
        ),
        outcome_mapping={
            "submitted": "SUBMITTED",
            "accepted": "PAID",
            "rejected": "REJECTED",
            "error": "FAILED",
        },
        description="Dev bounty: discovery → eligibility → qualification → selection → PR acceptance → payout",
    )
)

# AI Training / Data Annotation
register_funnel(
    CategoryFunnel(
        category="ai_training",
        stages=("DISCOVERED", "ELIGIBLE", "QUALIFIED", "TASK_ASSIGNED", "COMPLETION", "ACCEPT", "PAID"),
        probability_types=(
            ProbabilityType.P_ELIGIBLE,
            ProbabilityType.P_QUALIFIED,
            ProbabilityType.P_TASK_ASSIGNED,
            ProbabilityType.P_COMPLETION,
            ProbabilityType.P_ACCEPT,
            ProbabilityType.P_PAYMENT,
        ),
        outcome_mapping={
            "accepted": "PAID",
            "rejected": "REJECTED",
            "expired": "EXPIRED",
        },
        description="AI training: eligibility → qualification → task assignment → completion → platform acceptance → payment",
    )
)

# Client Work / Freelance
register_funnel(
    CategoryFunnel(
        category="client_work",
        stages=("DISCOVERED", "LEAD", "REPLY", "QUALIFIED", "PROPOSAL", "ACCEPT", "DELIVERY", "PAID"),
        probability_types=(
            ProbabilityType.P_LEAD,
            ProbabilityType.P_REPLY,
            ProbabilityType.P_QUALIFIED,
            ProbabilityType.P_PROPOSAL,
            ProbabilityType.P_ACCEPT,
            ProbabilityType.P_DELIVERY,
            ProbabilityType.P_PAYMENT,
        ),
        outcome_mapping={
            "accepted": "PAID",
            "rejected": "REJECTED",
            "cancelled": "CANCELLED",
        },
        description="Client work: discovery → lead → reply → qualification → proposal → acceptance → delivery → payment",
    )
)

# Employment
register_funnel(
    CategoryFunnel(
        category="employment",
        stages=("DISCOVERED", "ELIGIBLE", "APPLICATION", "RESPONSE", "INTERVIEW", "OFFER", "HIRED", "RETAINED"),
        probability_types=(
            ProbabilityType.P_ELIGIBLE,
            ProbabilityType.P_APPLICATION,
            ProbabilityType.P_RESPONSE,
            ProbabilityType.P_INTERVIEW,
            ProbabilityType.P_OFFER,
            ProbabilityType.P_ACCEPT,
            ProbabilityType.P_RETENTION,
        ),
        outcome_mapping={
            "hired": "HIRED",
            "rejected": "REJECTED",
            "declined": "DECLINED",
        },
        description="Employment: discovery → eligibility → application → response → interview → offer → hire → retention",
    )
)

# Investment
register_funnel(
    CategoryFunnel(
        category="investment",
        stages=("DISCOVERED", "THESIS", "ELIGIBLE", "EXECUTED", "OUTCOME", "REVIEWED"),
        probability_types=(
            ProbabilityType.P_THESIS,
            ProbabilityType.P_ELIGIBLE,
            ProbabilityType.P_EXECUTION,
            ProbabilityType.P_RETURN,
            ProbabilityType.P_RISK,
        ),
        outcome_mapping={
            "profit": "PROFIT",
            "loss": "LOSS",
            "break_even": "BREAK_EVEN",
        },
        description="Investment: discovery → thesis → eligibility → execution → outcome → review",
    )
)


# ────────────────────────────────────────────────────────────────
# Helper: Get probability types for a category
# ────────────────────────────────────────────────────────────────


def get_probability_types_for_category(category: str) -> tuple[ProbabilityType, ...]:
    """Get the probability types used in a category's funnel."""
    funnel = get_funnel(category)
    return funnel.probability_types


def get_stages_for_category(category: str) -> tuple[str, ...]:
    """Get the stages for a category's funnel."""
    funnel = get_funnel(category)
    return funnel.stages
