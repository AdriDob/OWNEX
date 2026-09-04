"""Opportunity Genome — Single Source of Truth for all opportunities across OWNEX.

This is the canonical model that unifies:
- database/models.py (SQLAlchemy persistence)
- cores/direct_work_engine/models.py (DWE active engine)
- cores/opportunity/models.py (legacy intelligence layer)

All legacy models map TO this genome. No logic lives here — only data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class GenomeSource(StrEnum):
    """Origin system that produced this genome entry."""

    DIRECT_WORK = "direct_work"  # cores/direct_work_engine discovery
    LEGACY_INTEL = "legacy_intel"  # cores/opportunity engine
    DATABASE = "database"  # database/models.py (Target/Finding/Report)
    MANUAL = "manual"  # user-created
    IMPORTED = "imported"  # bulk import / migration


class GenomeStatus(StrEnum):
    """Lifecycle state of an opportunity genome."""

    DISCOVERED = "discovered"  # just found, not yet evaluated
    QUALIFIED = "qualified"  # passed strict filter, barrier scored
    SELECTED = "selected"  # chosen for execution
    PREPARED = "prepared"  # delivery package ready
    EXECUTING = "executing"  # work in progress (coding, testing, etc.)
    VALIDATING = "validating"  # quality gate running
    DELIVERING = "delivering"  # submission in progress
    LEARNED = "learned"  # outcome recorded, feedback applied
    PAID = "paid"  # money received, cycle complete
    ARCHIVED = "archived"  # rejected, expired, or superseded


class WorkStream(StrEnum):
    """High-level work streams (from DWE)."""

    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    AI_WORK = "ai_work"
    GAME_DEV = "game_dev"
    OPEN_SOURCE = "open_source"
    TECH_CONTENT = "tech_content"


class OpportunityCategory(StrEnum):
    """Canonical product taxonomy (from DWE)."""

    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    SECURITY_RESEARCH = "security_research"
    OSS_BOUNTIES = "oss_bounties"
    OPEN_SOURCE = "open_source"
    SOFTWARE_ENGINEERING = "software_engineering"
    BACKEND = "backend"
    FRONTEND = "frontend"
    FULL_STACK = "full_stack"
    DEVOPS = "devops"
    CLOUD = "cloud"
    INFRASTRUCTURE = "infrastructure"
    AI_ENGINEERING = "ai_engineering"
    ML_ENGINEERING = "ml_engineering"
    LLM_ENGINEERING = "llm_engineering"
    PROMPT_ENGINEERING = "prompt_engineering"
    BROWSER_AUTOMATION = "browser_automation"
    QA_AUTOMATION = "qa_automation"
    REVERSE_ENGINEERING = "reverse_engineering"
    MALWARE_ANALYSIS = "malware_analysis"
    EMBEDDED = "embedded"
    IOT = "iot"
    MOBILE_DEVELOPMENT = "mobile_development"
    DESKTOP_DEVELOPMENT = "desktop_development"
    API_DEVELOPMENT = "api_development"
    SDK_DEVELOPMENT = "sdk_development"
    BLOCKCHAIN_DEVELOPMENT = "blockchain_development"
    SMART_CONTRACTS = "smart_contracts"
    DATA_ENGINEERING = "data_engineering"
    WEB_SCRAPING = "web_scraping"
    TECHNICAL_WRITING = "technical_writing"
    DOCUMENTATION = "documentation"
    AI_EVALUATION = "ai_evaluation"
    DATA_ANNOTATION = "data_annotation"
    SYNTHETIC_DATA = "synthetic_data"
    CODE_REVIEW = "code_review"
    GAME_DEVELOPMENT = "game_development"
    COMPETITIONS = "competitions"


class GameDevSpecialization(StrEnum):
    GAMEPLAY_PROGRAMMING = "gameplay_programming"
    UNREAL_CPP = "unreal_cpp"
    UNITY_CSHARP = "unity_csharp"
    GODOT = "godot"
    MULTIPLAYER_NETWORKING = "multiplayer_networking"
    AI_PROGRAMMING = "ai_programming"
    ENGINE_PROGRAMMING = "engine_programming"
    RENDERING = "rendering"
    PHYSICS = "physics"
    TOOLS_PROGRAMMING = "tools_programming"
    ECS = "ecs"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    GAME_BACKEND = "game_backend"
    SDK_INTEGRATION = "sdk_integration"
    MOBILE_GAMES = "mobile_games"
    STEAM_INTEGRATION = "steam_integration"
    CONSOLE_DEVELOPMENT = "console_development"
    LIVE_SERVICE = "live_service"
    BUILD_PIPELINES = "build_pipelines"


class WorkPlatform(StrEnum):
    HACKERONE = "hackerone"
    BUG_CROWD = "bugcrowd"
    INTIGRITI = "intigriti"
    YES_WE_HACK = "yeswehack"
    SYNCACK = "synack"
    IMMUNEFI = "immunefi"
    ALGORA = "algora"
    OPIRE = "opire"
    OPEN_COLLECTIVE = "opencollective"
    ISSUE_HUNT = "issuehunt"
    FREELANCER = "freelancer"
    UPWORK = "upwork"
    FIVERR = "fiverr"
    SUPER_TEAM = "superteam"
    GITHUB = "github"
    OUTLIER = "outlier"
    MINDRIFT = "mindrift"
    DATA_ANNOTATION_PLATFORM = "data_annotation_platform"
    LINKEDIN = "linkedin"
    REMOTASKS = "remotasks"
    OPYRE_MICROTASK = "opyre_microtask"
    FREELANCER_MICROTASK = "freelancer_microtask"
    COMPANY_WEBSITE = "company_website"
    CODE4RENA = "code4rena"
    OTHER = "other"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    BOUNTY = "bounty"
    MICROTASK = "microtask"
    CHALLENGE = "challenge"
    PRIZE = "prize"
    OPEN_CALL = "open_call"
    ROLLING = "rolling"
    PROJECT = "project"
    RETAINER = "retainer"


class PaymentMethod(StrEnum):
    PAYPAL = "paypal"
    PAYONEER = "payoneer"
    WISE = "wise"
    BANK_WIRE = "bank_wire"
    CRYPTO = "crypto"
    STABLECOIN = "stablecoin"
    GIFT_CARD = "gift_card"
    PLATFORM_CREDIT = "platform_credit"
    OTHER = "other"


class DifficultyLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ExperienceLevel(StrEnum):
    NONE = "none"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"


class BarrierLevel(StrEnum):
    ZERO = "zero"
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EntryMechanism(StrEnum):
    DIRECT = "direct"
    REGISTRATION = "registration"
    ASSESSMENT = "assessment"
    TRAINING = "training"
    TEST = "test"
    INTERVIEW = "interview"
    PORTFOLIO = "portfolio"
    EXPERIENCE_REVIEW = "experience_review"
    INVITATION = "invitation"


CAPABILITY_MECHANISMS: frozenset[EntryMechanism] = frozenset(
    {EntryMechanism.ASSESSMENT, EntryMechanism.TRAINING, EntryMechanism.TEST}
)

FUNNEL_MECHANISMS: frozenset[EntryMechanism] = frozenset(
    {
        EntryMechanism.INTERVIEW,
        EntryMechanism.PORTFOLIO,
        EntryMechanism.EXPERIENCE_REVIEW,
        EntryMechanism.INVITATION,
    }
)


class ExperienceRequirement(StrEnum):
    NONE = "none"
    OPTIONAL = "optional"
    PREFERRED = "preferred"
    REQUIRED = "required"


ZERO_EXPERIENCE_REQUIREMENTS: frozenset[ExperienceRequirement] = frozenset(
    {ExperienceRequirement.NONE, ExperienceRequirement.OPTIONAL}
)


INTERNATIONAL_PAYMENT_METHODS: frozenset[PaymentMethod] = frozenset(
    {
        PaymentMethod.PAYPAL,
        PaymentMethod.PAYONEER,
        PaymentMethod.WISE,
        PaymentMethod.BANK_WIRE,
        PaymentMethod.CRYPTO,
        PaymentMethod.STABLECOIN,
    }
)


PAYMENT_RELIABILITY: dict[PaymentMethod, float] = {
    PaymentMethod.PAYPAL: 1.0,
    PaymentMethod.PAYONEER: 1.0,
    PaymentMethod.WISE: 1.0,
    PaymentMethod.BANK_WIRE: 0.9,
    PaymentMethod.STABLECOIN: 0.8,
    PaymentMethod.CRYPTO: 0.8,
    PaymentMethod.GIFT_CARD: 0.3,
    PaymentMethod.PLATFORM_CREDIT: 0.2,
    PaymentMethod.OTHER: 0.5,
}


GAME_DEVELOPMENT_SPECIALIZATIONS: frozenset[GameDevSpecialization] = frozenset(GameDevSpecialization)


@dataclass(slots=True)
class ZeroBarrierScore:
    """Continuous 0-100 entry-barrier score with per-factor breakdown."""

    total: float = 0.0
    factors: dict[str, float] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    barrier_level: BarrierLevel = BarrierLevel.HIGH
    reasoning: list[str] = field(default_factory=list)
    enablers: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def barrier_label(self) -> str:
        return self.barrier_level.value

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage/API."""
        return {
            "total": self.total,
            "factors": self.factors,
            "weights": self.weights,
            "barrier_level": self.barrier_level.value,
            "reasoning": self.reasoning,
            "enablers": self.enablers,
            "blockers": self.blockers,
        }


@dataclass(slots=True)
class OpportunityGenome:
    """Single Source of Truth for an opportunity across all OWNEX systems."""

    # Core Identity (no defaults - required fields)
    id: str
    external_id: str
    platform: str
    title: str
    category: str

    # Core Identity (with defaults)
    source: GenomeSource = GenomeSource.DIRECT_WORK
    description: str = ""
    url: str = ""

    # Categorization
    subcategory: str | None = None
    work_stream: str = WorkStream.DEV_BOUNTY

    # Financial
    reward: float = 0.0
    currency: str = "USD"
    payment_method: str = PaymentMethod.OTHER
    time_to_payout_days: float | None = None

    # Scoring
    zero_barrier_score: ZeroBarrierScore | None = None
    expected_value: float = 0.0
    acceptance_probability: float = 0.0
    risk_score: float = 0.0
    barrier_score: float = 0.0

    # Entry Model (DWE unique)
    experience_required: str = ExperienceLevel.NONE
    experience_requirement: str | None = None
    entry_mechanism: str = EntryMechanism.DIRECT
    portfolio_required: bool = False
    interview_required: bool = False
    technical_test_required: bool = False
    registration_required: bool = False

    # Skill / Compatibility
    technology_tags: list[str] = field(default_factory=list)
    language_required: str = ""
    estimated_time_hours: float = 0.0
    difficulty: str = DifficultyLevel.INTERMEDIATE

    # Workflow
    status: str = GenomeStatus.DISCOVERED
    employment_type: str = EmploymentType.CONTRACT

    # Derived entry-model facts
    @property
    def effective_experience_requirement(self) -> ExperienceRequirement:
        if self.experience_requirement is not None:
            return ExperienceRequirement(self.experience_requirement)
        if self.experience_required == ExperienceLevel.NONE:
            return ExperienceRequirement.NONE
        if self.experience_required == ExperienceLevel.JUNIOR:
            return ExperienceRequirement.OPTIONAL
        return ExperienceRequirement.REQUIRED

    @property
    def is_zero_experience(self) -> bool:
        return self.effective_experience_requirement in ZERO_EXPERIENCE_REQUIREMENTS

    @property
    def is_zero_barrier(self) -> bool:
        return (
            self.entry_mechanism == EntryMechanism.DIRECT
            and not self.technical_test_required
            and not self.interview_required
            and not self.portfolio_required
            and self.is_zero_experience
        )

    @property
    def international_payment(self) -> bool:
        return self.payment_method in INTERNATIONAL_PAYMENT_METHODS

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API responses."""
        return {
            "id": self.id,
            "external_id": self.external_id,
            "source": self.source.value,
            "platform": self.platform,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "category": self.category,
            "subcategory": self.subcategory,
            "work_stream": self.work_stream,
            "reward": self.reward,
            "currency": self.currency,
            "payment_method": self.payment_method,
            "time_to_payout_days": self.time_to_payout_days,
            "zero_barrier_score": (
                self.zero_barrier_score.to_dict()
                if self.zero_barrier_score and hasattr(self.zero_barrier_score, "to_dict")
                else (self.zero_barrier_score.__dict__ if self.zero_barrier_score else None)
            ),
            "expected_value": self.expected_value,
            "acceptance_probability": self.acceptance_probability,
            "risk_score": self.risk_score,
            "barrier_score": self.barrier_score,
            "experience_required": self.experience_required,
            "experience_requirement": self.experience_requirement,
            "entry_mechanism": self.entry_mechanism,
            "portfolio_required": self.portfolio_required,
            "interview_required": self.interview_required,
            "technical_test_required": self.technical_test_required,
            "registration_required": self.registration_required,
            "technology_tags": self.technology_tags,
            "language_required": self.language_required,
            "estimated_time_hours": self.estimated_time_hours,
            "difficulty": self.difficulty,
            "status": self.status,
            "employment_type": self.employment_type,
            "is_zero_experience": self.is_zero_experience,
            "is_zero_barrier": self.is_zero_barrier,
            "international_payment": self.international_payment,
            "metadata": self.metadata,
            "discovered_at": self.discovered_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpportunityGenome":
        """Deserialize from API/storage."""
        # Remove computed properties that shouldn't be passed to constructor
        computed_props = {
            "is_zero_experience",
            "is_zero_barrier",
            "international_payment",
            "effective_experience_requirement",
            "barrier_label",
        }
        filtered_data = {k: v for k, v in data.items() if k not in computed_props}

        # Convert datetime strings back to datetime objects
        for dt_field in ("discovered_at", "updated_at"):
            if dt_field in filtered_data and isinstance(filtered_data[dt_field], str):
                filtered_data[dt_field] = datetime.fromisoformat(filtered_data[dt_field].replace("Z", "+00:00"))

        # Convert ZeroBarrierScore dict back to object
        if filtered_data.get("zero_barrier_score") and isinstance(filtered_data["zero_barrier_score"], dict):
            zb_data = filtered_data["zero_barrier_score"]
            filtered_data["zero_barrier_score"] = ZeroBarrierScore(**zb_data)

        return cls(**filtered_data)
