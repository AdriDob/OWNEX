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


class WorkStream(StrEnum):
    """High-level work streams — what the user actually operates on.

    Each stream bundles related OpportunityCategory, shares platform access
    patterns, and has a distinct user workflow. OWNEX automates discovery,
    scoring, and delivery prep; the user only: configures access, reviews
    packages, and approves submissions.
    """

    # Security / Bug Bounty — public programs, API-key platforms, outcome-based
    BUG_BOUNTY = "bug_bounty"

    # Dev Bounty / Freelance — platforms where you submit code/PRs for rewards
    DEV_BOUNTY = "dev_bounty"

    # AI Work — evaluation, annotation, synthetic data (zero-barrier, assessment-based)
    AI_WORK = "ai_work"

    # Game Dev Programming — programming-only specializations
    GAME_DEV = "game_dev"

    # Open Source / Community — bounties, sponsors, grants
    OPEN_SOURCE = "open_source"

    # Technical Content — writing, docs, code review
    TECH_CONTENT = "tech_content"


# Canonical mapping: every OpportunityCategory → exactly one WorkStream.
# This is the SSOT for UI filtering, platform grouping, and action routing.
CATEGORY_TO_STREAM: dict[OpportunityCategory, WorkStream] = {
    # Bug Bounty stream
    OpportunityCategory.BUG_BOUNTY: WorkStream.BUG_BOUNTY,
    OpportunityCategory.SECURITY_RESEARCH: WorkStream.BUG_BOUNTY,
    OpportunityCategory.OSS_BOUNTIES: WorkStream.BUG_BOUNTY,
    OpportunityCategory.REVERSE_ENGINEERING: WorkStream.BUG_BOUNTY,
    OpportunityCategory.MALWARE_ANALYSIS: WorkStream.BUG_BOUNTY,
    OpportunityCategory.SMART_CONTRACTS: WorkStream.BUG_BOUNTY,
    OpportunityCategory.COMPETITIONS: WorkStream.BUG_BOUNTY,
    # Dev Bounty stream
    OpportunityCategory.DEV_BOUNTY: WorkStream.DEV_BOUNTY,
    OpportunityCategory.SOFTWARE_ENGINEERING: WorkStream.DEV_BOUNTY,
    OpportunityCategory.BACKEND: WorkStream.DEV_BOUNTY,
    OpportunityCategory.FRONTEND: WorkStream.DEV_BOUNTY,
    OpportunityCategory.FULL_STACK: WorkStream.DEV_BOUNTY,
    OpportunityCategory.DEVOPS: WorkStream.DEV_BOUNTY,
    OpportunityCategory.CLOUD: WorkStream.DEV_BOUNTY,
    OpportunityCategory.INFRASTRUCTURE: WorkStream.DEV_BOUNTY,
    OpportunityCategory.API_DEVELOPMENT: WorkStream.DEV_BOUNTY,
    OpportunityCategory.SDK_DEVELOPMENT: WorkStream.DEV_BOUNTY,
    OpportunityCategory.BROWSER_AUTOMATION: WorkStream.DEV_BOUNTY,
    OpportunityCategory.QA_AUTOMATION: WorkStream.DEV_BOUNTY,
    OpportunityCategory.WEB_SCRAPING: WorkStream.DEV_BOUNTY,
    OpportunityCategory.CODE_REVIEW: WorkStream.DEV_BOUNTY,
    OpportunityCategory.MOBILE_DEVELOPMENT: WorkStream.DEV_BOUNTY,
    OpportunityCategory.DESKTOP_DEVELOPMENT: WorkStream.DEV_BOUNTY,
    OpportunityCategory.EMBEDDED: WorkStream.DEV_BOUNTY,
    OpportunityCategory.IOT: WorkStream.DEV_BOUNTY,
    OpportunityCategory.BLOCKCHAIN_DEVELOPMENT: WorkStream.DEV_BOUNTY,
    # AI Work stream
    OpportunityCategory.AI_EVALUATION: WorkStream.AI_WORK,
    OpportunityCategory.DATA_ANNOTATION: WorkStream.AI_WORK,
    OpportunityCategory.SYNTHETIC_DATA: WorkStream.AI_WORK,
    OpportunityCategory.AI_ENGINEERING: WorkStream.AI_WORK,
    OpportunityCategory.ML_ENGINEERING: WorkStream.AI_WORK,
    OpportunityCategory.LLM_ENGINEERING: WorkStream.AI_WORK,
    OpportunityCategory.PROMPT_ENGINEERING: WorkStream.AI_WORK,
    # Game Dev stream
    OpportunityCategory.GAME_DEVELOPMENT: WorkStream.GAME_DEV,
    # Open Source stream
    OpportunityCategory.OPEN_SOURCE: WorkStream.OPEN_SOURCE,
    OpportunityCategory.OSS_BOUNTIES: WorkStream.OPEN_SOURCE,  # also in bug bounty
    # Tech Content stream
    OpportunityCategory.TECHNICAL_WRITING: WorkStream.TECH_CONTENT,
    OpportunityCategory.DOCUMENTATION: WorkStream.TECH_CONTENT,
    OpportunityCategory.CODE_REVIEW: WorkStream.TECH_CONTENT,  # also in dev bounty
}


# What the user needs to SEE per stream (minimal, actionable)
STREAM_UI_CONFIG: dict[WorkStream, dict] = {
    WorkStream.BUG_BOUNTY: {
        "label": "Bug Bounty",
        "icon": "🎯",
        "description": "Programas públicos de vulnerabilidades. Descubrimiento → hipótesis → reporte.",
        "platforms": ["hackerone", "bugcrowd", "intigriti", "yeswehack", "immunefi"],
        "access_type": "api_key",  # needs API key for earnings sync
        "deliverables": ["PoC", "Report", "Steps to reproduce", "Impact assessment"],
        "quick_actions": ["run_scan", "view_findings", "generate_report", "sync_earnings"],
        "automation": "discover programs → score barriers → prep reports → queue delivery",
        "user_decides": ["which programs to scan", "validate findings", "submit reports"],
    },
    WorkStream.DEV_BOUNTY: {
        "label": "Dev Bounty",
        "icon": "⚡",
        "description": "Tareas de código con recompensa (Opire, IssueHunt, Algora, Freelancer).",
        "platforms": ["opire", "issuehunt", "algora", "freelancer", "opencollective"],
        "access_type": "mixed",  # public + manual setup
        "deliverables": ["PR/Commit", "Tests passing", "Documentation", "README"],
        "quick_actions": ["clone_repo", "analyze_issue", "generate_fix", "create_pr", "submit_work"],
        "automation": "discover issues → analyze repo → generate fix → run tests → prep PR",
        "user_decides": ["which issues to take", "review generated code", "approve PR"],
    },
    WorkStream.AI_WORK: {
        "label": "AI Work",
        "icon": "🤖",
        "description": "Evaluación de modelos, anotación de datos, datos sintéticos (Outlier, Mindrift, etc.).",
        "platforms": ["outlier", "mindrift", "alignerr", "mercor", "dataannotation"],
        "access_type": "manual_setup",  # account + assessment
        "deliverables": ["Completed tasks", "Quality metrics", "Time logs"],
        "quick_actions": ["start_assessment", "view_queue", "submit_batch", "track_earnings"],
        "automation": "discover tasks → filter by skill → prep workspace → queue submission",
        "user_decides": ["which platforms to join", "complete assessments", "submit work"],
    },
    WorkStream.GAME_DEV: {
        "label": "Game Dev",
        "icon": "🎮",
        "description": "Especializaciones de programación de videojuegos (Unity, Unreal, Godot, etc.).",
        "platforms": ["freelancer", "opire", "algora", "upwork"],
        "access_type": "manual_setup",
        "deliverables": ["Code modules", "Systems", "Tools", "Performance fixes"],
        "quick_actions": ["filter_specialization", "view_tech_stack", "submit_unity_cpp"],
        "automation": "filter by specialization → match tech stack → prep delivery",
        "user_decides": ["specialization focus", "engine/language match", "review code"],
    },
    WorkStream.OPEN_SOURCE: {
        "label": "Open Source",
        "icon": "🌐",
        "description": "Bounties, sponsors, grants en proyectos open source.",
        "platforms": ["opencollective", "github_sponsors", "polar", "opire"],
        "access_type": "manual_setup",
        "deliverables": ["PR merged", "Issue resolved", "Documentation", "Release notes"],
        "quick_actions": ["find_good_first_issues", "track_sponsors", "submit_pr"],
        "automation": "discover repos → filter by label → assess effort → prep PR",
        "user_decides": ["which projects to contribute", "review maintainer feedback"],
    },
    WorkStream.TECH_CONTENT: {
        "label": "Tech Content",
        "icon": "📝",
        "description": "Escritura técnica, documentación, code review remunerado.",
        "platforms": ["freelancer", "technical_writing_platforms", "docs_bounties"],
        "access_type": "manual_setup",
        "deliverables": ["Articles", "Docs", "Review reports", "Tutorials"],
        "quick_actions": ["find_writing_gigs", "submit_draft", "track_publications"],
        "automation": "match topics → outline → draft → review → deliver",
        "user_decides": ["topic selection", "review/edit content", "approve publication"],
    },
}


# Platform → primary stream (for quick filtering)
PLATFORM_PRIMARY_STREAM: dict[str, WorkStream] = {
    "hackerone": WorkStream.BUG_BOUNTY,
    "bugcrowd": WorkStream.BUG_BOUNTY,
    "intigriti": WorkStream.BUG_BOUNTY,
    "yeswehack": WorkStream.BUG_BOUNTY,
    "immunefi": WorkStream.BUG_BOUNTY,
    "opire": WorkStream.DEV_BOUNTY,
    "issuehunt": WorkStream.DEV_BOUNTY,
    "algora": WorkStream.DEV_BOUNTY,
    "freelancer": WorkStream.DEV_BOUNTY,
    "opencollective": WorkStream.OPEN_SOURCE,
    "outlier": WorkStream.AI_WORK,
    "mindrift": WorkStream.AI_WORK,
    "alignerr": WorkStream.AI_WORK,
    "mercor": WorkStream.AI_WORK,
    "dataannotation": WorkStream.AI_WORK,
    "upwork": WorkStream.DEV_BOUNTY,
}


def get_stream_for_category(category: OpportunityCategory) -> WorkStream:
    """Get the primary work stream for a category."""
    return CATEGORY_TO_STREAM.get(category, WorkStream.DEV_BOUNTY)


def get_stream_for_platform(platform: str) -> WorkStream:
    """Get the primary work stream for a platform."""
    return PLATFORM_PRIMARY_STREAM.get(platform.lower(), WorkStream.DEV_BOUNTY)

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
    """How a worker gets from "outside" to "doing paid work".

    Capability mechanisms (ASSESSMENT/TRAINING/TEST) are one-time,
    amortizable costs that prove skill — they are NOT hiring funnels.
    Funnel mechanisms (INTERVIEW/PORTFOLIO/EXPERIENCE_REVIEW/INVITATION)
    gate on who you are, not what you can do.

    "Zero Experience does not mean Zero Barrier": an opportunity can require
    a capability assessment and still accept workers with no prior job
    history in the category.
    """

    DIRECT = "direct"
    REGISTRATION = "registration"
    ASSESSMENT = "assessment"
    TRAINING = "training"
    TEST = "test"
    INTERVIEW = "interview"
    PORTFOLIO = "portfolio"
    EXPERIENCE_REVIEW = "experience_review"
    INVITATION = "invitation"


# Mechanisms that prove capability once (amortized over a work stream).
CAPABILITY_MECHANISMS: frozenset[EntryMechanism] = frozenset(
    {EntryMechanism.ASSESSMENT, EntryMechanism.TRAINING, EntryMechanism.TEST}
)

# Mechanisms that gate on identity/history (hiring funnel).
FUNNEL_MECHANISMS: frozenset[EntryMechanism] = frozenset(
    {
        EntryMechanism.INTERVIEW,
        EntryMechanism.PORTFOLIO,
        EntryMechanism.EXPERIENCE_REVIEW,
        EntryMechanism.INVITATION,
    }
)


class ExperienceRequirement(StrEnum):
    """Whether prior work history in the category is required to enter."""

    NONE = "none"
    OPTIONAL = "optional"
    PREFERRED = "preferred"
    REQUIRED = "required"


# Requirement levels compatible with working without prior experience.
ZERO_EXPERIENCE_REQUIREMENTS: frozenset[ExperienceRequirement] = frozenset(
    {ExperienceRequirement.NONE, ExperienceRequirement.OPTIONAL}
)


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

    # Entry model (additive, 2026-08-25): distinguishes "no prior experience
    # needed" from "nothing stands between you and the work". Legacy data
    # without these fields derives them from the classic barrier flags.
    entry_mechanism: EntryMechanism = EntryMechanism.DIRECT
    experience_requirement: ExperienceRequirement | None = None
    hourly_rate_usd: float | None = None  # for hourly-stream work shapes
    time_to_first_work_hours: float | None = None
    rate_source: str = "unknown"  # platform | ownex_history | unknown

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

    # ── Derived entry-model facts (single definition point) ──

    @property
    def effective_experience_requirement(self) -> ExperienceRequirement:
        """Legacy-aware view of the experience gate.

        New data sets ``experience_requirement`` explicitly; legacy records
        only carry ``experience_required`` (a depth level), which maps as:
        NONE→NONE (no gate), JUNIOR→OPTIONAL, MID/SENIOR→REQUIRED.
        """
        if self.experience_requirement is not None:
            return self.experience_requirement
        if self.experience_required == ExperienceLevel.NONE:
            return ExperienceRequirement.NONE
        if self.experience_required == ExperienceLevel.JUNIOR:
            return ExperienceRequirement.OPTIONAL
        return ExperienceRequirement.REQUIRED

    @property
    def is_zero_experience(self) -> bool:
        """No prior work history in the category needed to do this work."""
        return self.effective_experience_requirement in ZERO_EXPERIENCE_REQUIREMENTS

    @property
    def is_zero_barrier(self) -> bool:
        """Nothing at all stands between you and paid work right now.

        Strictly stronger than zero-experience: no application gate of any
        kind (assessment/training/test/interview/portfolio/approval).
        """
        return (
            self.entry_mechanism == EntryMechanism.DIRECT
            and not self.technical_test_required
            and not self.interview_required
            and not self.portfolio_required
            and self.effective_experience_requirement in ZERO_EXPERIENCE_REQUIREMENTS
        )


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
    # HTROI — Human-Time Adjusted ROI (Fase C, Income Multiplier)
    htroi: HumanTimeAdjustedROI | None = None
