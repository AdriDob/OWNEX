"""Pydantic schemas for Economic Intelligence models."""

from __future__ import annotations

from pydantic import BaseModel

# ── Program ──

class ProgramCreate(BaseModel):
    name: str
    platform: str
    platform_program_id: str | None = None
    program_url: str | None = None
    private: bool = False
    scope_summary: str | None = None
    rewards_text: str | None = None
    exclusions_text: str | None = None
    policy_text: str | None = None
    technologies: str | None = None
    assets: str | None = None


class ProgramUpdate(BaseModel):
    name: str | None = None
    platform: str | None = None
    program_url: str | None = None
    private: bool | None = None
    status: str | None = None
    scope_summary: str | None = None
    rewards_text: str | None = None
    exclusions_text: str | None = None
    policy_text: str | None = None
    technologies: str | None = None
    assets: str | None = None
    orion_score: float | None = None
    priority: str | None = None


class ProgramOut(BaseModel):
    id: int
    name: str
    platform: str
    platform_program_id: str | None = None
    program_url: str | None = None
    private: bool = False
    status: str = "active"
    scope_summary: str | None = None
    rewards_text: str | None = None
    exclusions_text: str | None = None
    policy_text: str | None = None
    technologies: str | None = None
    assets: str | None = None
    orion_score: float = 0.0
    priority: str = "medium"
    total_reports: int = 0
    confirmed_reports: int = 0
    total_earned: float = 0.0
    total_hours_spent: float = 0.0
    last_scope_fetch: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    tier_count: int = 0


class ProgramListOut(BaseModel):
    items: list[ProgramOut]
    total: int


# ── BountyTier ──

class BountyTierCreate(BaseModel):
    program_id: int
    tier_name: str
    min_reward: float = 0.0
    max_reward: float | None = None
    currency: str = "USD"
    requirements: str | None = None


class BountyTierOut(BaseModel):
    id: int
    program_id: int
    tier_name: str
    min_reward: float
    max_reward: float | None = None
    currency: str = "USD"
    requirements: str | None = None
    created_at: str | None = None


# ── ScopeDocument ──

class ScopeDocumentOut(BaseModel):
    id: int
    program_id: int
    original_url: str | None = None
    content_type: str | None = None
    summary: str | None = None
    hash: str | None = None
    assets_extracted: str | None = None
    changes_from_previous: str | None = None
    fetched_at: str | None = None
    created_at: str | None = None


# ── ProgramIntel ──

class ProgramIntelOut(BaseModel):
    id: int
    program_id: int
    ai_summary: str | None = None
    technologies_list: str | None = None
    recent_changes: str | None = None
    historical_bugs: str | None = None
    public_reports: str | None = None
    hypotheses: str | None = None
    interesting_endpoints: str | None = None
    notes: str | None = None
    pending_ideas: str | None = None
    score: float = 0.0
    priority: str = "medium"
    difficulty: str = "medium"
    estimated_competition: float = 0.5
    related_findings: str | None = None
    past_reports: str | None = None
    speed_rating: str = "average"
    best_vuln_types: str | None = None
    probability_of_success: float = 0.3
    recommended_approach: str | None = None
    last_analyzed_at: str | None = None
    updated_at: str | None = None


class ProgramIntelUpdate(BaseModel):
    ai_summary: str | None = None
    technologies_list: str | None = None
    recent_changes: str | None = None
    historical_bugs: str | None = None
    public_reports: str | None = None
    hypotheses: str | None = None
    interesting_endpoints: str | None = None
    notes: str | None = None
    pending_ideas: str | None = None
    score: float | None = None
    priority: str | None = None
    difficulty: str | None = None
    estimated_competition: float | None = None
    related_findings: str | None = None
    past_reports: str | None = None
    speed_rating: str | None = None
    best_vuln_types: str | None = None
    probability_of_success: float | None = None
    recommended_approach: str | None = None


# ── FinancialMetric ──

class FinancialMetricOut(BaseModel):
    id: int
    metric_type: str
    dimension: str | None = None
    value: float
    period: str | None = None
    recorded_at: str | None = None


class FinancialSummaryOut(BaseModel):
    total_collected: float = 0.0
    total_pending: float = 0.0
    total_estimated: float = 0.0
    usd_per_hour: float = 0.0
    usd_per_program: dict[str, float] = {}
    usd_per_platform: dict[str, float] = {}
    usd_per_vuln_type: dict[str, float] = {}
    weekly_earnings: float = 0.0
    monthly_earnings: float = 0.0
    best_program: str | None = None
    next_action: str | None = None


# ── Money Radar ──

class MoneyRadarProgramOut(BaseModel):
    id: int
    name: str
    platform: str
    program_url: str | None = None
    private: bool = False
    status: str = "active"
    orion_score: float = 0.0
    priority: str = "medium"
    max_reward: float | None = None
    min_reward: float | None = None
    reward_currency: str = "USD"
    total_reports: int = 0
    confirmed_reports: int = 0
    total_earned: float = 0.0
    competition: float = 0.5
    effort_hours: float = 1.0
    evh: float = 0.0  # Expected Value per Hour
    technologies_summary: str | None = None


class MoneyRadarOut(BaseModel):
    items: list[MoneyRadarProgramOut]
    total: int
    generated_at: str


# ── ROI Summary ──

class ROISummaryOut(BaseModel):
    total_earned: float = 0.0
    total_pending: float = 0.0
    total_spent_hours: float = 0.0
    usd_per_hour: float = 0.0
    usd_per_hour_rating: str = "N/A"
    weekly_earnings: float = 0.0
    monthly_earnings: float = 0.0
    best_program: str | None = None
    best_program_earned: float = 0.0
    best_platform: str | None = None
    best_platform_earned: float = 0.0
    best_vuln_type: str | None = None
    best_vuln_type_earned: float = 0.0
    acceptance_rate: float = 0.0
    avg_response_time_days: float = 0.0
    report_count: int = 0


# ── Memory Pattern ──

class MemoryPatternCreate(BaseModel):
    category: str
    observation: str
    context: str | None = None
    confidence: float = 0.5
    tags: str | None = None
    source_program_id: int | None = None


class MemoryPatternOut(BaseModel):
    id: int
    category: str
    observation: str
    context: str | None = None
    confidence: float = 0.5
    evidence_count: int = 1
    tags: str | None = None
    source_program_id: int | None = None
    created_at: str | None = None


class MemoryPatternListOut(BaseModel):
    items: list[MemoryPatternOut]
    total: int


# ── Report Priority ──

class ReportPriorityOut(BaseModel):
    id: int
    report_id: int
    report_title: str = ""
    report_status: str = "draft"
    program: str = ""
    vulnerability: str = ""
    estimated_reward: float = 0.0
    confidence_score: float = 0.5
    acceptance_probability: float = 0.5
    expected_value: float = 0.0
    priority_score: float = 0.0
    priority_rank: int | None = None
    time_to_submit: str | None = None
    reasoning: str | None = None
    last_evaluated: str | None = None


class ReportPriorityListOut(BaseModel):
    items: list[ReportPriorityOut]
    total: int


# ── Opportunity Planner ──

class OpportunityPlanOut(BaseModel):
    program_id: int
    program_name: str
    platform: str
    orion_score: float

    where_to_start: str
    endpoints_to_review: list[str]
    recommended_techniques: list[str]
    best_vuln_types: list[str]
    estimated_time_hours: float
    expected_return_min: float
    expected_return_max: float
    expected_value_per_hour: float
    checklist: list[str]
    generated_at: str
