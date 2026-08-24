"""Data models for the Direct Work Engine.

Describes remote technology opportunities across every supported category and
scores their entry barrier as a continuous spectrum (never a binary promise).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class OpportunityCategory(StrEnum):
    """All IT ecosystem categories OWNEX can discover and score.

    This is THE canonical product taxonomy; other engines map onto it via
    ``cores.work_taxonomy`` (exhaustiveness enforced by tests).
    """

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
    """Programming-only specializations within Game Development.

    Artistic disciplines (concept art, character design, environment design,
    UI art, artistic animation) are deliberately excluded by contract.
    """

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
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Payment methods that can receive money internationally from any country.
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

# Payment method reliability multiplier used by the scorer.
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

# The only specializations accepted under Game Development (programming-only).
GAME_DEVELOPMENT_SPECIALIZATIONS: frozenset[GameDevSpecialization] = frozenset(GameDevSpecialization)


@dataclass(slots=True)
class ZeroBarrierScore:
    """Continuous 0-100 entry-barrier score with per-factor breakdown.

    Higher is better: closer to "no experience, no portfolio, no interview,
    direct form, international payment, remote". Never a promise that zero
    barrier exists everywhere — only a ranking of how low the barrier is.
    """

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


@dataclass(slots=True)
class Opportunity:
    """A single discovered remote opportunity with full barrier metadata."""

    id: str
    title: str
    platform: WorkPlatform
    category: OpportunityCategory
    url: str = ""
    description: str = ""

    company: str = ""
    country: str = ""
    remote: bool = True

    payment: float = 0.0
    currency: str = "USD"
    payment_method: PaymentMethod = PaymentMethod.OTHER
    international_payment: bool | None = None

    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    language_required: str = ""
    estimated_time_hours: float = 0.0

    experience_required: ExperienceLevel = ExperienceLevel.NONE
    portfolio_required: bool = False
    interview_required: bool = False
    technical_test_required: bool = False
    registration_required: bool = False

    time_to_payout_days: float | None = None
    reputation: float = 0.5
    risk: float = 0.5
    payment_proven: bool = False
    stability: float = 0.5
    compatibility: float = 0.5

    accepts_beginner: bool = True
    accepts_freelancers: bool = True
    accepts_individuals: bool = True
    accepts_ai_tools: bool = True
    asynchronous: bool = True

    specialization: GameDevSpecialization | None = None
    technology_tags: list[str] = field(default_factory=list)
    employment_type: EmploymentType = EmploymentType.CONTRACT

    # Zero Barrier Score (populated by scorer)
    zero_barrier_score: ZeroBarrierScore | None = None

    def __post_init__(self) -> None:
        if self.category == OpportunityCategory.GAME_DEVELOPMENT:
            if self.specialization is None:
                raise ValueError("Game Development requires a programming specialization")
            if self.specialization not in GAME_DEVELOPMENT_SPECIALIZATIONS:
                raise ValueError(
                    f"{getattr(self.specialization, 'value', self.specialization)} is not a programming-only "
                    "Game Development specialization"
                )
        if self.international_payment is None:
            self.international_payment = self.payment_method in INTERNATIONAL_PAYMENT_METHODS


@dataclass(slots=True)
class UserProfile:
    """Real facts about the user. Used for compatibility, never invented."""

    name: str
    country: str = "Argentina"
    languages: set[str] = field(default_factory=lambda: {"es", "en"})
    skills: set[str] = field(default_factory=set)
    experience_level: ExperienceLevel = ExperienceLevel.NONE
    remote_only: bool = True
    accepts_ai_tools: bool = True
    availability_hours: float = 40.0
    portfolio_url: str = ""
    github_url: str = ""
    linkedin_url: str = ""
    projects: list[str] = field(default_factory=list)
    has_portfolio: bool = False
    async_preferred: bool = True
    preferred_payment_methods: list[PaymentMethod] = field(default_factory=list)
    preferred_currencies: list[str] = field(default_factory=lambda: ["USD"])
    preferred_employment_types: list[EmploymentType] = field(default_factory=list)
    platform_success_rates: dict[str, float] = field(default_factory=dict)
    category_success_rates: dict[str, float] = field(default_factory=dict)
    preferred_categories: list[OpportunityCategory] = field(default_factory=list)
    excluded_categories: list[OpportunityCategory] = field(default_factory=list)
    min_payment: float = 0.0
    total_earnings: float = 0.0
    applications_submitted: int = 0
    applications_accepted: int = 0
    avg_time_to_payment_days: float = 0.0


@dataclass(slots=True)
class RankedOpportunity:
    """Opportunity with ranking and recommendation metadata."""

    opportunity: Opportunity
    rank: int = 0
    zero_barrier_score: ZeroBarrierScore | None = None
    expected_value: float = 0.0
    acceptance_probability: float = 0.0
    compatibility_score: float = 0.0
    speed_score: float = 0.0
    reputation_score: float = 0.0
    risk_score: float = 0.0
    overall_recommendation_score: float = 0.0
    recommendation_reasoning: list[str] = field(default_factory=list)
    strategy: str | None = None
    discovered_at: str = ""
    payment_compat_score: float = 100.0
    payment_compat_notes: list[str] = field(default_factory=list)
