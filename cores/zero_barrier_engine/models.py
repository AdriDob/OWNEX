"""Zero-Barrier Income Engine Models

Core data models for the Zero-Barrier Maximum Income Engine.
Public-first, zero-barrier, EV/hour focused.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from cores.direct_work_engine.models import (
    DifficultyLevel as BaseDifficultyLevel,
)
from cores.direct_work_engine.models import (
    ExperienceLevel as BaseExperienceLevel,
)
from cores.direct_work_engine.models import (
    OpportunityCategory as BaseOpportunityCategory,
)
from cores.direct_work_engine.models import (
    PaymentMethod as BasePaymentMethod,
)
from cores.direct_work_engine.models import (
    UserProfile as BaseUserProfile,
)
from cores.direct_work_engine.models import (
    WorkPlatform as BaseWorkPlatform,
)

# Re-export base enums with zero-barrier specific extensions
WorkPlatform = BaseWorkPlatform
OpportunityCategory = BaseOpportunityCategory
PaymentMethod = BasePaymentMethod
DifficultyLevel = BaseDifficultyLevel
ExperienceLevel = BaseExperienceLevel
# ZeroBarrierLevel = BaseBarrierLevel  # type: ignore


class OpportunitySource(StrEnum):
    """Public sources of zero-barrier opportunities."""

    # Bug Bounty Platforms
    HACKERONE = "hackerone"
    BUGCROWD = "bugcrowd"
    INTIGRITI = "intigriti"
    YESWEHACK = "yeswehack"
    IMMUNEFI = "immunefi"

    # Dev Bounty Platforms
    GITHUB = "github"
    ALGORA = "algora"
    OPIRE = "opire"
    SUPERTEAM = "superteam"

    # AI/Technical Work Platforms
    OUTLIER = "outlier"
    MERCOR = "mercor"
    DATA_ANNOTATION = "data_annotation"
    MINDRIFT = "mindrift"
    CROWDGEN = "crowdgen"
    REMOTASKS = "remotasks"

    # Web3/Dev Bounties
    SUPERTEAM_DEV = "superteam_dev"
    ALGORA_DEV = "algora_dev"
    OPIRE_DEV = "opire_dev"
    GITHUB_BOUNTIES = "github_bounties"

    # Competitions
    CODEFORCES = "codeforces"
    LEETCODE = "leetcode"
    KAGGLE = "kaggle"
    HUGGINGFACE = "huggingface"

    # Direct Public Programs
    GOOGLE_VRP = "google_vrp"
    MICROSOFT_VRP = "microsoft_vrp"
    APPLE_VRP = "apple_vrp"
    META_VRP = "meta_vrp"
    AMAZON_VRP = "amazon_vrp"


class OpportunitySourceType(StrEnum):
    """Type of opportunity source."""

    BUG_BOUNTY_PLATFORM = "bug_bounty_platform"
    DEV_BOUNTY_PLATFORM = "dev_bounty_platform"
    AI_TECHNICAL_PLATFORM = "ai_technical_platform"
    COMPETITION_PLATFORM = "competition_platform"
    DIRECT_PUBLIC_PROGRAM = "direct_public_program"


class ZeroBarrierLevel(StrEnum):
    ZERO = "zero"
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    PENDING = "pending"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"


# Re-export base classes with zero-barrier specific fields
@dataclass(slots=True)
class ZeroBarrierScore:
    """Zero-barrier score with per-factor breakdown."""

    total: float = 0.0
    factors: dict[str, float] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    level: ZeroBarrierLevel = ZeroBarrierLevel.HIGH
    reasoning: list[str] = field(default_factory=list)
    enablers: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def is_zero_barrier(self) -> bool:
        return self.level in (ZeroBarrierLevel.ZERO, ZeroBarrierLevel.VERY_LOW, ZeroBarrierLevel.LOW)


@dataclass(slots=True)
class PublicOpportunity:
    """A single public zero-barrier opportunity."""

    id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:8])
    title: str = ""
    source: str = ""
    source_type: str = ""
    platform: str = ""
    category: str = ""

    # Basic info
    description: str = ""
    url: str = ""

    # Economic
    reward_min: float = 0.0
    reward_max: float = 0.0
    reward_typical: float = 0.0
    currency: str = "USD"
    payment_method: str = "OTHER"
    payment_methods: list[str] = field(default_factory=list)
    payment_proven: bool = False

    # Barrier
    zero_barrier_level: ZeroBarrierLevel = ZeroBarrierLevel.HIGH
    zero_barrier_score: float = 0.0
    requires_kyc: bool = False
    requires_invitation: bool = False
    requires_portfolio: bool = False
    requires_interview: bool = False
    requires_experience: bool = False
    requires_assessment: bool = False
    requires_technical_test: bool = False
    requires_registration: bool = False
    requires_portfolio_review: bool = False

    # Work
    estimated_hours: float = 0.0
    difficulty: str = "intermediate"
    skills_required: list[str] = field(default_factory=list)
    experience_required: str = "none"
    remote: bool = True
    async_work: bool = True

    # Economic
    reward_min: float = 0.0
    reward_max: float = 0.0
    reward_typical: float = 0.0
    currency: str = "USD"
    payment_method: str = "OTHER"
    payment_methods: list[str] = field(default_factory=list)
    payment_proven: bool = False
    payment_latency_days: int = 30
    payment_reliability: float = 0.5

    # Competition & probability
    competition_level: str = "medium"
    duplication_risk: str = "medium"
    acceptance_probability: float = 0.5
    duplicate_risk: float = 0.3
    disqualification_risk: float = 0.2
    competition_level: str = "medium"
    researcher_density: float = 0.5

    # Verification
    verification_status: str = "unverified"
    last_verified: datetime | None = None
    source_url: str = ""
    program_url: str = ""
    scope: str = ""
    out_of_scope: str = ""
    known_duplicates: list[str] = field(default_factory=list)

    # Skill match
    skills_required: list[str] = field(default_factory=list)
    experience_required: str = "none"
    skills_match: float = 0.0
    skill_match_details: dict[str, float] = field(default_factory=dict)

    # Timing
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    deadline: datetime | None = None
    time_to_first_payment_days: int = 30
    time_to_work_start_hours: float = 0.0

    # Upside
    max_potential: float = 0.0
    upside_potential: str = "medium"
    upside_score: float = 0.0

    # Metadata
    source_url: str = ""
    program_url: str = ""
    platform: str = ""
    category: str = ""

    def __post_init__(self):
        if not self.id:
            import uuid

            self.id = uuid.uuid4().hex[:8]


@dataclass(slots=True)
class EVHourScore:
    """Expected Value per Human Hour score."""

    ev_hour: float = 0.0
    expected_value: float = 0.0
    probability_success: float = 0.0
    expected_payout: float = 0.0
    estimated_hours: float = 0.0
    human_hours: float = 0.0
    machine_hours: float = 0.0
    automation_level: str = "A0"
    automation_savings_hours: float = 0.0
    time_to_payment_days: int = 30
    capital_velocity_factor: float = 1.0
    risk_adjusted: float = 0.0
    breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class RankedOpportunity:
    """Opportunity with ranking and scoring."""

    opportunity: PublicOpportunity
    rank: int = 0
    zero_barrier_score: float = 0.0
    ev_hour_score: EVHourScore | None = None
    ev_hour: float = 0.0
    expected_value: float = 0.0
    acceptance_probability: float = 0.0
    compatibility_score: float = 0.0
    speed_score: float = 0.0
    reputation_score: float = 0.0
    risk_score: float = 0.0
    overall_score: float = 0.0
    reasoning: list[str] = field(default_factory=list)
    strategy: str = ""
    discovered_at: str = ""
    payment_compat_score: float = 100.0
    payment_compat_notes: list[str] = field(default_factory=list)
    is_best_action: bool = False
    action_packet: Any = None


@dataclass(slots=True)
class SkillMap:
    """User's skill map with economic valuation."""

    skills: dict[str, dict] = field(default_factory=dict)
    verified_skills: list[str] = field(default_factory=list)
    learning_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    skill_values: dict[str, float] = field(default_factory=dict)
    learning_priority: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ActionPacket:
    """Prepared action packet for human execution."""

    opportunity_id: str
    why_this: str
    what_to_do: list[str]
    where_to_start: str
    what_to_check: list[str]
    what_skill_required: list[str]
    estimated_hours: float
    expected_value: float
    risks: list[str]
    stop_condition: str
    success_condition: str
    preparation_steps: list[str] = field(default_factory=list)
    human_gates: list[str] = field(default_factory=list)
    automation_available: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IncomeLane:
    """Income lane configuration."""

    name: str
    description: str
    categories: list[str]
    target_monthly: float
    target_ev_hour: float
    automation_level: str
    human_hours_target: float
    priority: int


@dataclass(slots=True)
class LaneAllocation:
    """Current lane allocation recommendation."""

    cashflow: float
    high_ev: float
    skill_compounding: float
    recommended_hours: dict[str, float]
    reasoning: str


# Re-export UserProfile from base with zero-barrier extensions
UserProfile = BaseUserProfile


# Add any zero-barrier specific extensions here if needed
# (The base UserProfile already has the needed fields)
