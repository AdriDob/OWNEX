import ast
import json
import logging

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    verification_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


SCAN_STATUS = (
    "pending",
    "running",
    "completed",
    "failed",
    "timeout",
)


class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False, index=True)

    domain = Column(String, nullable=True)

    active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    path = Column(
        String,
        nullable=False,
        default="/",
    )

    method = Column(
        String,
        nullable=False,
        default="GET",
    )

    # JSON metadata / labels / scoring cache
    params = Column(
        Text,
        nullable=True,
    )

    discovered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    hypothesis_id = Column(
        String,
        nullable=True,
    )

    # Autonomous scanning fields
    last_scanned = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    scan_count = Column(
        Integer,
        default=0,
        nullable=False,
    )

    @property
    def parsed_params(self) -> dict:
        if not self.params:
            return {}
        try:
            return json.loads(self.params)
        except (json.JSONDecodeError, ValueError):
            try:
                return ast.literal_eval(self.params)
            except (ValueError, SyntaxError):
                logging.getLogger("cateye.models").warning(f"Could not parse params for endpoint {self.id}")
                return {}


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    endpoint_id = Column(
        Integer,
        ForeignKey("endpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(
        String,
        nullable=False,
    )

    severity = Column(
        String,
        nullable=True,
        default="medium",
    )

    description = Column(
        Text,
        nullable=True,
    )

    status = Column(
        String,
        nullable=False,
        default="open",
        server_default="open",
    )

    vulnerability_type = Column(String, nullable=True, default="unknown")

    notes = Column(Text, nullable=True, default="")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class MemoryRecord(Base):
    __tablename__ = "memory_records"

    id = Column(Integer, primary_key=True, index=True)

    category = Column(
        String,
        nullable=False,
        index=True,
    )

    key = Column(
        String,
        nullable=False,
        index=True,
    )

    details = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Verdict(Base):
    """Stores validation loop results: confirmed/rejected/inconclusive status."""

    __tablename__ = "verdicts"

    id = Column(Integer, primary_key=True, index=True)

    hot_path_id = Column(String, nullable=False, index=True)

    endpoint_id = Column(
        Integer,
        ForeignKey("endpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # confirmed | rejected | inconclusive
    status = Column(String, nullable=False, index=True)

    # confidence score 0-1
    confidence = Column(
        String,  # JSON serialized float breakdown
        nullable=True,
    )

    reproducibility_score = Column(
        String,  # Consistency across attempts
        nullable=True,
    )

    # JSON: passed_rules, failed_rules, details
    validation_report = Column(Text, nullable=True)

    # JSON: breakdown of confidence calculation
    confidence_details = Column(Text, nullable=True)

    # Comma-separated evidence_ids or JSON array
    evidence_links = Column(Text, nullable=True)

    reason = Column(Text, nullable=True)

    retry_count = Column(Integer, default=3)

    uncertainty_level = Column(String, nullable=True, default="unknown")
    missing_verifications = Column(Text, nullable=True)
    alternative_explanations = Column(Text, nullable=True)
    next_best_test = Column(Text, nullable=True)
    vulnerability_type = Column(String, nullable=True, default="unknown")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Evidence(Base):
    """Stores captured request/response pairs and diffs from validation attempts."""

    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)

    verdict_id = Column(
        Integer,
        ForeignKey("verdicts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    endpoint_id = Column(
        Integer,
        ForeignKey("endpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # attempt_1, attempt_2, etc
    attempt_label = Column(String, nullable=False)

    # Request context
    request_url = Column(String, nullable=False)
    request_method = Column(String, default="GET")
    request_headers = Column(Text, nullable=True)  # JSON
    request_params = Column(Text, nullable=True)  # JSON
    request_body = Column(Text, nullable=True)
    auth_label = Column(String, nullable=True)  # "user_a", "user_b", "anonymous"

    # Response
    response_status = Column(Integer, nullable=False)
    response_headers = Column(Text, nullable=True)  # JSON
    response_body = Column(Text, nullable=True)
    response_body_hash = Column(String, nullable=True)

    # Comparison metadata
    status_match = Column(String, default="unknown")  # boolean as string
    body_diff_ratio = Column(String, nullable=True)  # float as string
    sensitive_fields = Column(Text, nullable=True)  # JSON array
    consistent = Column(String, default="true")  # boolean

    # Replay instruction
    curl_command = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ValidationResult(Base):
    """Stores detailed comparison results from each attempt."""

    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)

    verdict_id = Column(
        Integer,
        ForeignKey("verdicts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    attempt = Column(Integer, nullable=False)

    # JSON: baseline & probe response metadata
    baseline_response = Column(Text, nullable=True)
    probe_response = Column(Text, nullable=True)

    # JSON: comparison details
    comparison_summary = Column(Text, nullable=True)

    # Rate limit / timeout flags
    has_rate_limit = Column(String, default="false")
    has_timeout = Column(String, default="false")

    # Pass/fail on rules
    rule_results = Column(Text, nullable=True)  # JSON

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    mode = Column(
        String,
        nullable=True,
        default="FAST",
    )

    status = Column(
        String,
        nullable=False,
        default="pending",
    )

    endpoint_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Store lightweight metadata only.
    # Never store huge raw scan blobs here.
    outputs = Column(
        Text,
        nullable=True,
    )

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    finished_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )


class Favorite(Base):
    """User workspace favorites — metadata only, never modifies core data."""

    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String, nullable=False, index=True)  # target, endpoint, evidence, report, quick_win
    item_id = Column(Integer, nullable=False, index=True)
    label = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    """Operational task queue — organizational only, never modifies core data."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)  # pending, in_progress, waiting, completed
    priority = Column(String, nullable=True, default="medium")  # low, medium, high, critical
    linked_type = Column(String, nullable=True, index=True)  # target, evidence, report, quick_win, replay
    linked_id = Column(Integer, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)  # when the task is due
    calendar_event_id = Column(String, nullable=True)  # Outlook Graph event id when synced
    synced_to_calendar = Column(String, nullable=False, default="false")  # true/false — sync state
    todo_task_id = Column(String, nullable=True)  # Microsoft To Do task id when synced
    synced_to_todo = Column(String, nullable=False, default="false")  # true/false — To Do sync state
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Session(Base):
    """Persistent working context — tracks current investigation state."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True, default="Default Session")
    current_target_id = Column(Integer, nullable=True)
    current_investigation = Column(Text, nullable=True)  # JSON
    open_evidence_ids = Column(Text, nullable=True)  # JSON array
    current_replay_id = Column(Integer, nullable=True)
    current_report_draft = Column(Text, nullable=True)  # JSON
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Notification(Base):
    """Internal operational notifications — persisted from NotificationHub."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    message = Column(String, nullable=False)
    severity = Column(String, nullable=True, default="info")
    priority = Column(String, nullable=True, default="medium")
    linked_type = Column(String, nullable=True)
    linked_id = Column(Integer, nullable=True)
    dedup_key = Column(String, nullable=True)
    is_read = Column(String, nullable=False, default="false")
    delivered_via = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Device(Base):
    """Push notification device registrations."""

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    platform = Column(String, nullable=False, index=True)  # fcm, apns, webpush
    token = Column(String, nullable=False)
    name = Column(String, nullable=True)
    is_active = Column(String, nullable=False, default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DeliveryRecord(Base):
    """Notification delivery status per channel."""

    __tablename__ = "delivery_records"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String, nullable=False)  # desktop, web, mobile, email, fcm
    status = Column(String, nullable=False, default="pending")  # pending, sent, failed
    error = Column(Text, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QuickWin(Base):
    """Stores actionable quick wins associated with a target."""

    __tablename__ = "quick_wins"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String, nullable=False)
    impact = Column(String, nullable=False, default="medium")
    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class TargetIdentity(Base):
    """An identity/persona the investigator uses when interacting with a target."""

    __tablename__ = "target_identities"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label = Column(
        String,
        nullable=False,
        default="Default",
    )

    # login_form | bearer_token | api_key | cookie | basic_auth | none
    auth_type = Column(String, nullable=False, default="none")

    # AES-256-GCM encrypted JSON: {username?, password?, token?, api_key?, login_url?, login_params?}
    credentials_encrypted = Column(Text, nullable=True)

    # Nonce/IV for AES-GCM decryption
    credentials_nonce = Column(String, nullable=True)

    # Whether this is the primary identity for baseline comparisons
    is_baseline = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class TargetSession(Base):
    """Active authenticated session for a target identity."""

    __tablename__ = "target_sessions"

    id = Column(Integer, primary_key=True, index=True)

    identity_id = Column(
        Integer,
        ForeignKey("target_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )

    # AES-256-GCM encrypted access token
    token_encrypted = Column(Text, nullable=True)

    # AES-256-GCM encrypted JSON cookies object
    cookies_encrypted = Column(Text, nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=True)

    last_refresh_at = Column(DateTime(timezone=True), nullable=True)

    is_valid = Column(Boolean, default=True)

    failure_count = Column(Integer, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Investigation(Base):
    """Central workspace unit — ties together target, identities, and pipeline state."""

    __tablename__ = "investigations"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String, nullable=False)

    # active | paused | completed | archived
    status = Column(String, nullable=False, default="active", index=True)

    # JSON: {recon, hypotheses, validation, reporting} stage flags
    pipeline_state = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)

    # JSON array of tag strings
    tags = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class ValidationRun(Base):
    """A single execution of the validation pipeline against an endpoint."""

    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, index=True)

    investigation_id = Column(
        Integer,
        ForeignKey("investigations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    endpoint_id = Column(
        Integer,
        ForeignKey("endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    identity_baseline_id = Column(
        Integer,
        ForeignKey("target_identities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    identity_probe_id = Column(
        Integer,
        ForeignKey("target_identities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # running | completed | failed | aborted
    status = Column(String, nullable=False, default="running", index=True)

    verdict_id = Column(
        Integer,
        ForeignKey("verdicts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    finished_at = Column(DateTime(timezone=True), nullable=True)


class Report(Base):
    """Generated report with full history tracking."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    investigation_id = Column(
        Integer,
        ForeignKey("investigations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # hackerone_json | bugcrowd_html | markdown | html
    format = Column(String, nullable=False, default="markdown")

    content = Column(Text, nullable=True)

    # JSON array of finding IDs included in this report
    finding_ids = Column(Text, nullable=True)

    program = Column(String, nullable=True, index=True, default="")
    target = Column(String, nullable=True, index=True, default="")
    vulnerability = Column(String, nullable=True, default="")
    severity = Column(String, nullable=True, default="medium")
    status = Column(String, nullable=True, default="draft", index=True)

    estimated_reward = Column(Float, nullable=True, default=0.0)
    confirmed_reward = Column(Float, nullable=True, default=0.0)
    currency = Column(String, nullable=True, default="USD")

    evidence_count = Column(Integer, nullable=True, default=0)
    notes = Column(Text, nullable=True, default="")

    timeline = Column(Text, nullable=True, default="[]")
    attachments = Column(Text, nullable=True, default="[]")

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class SubmissionRecord(Base):
    """Tracks report submissions to external bug bounty platforms."""

    __tablename__ = "submission_records"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)
    external_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="submitted", index=True)
    extra_data = Column(Text, nullable=True, default="{}")
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    last_update = Column(DateTime(timezone=True), nullable=True)


class ReportVersion(Base):
    """Versioned snapshots of a report before finalization."""

    __tablename__ = "report_versions"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    content = Column(Text, nullable=True)
    summary = Column(String, nullable=True, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PipelineRun(Base):
    """Persistent autonomous pipeline execution record."""

    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    correlation_id = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    current_state = Column(
        String,
        nullable=False,
        default="pending",
        index=True,
    )

    state_history = Column(
        Text,
        nullable=True,
        default="[]",
    )

    quality_score = Column(
        Float,
        nullable=True,
        default=0.0,
    )

    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    max_retries = Column(
        Integer,
        nullable=False,
        default=3,
    )

    error_message = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )


class CATEYEConfig(Base):
    """Persistent key-value configuration store."""

    __tablename__ = "CATEYE_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class AIProviderConfig(Base):
    """Persistent AI provider configuration."""

    __tablename__ = "ai_provider_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class SystemStateRecord(Base):
    """Persistent snapshot of the last-known system state — survives restart."""

    __tablename__ = "system_state_records"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, nullable=False, default="BOOTING")
    services_json = Column(Text, nullable=True, default="[]")
    uptime_seconds = Column(Float, nullable=False, default=0.0)
    boot_start = Column(Float, nullable=False, default=0.0)
    last_state_change = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EventBusEntry(Base):
    """Persistent event bus history — survives restarts for audit/replay."""

    __tablename__ = "event_bus_history"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    priority = Column(String, nullable=False, default="medium")
    payload_json = Column(Text, nullable=True, default="{}")
    timestamp = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LedgerEntry(Base):
    """Persistent financial ledger entry — append-only, immutable transaction log."""

    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(String, unique=True, nullable=False, index=True)
    event = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="USD")
    description = Column(String, default="")
    source = Column(String, default="system")
    source_id = Column(String, default="")
    platform = Column(String, default="internal", index=True)
    timestamp = Column(String, nullable=False)
    metadata_json = Column(Text, default="{}")
    reconciled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Evolution Engine: Metrics & Knowledge ──


class MetricEvent(Base):
    """Raw metric event — append-only telemetry for the Evolution Engine.

    Every observable action in ORION produces one row: pipeline stages, tool
    executions, API calls, background jobs.  The Observe layer of the Evolution
    Engine persists these for later analysis, bottleneck detection, and ROI
    calculation.
    """

    __tablename__ = "metric_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Who / what produced this event
    module = Column(String, nullable=False, index=True)  # cateye, atlas, odyssey, hermes, core
    pipeline = Column(String, nullable=True, index=True)  # discover, recon, hypothesis, validate, report
    tool = Column(String, nullable=True, index=True)  # katana, httpx, nuclei, dalfox, …
    event_type = Column(String, nullable=False, index=True)  # pipeline_stage, tool_execution, api_call, background_job

    # Timing & resources
    duration_ms = Column(Float, nullable=True)
    cpu_percent = Column(Float, nullable=True)
    memory_mb = Column(Float, nullable=True)

    # Outcome
    status = Column(String, nullable=True, default="success")  # success, failed, timeout, skipped

    # Foreign keys for correlation
    target_id = Column(Integer, nullable=True, index=True)
    finding_id = Column(Integer, nullable=True, index=True)
    report_id = Column(Integer, nullable=True, index=True)

    # Flexible extra data (JSON)
    metadata_json = Column(Text, nullable=True)

    # Ingestion timestamp (when the engine recorded it, not when it happened)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class MetricRollup(Base):
    """Pre-aggregated metric rollups for fast querying.

    Generated periodically (hourly / daily) from MetricEvent rows so that
    dashboards, reports, and the Analyze layer don't need to scan raw events
    every time.
    """

    __tablename__ = "metric_rollups"

    id = Column(Integer, primary_key=True, index=True)
    granularity = Column(String, nullable=False, index=True)  # hourly, daily
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)

    # Grouping keys (same as MetricEvent)
    module = Column(String, nullable=False, index=True)
    pipeline = Column(String, nullable=True, index=True)
    tool = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=True, index=True)
    status = Column(String, nullable=True, index=True)

    # Aggregated timing
    count = Column(Integer, nullable=False, default=0)
    avg_duration_ms = Column(Float, nullable=True)
    p50_duration_ms = Column(Float, nullable=True)
    p95_duration_ms = Column(Float, nullable=True)
    min_duration_ms = Column(Float, nullable=True)
    max_duration_ms = Column(Float, nullable=True)
    total_duration_ms = Column(Float, nullable=True)

    # Aggregated resources
    avg_cpu_percent = Column(Float, nullable=True)
    avg_memory_mb = Column(Float, nullable=True)

    # Outcome counts
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)

    # Human-impact estimate (set by Analyze layer)
    total_human_hours_saved = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_metric_rollups_lookup", "granularity", "period_start", "module", "event_type"),)


class KnowledgeAsset(Base):
    """Persistent knowledge artifact produced by the Evolution Engine.

    Every cycle of Observe → Analyze → Hypothesis → Evidence Check → Asset
    produces one row.  Types: heuristic, pattern, rule, statistic, workflow,
    benchmark, template, finding_pattern, report_template, optimization,
    experiment, research, tool_config, playbook.

    Lifecycle: draft → hypothesis → validated → production → deprecated.
    """

    __tablename__ = "knowledge_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_type = Column(String, nullable=False, index=True)
    domain = Column(String, nullable=False, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Provenance
    source = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    source_confidence = Column(Float, nullable=False, default=0.0)

    # Asset payload
    content_json = Column(Text, nullable=True)
    evidence_json = Column(Text, nullable=True)

    # Impact & usage
    impact_score = Column(Float, nullable=True)
    hit_count = Column(Integer, nullable=False, default=0)
    reuse_count = Column(Integer, nullable=False, default=0)

    # Lifecycle: draft → hypothesis → validated → production → deprecated
    status = Column(String, nullable=False, default="draft", index=True)
    last_validated = Column(DateTime(timezone=True), nullable=True)
    validation_count = Column(Integer, nullable=False, default=0)

    # Evidence check fields
    observation_count = Column(Integer, nullable=True)
    evidence_summary = Column(Text, nullable=True)
    opportunity_cost_hours = Column(Float, nullable=True)
    implementation_effort = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)

    # Categorization
    tags_json = Column(Text, nullable=True)

    # Versioning
    version = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_knowledge_assets_lookup", "domain", "asset_type", "status"),)


class MobileApproval(Base):
    """Mobile approval requests for autonomous actions (bounties, reports, etc.)."""

    __tablename__ = "mobile_approvals"

    id = Column(Integer, primary_key=True, index=True)

    # Entity requiring approval
    entity_type = Column(String, nullable=False, index=True)  # "bounty", "report", "action"
    entity_id = Column(String, nullable=False, index=True)  # ID of the entity

    # Approval details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)  # Additional context (JSON)

    # Status: pending, approved, rejected
    status = Column(String, nullable=False, default="pending", index=True)

    # Priority: low, medium, high, critical
    priority = Column(String, nullable=False, default="medium")

    # Approval/rejection info
    approved_by = Column(String, nullable=True)  # User/device that approved
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_mobile_approvals_entity", "entity_type", "entity_id"),)


class WorkerCheckpoint(Base):
    """Persisted checkpoints for WorkerCore work items enabling resume capability."""

    __tablename__ = "worker_checkpoints"

    id = Column(Integer, primary_key=True, index=True)

    # Work item identification
    work_item_id = Column(String, nullable=False, index=True)
    work_item_title = Column(String, nullable=True)
    work_item_platform = Column(String, nullable=True)
    work_item_category = Column(String, nullable=True)

    # Checkpoint metadata
    phase = Column(
        String, nullable=False, index=True
    )  # discover, evaluate, select, prepare, execute, validate, deliver, learn
    checkpoint_data = Column(Text, nullable=True)  # JSON serialized checkpoint data
    phase_completed = Column(String, nullable=False, default="false")  # "true"/"false"

    # Error tracking
    error = Column(Text, nullable=True)

    # Retry tracking
    retry_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_worker_checkpoints_work_item", "work_item_id", "phase"),)


class WorkerAuditLog(Base):
    """Immutable audit trail for WorkerCore actions.

    Records every significant action with workflow_id, execution_id,
    trace_id, and full context for forensic analysis.
    """

    __tablename__ = "worker_audit_log"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    workflow_id = Column(String, nullable=False, index=True)
    execution_id = Column(String, nullable=False, index=True)
    trace_id = Column(String, nullable=True, index=True)
    work_item_id = Column(String, nullable=True, index=True)

    # Action details
    action = Column(String, nullable=False, index=True)  # discover, evaluate, execute, deliver, etc.
    phase = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, success, failed, blocked, rejected

    # Context
    details = Column(Text, nullable=True)  # JSON with full context
    error = Column(Text, nullable=True)
    cost_usd = Column(Float, nullable=True, default=0.0)

    # Human control
    requires_approval = Column(String, nullable=True, default="false")  # "true"/"false"
    approved_by = Column(String, nullable=True)  # "human" / "auto" / None
    approval_reason = Column(Text, nullable=True)

    # Autonomy
    autonomy_level = Column(String, nullable=True)
    would_block_if_restricted = Column(String, nullable=True, default="false")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_worker_audit_workflow", "workflow_id", "action"),
        Index("ix_worker_audit_execution", "execution_id", "phase"),
    )


# Backward-compatible alias — import as CATEYEConfig or RastroConfig
RastroConfig = CATEYEConfig
# OWNEX settings service imports the config model under the OWNEX name
OWNEXConfig = CATEYEConfig
