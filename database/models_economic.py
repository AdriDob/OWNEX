"""Economic Intelligence models — Program, Bounty, Scope, Intelligence Dossier."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from .db import Base


class Program(Base):
    """Bug bounty program — the core entity for economic intelligence."""

    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)  # hackerone, bugcrowd, intigriti, etc.
    platform_program_id = Column(String, nullable=True, index=True)  # external ID on the platform
    program_url = Column(String, nullable=True)
    private = Column(Boolean, default=False)
    status = Column(String, default="active", index=True)  # active, paused, closed, invitation_only

    # Core program data
    scope_summary = Column(Text, nullable=True)
    rewards_text = Column(Text, nullable=True)
    exclusions_text = Column(Text, nullable=True)
    policy_text = Column(Text, nullable=True)
    technologies = Column(Text, nullable=True)  # JSON array
    assets = Column(Text, nullable=True)  # JSON array of in-scope asset descriptors
    platform_data = Column(Text, nullable=True)  # JSON blob for platform-specific metadata

    # Scoring
    orion_score = Column(Float, default=0.0, index=True)
    priority = Column(String, default="medium", index=True)  # critical, high, medium, low

    # Scope tracking
    last_scope_fetch = Column(DateTime(timezone=True), nullable=True)
    last_scope_hash = Column(String, nullable=True)

    # Stats
    total_reports = Column(Integer, default=0)
    confirmed_reports = Column(Integer, default=0)
    total_earned = Column(Float, default=0.0)
    total_hours_spent = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BountyTier(Base):
    """Bounty reward tiers per program."""

    __tablename__ = "bounty_tiers"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)

    tier_name = Column(String, nullable=False)  # Critical, High, Medium, Low, Informational
    min_reward = Column(Float, default=0.0)
    max_reward = Column(Float, nullable=True)
    currency = Column(String, default="USD")
    requirements = Column(Text, nullable=True)  # What's needed for this tier (RCE, PoC, etc.)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScopeDocument(Base):
    """Indexed scope document — raw text + AI summary + change tracking."""

    __tablename__ = "scope_documents"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)

    original_url = Column(String, nullable=True)
    content_type = Column(String, nullable=True)  # html, pdf, text
    raw_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)  # AI-generated summary
    hash = Column(String, nullable=True, index=True)  # For change detection
    assets_extracted = Column(Text, nullable=True)  # JSON array of extracted assets
    changes_from_previous = Column(Text, nullable=True)  # JSON describing what changed

    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProgramIntel(Base):
    """Per-program intelligence dossier — maintained permanently."""

    __tablename__ = "program_intel"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    ai_summary = Column(Text, nullable=True)  # AI-generated program summary
    technologies_list = Column(Text, nullable=True)  # JSON array
    recent_changes = Column(Text, nullable=True)  # JSON array of {date, description}
    historical_bugs = Column(Text, nullable=True)  # JSON array of bugs found in this program
    public_reports = Column(Text, nullable=True)  # JSON array of public disclosures
    hypotheses = Column(Text, nullable=True)  # JSON array of existing hypotheses
    interesting_endpoints = Column(Text, nullable=True)  # JSON array
    notes = Column(Text, nullable=True)
    pending_ideas = Column(Text, nullable=True)  # JSON array
    score = Column(Float, default=0.0)
    priority = Column(String, default="medium")

    # Economic intelligence fields
    difficulty = Column(String, nullable=True, default="medium")  # easy, medium, hard, expert
    estimated_competition = Column(Float, nullable=True, default=0.5)  # 0.0-1.0
    related_findings = Column(Text, nullable=True)  # JSON array of finding IDs
    past_reports = Column(Text, nullable=True)  # JSON array of past report summaries
    speed_rating = Column(String, nullable=True, default="average")  # fast, average, slow
    best_vuln_types = Column(Text, nullable=True)  # JSON array of recommended vuln types
    probability_of_success = Column(Float, nullable=True, default=0.3)  # 0.0-1.0
    recommended_approach = Column(Text, nullable=True)  # Text

    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FinancialMetric(Base):
    """Time-series financial metrics for ROI Engine."""

    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_type = Column(String, nullable=False, index=True)  # usd_per_hour, usd_per_program, etc.
    dimension = Column(String, nullable=True, index=True)  # program name, platform, vuln type
    value = Column(Float, default=0.0)
    period = Column(String, nullable=True, index=True)  # weekly, monthly, all_time
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class MemoryPattern(Base):
    """Learned patterns from past bug hunting experience."""

    __tablename__ = "memory_patterns"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)  # platform, tech, vuln_type, company_type
    observation = Column(String, nullable=False)  # e.g. "Las APIs GraphQL dan mejores resultados"
    context = Column(Text, nullable=True)  # JSON: supporting data
    confidence = Column(Float, default=0.5)  # 0.0-1.0, increases with evidence
    evidence_count = Column(Integer, default=1)
    tags = Column(Text, nullable=True)  # JSON array for filtering
    source_program_id = Column(Integer, ForeignKey("programs.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReportPriority(Base):
    """Intelligent report queue — prioritised by expected economic value."""

    __tablename__ = "report_priorities"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    estimated_reward = Column(Float, default=0.0)
    confidence_score = Column(Float, default=0.5)  # 0.0-1.0
    acceptance_probability = Column(Float, default=0.5)  # 0.0-1.0
    expected_value = Column(Float, default=0.0)  # estimated_reward * acceptance_probability
    priority_score = Column(Float, default=0.0, index=True)
    priority_rank = Column(Integer, nullable=True)

    time_to_submit = Column(String, nullable=True)  # immediate, today, this_week, this_month
    reasoning = Column(Text, nullable=True)  # why this priority
    last_evaluated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PayoutRecord(Base):
    """Confirmed or pending payout from a bug bounty platform."""

    __tablename__ = "revenue_payouts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="USD")
    program = Column(String, nullable=True, index=True, default="")
    external_id = Column(String, nullable=True, index=True)
    submission_record_id = Column(Integer, ForeignKey("submission_records.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default="confirmed", index=True)  # pending, confirmed
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RevenueEvent(Base):
    """Audit log for revenue pipeline events."""

    __tablename__ = "revenue_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    payload = Column(Text, nullable=True, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AdapterPerformanceMetrics(Base):
    """Adapter performance tracking for 300+ income sources.

    Tracks recency, success rate and volume for automatic prioritization.
    Priority score = recency(40%) + success_rate(40%) + volume(20%)
    Half-life for recency: 30 days.

    Each adapter represents a income source: bug bounty platforms, AI training
    platforms, bounties, etc. Scores update dynamically as activity occurs.
    """

    __tablename__ = "adapter_performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    adapter_name = Column(String(128), unique=True, nullable=False, index=True)
    last_activity = Column(DateTime(timezone=True), nullable=False, default=None)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    total_requests = Column(Integer, nullable=False, default=0)
    avg_response_time_ms = Column(Integer, nullable=False, default=0)
    priority_score = Column(Float, nullable=False, default=0.5)
    is_active = Column(Boolean, nullable=False, default=True)
    category = Column(String(64), nullable=False, default="other")  # bounty, trading, sensor, other
    last_validated = Column(DateTime(timezone=True), nullable=False, default=None)
    meta_json = Column(Text, nullable=True)  # JSON string for adapter-specific data

    # Note: created_at/updated_at not included - table predates this model field
    # They are tracked separately if needed via application logic

    @property
    def recency_score(self) -> float:
        """Recency component (40% weight) with 30-day half-life.

        Decays from 1.0 to 0.0 over 30 days of inactivity.
        """
        if self.last_activity is None:
            return 0.0
        now = datetime.now()
        days_since = (now - self.last_activity).days + 1e-10
        # Exponential decay: half-life = 30 days
        return max(0.0, round(2 ** (-days_since / 30), 4))

    @property
    def success_rate(self) -> float:
        """Success rate component (40% weight)."""
        return round(self.success_count / max(self.total_requests, 1), 4)

    @property
    def volume_score(self) -> float:
        """Volume component (20% weight), saturated at 1000 requests."""
        return round(min(self.total_requests / 1000, 1.0), 4)

    @property
    def priority_score_calculated(self) -> float:
        """Final priority score: recency(40%) + success_rate(40%) + volume(20%)."""
        return round(
            self.recency_score * 0.4 + self.success_rate * 0.4 + self.volume_score * 0.2,
            4,
        )

    def update_activity(self, success: bool = True, response_time_ms: int | None = None) -> None:
        """Update metrics after a request/completed task.

        Args:
            success: Whether the request/task succeeded
            response_time_ms: Response time in milliseconds (optional)
        """
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        self.last_activity = now
        self.total_requests += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        if response_time_ms is not None:
            # Running average
            self.avg_response_time_ms = round(
                (self.avg_response_time_ms * (self.total_requests - 1) + response_time_ms) / self.total_requests
                if self.total_requests > 0
                else response_time_ms
            )
        # Recalculate priority score
        # (will be accessed via priority_score_calculated property)
