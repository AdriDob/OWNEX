"""Event Types — standardized event type constants and payload schemas.

Every event in the system follows this structure:

.. code-block:: python

    {
        "correlation_id": "uuid",
        "event_type": "domain:action:status",
        "source": "module_name",
        "timestamp": 1234567890.0,
        "payload": { ... },
        "duration_ms": 150.0,        # optional
        "user": "user@example.com",  # optional
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

# ── Event type constants ────────────────────────────────────────


class Events:
    """Centralized event type constants, grouped by domain."""

    # ── System lifecycle ────────────────────────────────────────
    SYSTEM_BOOT_STARTING = "system:boot:starting"
    SYSTEM_BOOT_COMPLETE = "system:boot:complete"
    SYSTEM_READY = "system:ready"
    SYSTEM_ERROR = "system:error"
    SYSTEM_DEGRADED = "system:degraded"
    SYSTEM_ALERT = "system:alert"
    HEALTH_SCORE_UPDATED = "health_score:updated"

    # ── Findings pipeline ───────────────────────────────────────
    FINDING_CREATED = "finding:created"
    FINDING_STATUS_CHANGED = "finding:status_changed"
    FINDING_CONFIRMED = "finding:confirmed"

    # ── Report pipeline ─────────────────────────────────────────
    REPORT_GENERATED = "report:generated"
    REPORT_ACCEPTED = "report:accepted"
    REPORT_REJECTED = "report:rejected"

    # ── Financial pipeline ──────────────────────────────────────
    FINANCIAL_CANDIDATE = "financial:candidate"  # finding confirmed → possible income
    INVOICE_REQUESTED = "invoice:requested"  # system requests an invoice
    INVOICE_CREATED = "invoice:created"  # ARCA created the invoice
    INVOICE_APPROVED = "invoice:approved"  # invoice approved for sending
    PAYOUT_RECEIVED = "financial:payout_received"
    PAYOUT_CONFIRMED = "financial:payout_confirmed"

    # ── Notification pipeline ──────────────────────────────────
    NOTIFICATION_REQUESTED = "notification:requested"  # any module needs to notify
    NOTIFICATION_SENT = "notification:sent"  # notification was dispatched
    EMAIL_SENT = "outlook:email:sent"

    # ── COPILOT decisions ───────────────────────────────────────
    COPILOT_ANALYSIS_COMPLETED = "copilot:analysis:completed"
    COPILOT_PLAN_CREATED = "copilot:plan:created"
    COPILOT_PLAN_EXECUTED = "copilot:plan:executed"
    COPILOT_REVIEW_COMPLETED = "copilot:review:completed"
    COPILOT_AUDIT_COMPLETED = "copilot:audit:completed"
    COPILOT_RECOMMENDATION = "copilot:recommendation"
    COPILOT_DECISION = "copilot:decision"  # Decision Engine output
    COPILOT_HEARTBEAT = "copilot:heartbeat"

    # ── ARCA (tax) ─────────────────────────────────────────────
    ARCA_CUIT_VALIDATED = "arca:cuit:validated"
    ARCA_INVOICE_CREATED = "arca:invoice:created"

    # ── Target / Discovery ─────────────────────────────────────
    TARGET_CREATED = "target:created"
    DISCOVERY_COMPLETED = "discovery:completed"
    DISCOVERY_PROGRAM_NEW = "discovery:program:new"
    DISCOVERY_PROGRAM_UPDATED = "discovery:program:updated"
    DISCOVERY_PROGRAM_REMOVED = "discovery:program:removed"
    OPPORTUNITY_FOUND = "opportunity:found"
    OPPORTUNITY_UPDATED = "opportunity:updated"
    QUICK_WIN_DETECTED = "quick_win:detected"

    # ── Recovery ────────────────────────────────────────────────
    RECOVERY_STARTED = "recovery:started"
    RECOVERY_SUCCESS = "recovery:success"
    RECOVERY_FAILED = "recovery:failed"

    # ── Auto optimization ──────────────────────────────────────
    AUTO_OPTIMIZATION_APPLIED = "auto_optimization:applied"
    ANOMALY_DETECTED = "anomaly:detected"

    # ── Scheduler ──────────────────────────────────────────────
    SCHEDULER_JOB_DUE = "scheduler:job_due"

    # ── Execution Platform ────────────────────────────────────
    EXECUTION_WORKFLOW_CREATED = "execution:workflow:created"
    EXECUTION_WORKFLOW_STARTED = "execution:workflow:started"
    EXECUTION_WORKFLOW_COMPLETED = "execution:workflow:completed"
    EXECUTION_WORKFLOW_FAILED = "execution:workflow:failed"
    EXECUTION_WORKFLOW_CANCELLED = "execution:workflow:cancelled"
    EXECUTION_STARTED = "execution:started"
    EXECUTION_PAUSED = "execution:paused"
    EXECUTION_RESUMED = "execution:resumed"
    EXECUTION_COMPLETED = "execution:completed"
    EXECUTION_FAILED = "execution:failed"
    EXECUTION_CANCELLED = "execution:cancelled"
    EXECUTION_NODE_STARTED = "execution:node:started"
    EXECUTION_NODE_COMPLETED = "execution:node:completed"
    EXECUTION_NODE_FAILED = "execution:node:failed"
    EXECUTION_NODE_RETRYING = "execution:node:retrying"
    EXECUTION_APPROVAL_REQUESTED = "execution:approval:requested"
    EXECUTION_APPROVAL_APPROVED = "execution:approval:approved"
    EXECUTION_APPROVAL_REJECTED = "execution:approval:rejected"
    EXECUTION_APPROVAL_EXPIRED = "execution:approval:expired"
    EXECUTION_CHECKPOINT_SAVED = "execution:checkpoint:saved"
    EXECUTION_CHECKPOINT_RESTORED = "execution:checkpoint:restored"
    EXECUTION_ROLLBACK_STARTED = "execution:rollback:started"
    EXECUTION_ROLLBACK_COMPLETED = "execution:rollback:completed"
    EXECUTION_INTENT_EXPRESSED = "execution:intent:expressed"
    EXECUTION_INTENT_DESIGNED = "execution:intent:designed"
    EXECUTION_INTENT_VALIDATED = "execution:intent:validated"
    EXECUTION_INTENT_COMPILED = "execution:intent:compiled"
    EXECUTION_INTENT_EXECUTING = "execution:intent:executing"
    EXECUTION_INTENT_COMPLETED = "execution:intent:completed"
    EXECUTION_INTENT_FAILED = "execution:intent:failed"
    EXECUTION_INTENT_REJECTED = "execution:intent:rejected"
    EXECUTION_METRICS_COLLECTED = "execution:metrics:collected"
    EXECUTION_VALIDATION_STARTED = "execution:validation:started"
    EXECUTION_VALIDATION_COMPLETED = "execution:validation:completed"
    EXECUTION_VALIDATION_FAILED = "execution:validation:failed"
    EXECUTION_PLAN_CREATED = "execution:plan:created"
    EXECUTION_JOURNAL_ENTRY = "execution:journal:entry"

    # ── MERLIN Agent ────────────────────────────────────────
    HERMES_ACTION_REQUESTED = "hermes:action:requested"
    HERMES_ACTION_APPROVED = "hermes:action:approved"
    HERMES_ACTION_STARTED = "hermes:action:started"
    HERMES_ACTION_COMPLETED = "hermes:action:completed"
    HERMES_ACTION_FAILED = "hermes:action:failed"
    HERMES_PERMISSION_REQUIRED = "hermes:permission:required"
    HERMES_SECURITY_BLOCKED = "hermes:security:blocked"

    # ── F1 Assistant / CLI ─────────────────────────────────────
    F1_DAILY_BRIEFING = "f1:daily_briefing"
    F1_STATUS = "f1:status"
    F1_ALERT = "f1:alert"
    F1_QUESTION = "f1:question"
    CLI_COMMAND_EXECUTED = "cli:command:executed"
    NOTIFICATION_SMART = "notification:smart"

    # ── Revenue Pipeline ──────────────────────────────────────
    REVENUE_REPORT_SUBMITTED = "revenue:report_submitted"
    REVENUE_SUBMISSION_FAILED = "revenue:submission_failed"
    REVENUE_STATUS_CHANGED = "revenue:status_changed"
    REVENUE_SYNC_COMPLETED = "revenue:sync_completed"
    REVENUE_SYNC_FAILED = "revenue:sync_failed"
    REVENUE_PAYOUT_RECORDED = "revenue:payout_recorded"

    # ── Command System ─────────────────────────────────────────
    COMMAND_EXECUTED = "command:executed"
    COMMAND_FAILED = "command:failed"
    COMMAND_REJECTED = "command:rejected"

    # ── Market Intelligence ──────────────────────────────────────
    INTEL_SIGNAL_DETECTED = "intel:signal:detected"
    INTEL_OPPORTUNITY_ASSESSED = "intel:opportunity:assessed"
    INTEL_BRIEF_GENERATED = "intel:brief:generated"
    INTEL_SOURCE_UPDATED = "intel:source:updated"

    # ── Report Acceptance Optimizer ────────────────────────────
    ACCEPTANCE_OUTCOME_RECORDED = "acceptance:outcome:recorded"
    ACCEPTANCE_WEIGHTS_ADAPTED = "acceptance:weights:adapted"
    ACCEPTANCE_PREDICTION_MADE = "acceptance:prediction:made"

    # ── Auto-Submit Pipeline ──────────────────────────────────
    AUTO_SUBMIT_EXECUTED = "auto_submit:executed"
    AUTO_SUBMIT_FAILED = "auto_submit:failed"
    AUTO_SUBMIT_QUEUED = "auto_submit:queued"

    # ── Report Optimizer ─────────────────────────────────────
    REPORT_OPTIMIZED = "report:optimized"

    # ── AI Router ──────────────────────────────────────────────────
    AI_ROUTER_SWITCH_REQUESTED = "ai:router:switch_requested"
    AI_ROUTER_SWITCHED = "ai:router:switched"
    AI_ROUTER_SWITCH_FAILED = "ai:router:switch_failed"
    AI_ROUTER_FALLBACK_TRIGGERED = "ai:router:fallback_triggered"
    AI_ROUTER_PROVIDER_FAILED = "ai:router:provider_failed"

    # ── Bug Bounty Integrations ──────────────────────────────────
    HACKERONE_HACKTIVITY_FETCHED = "hackerone:hacktivity:fetched"
    HACKERONE_SCOPES_FETCHED = "hackerone:scopes:fetched"

    # ── AI Bounty Auto-Hunter ──────────────────────────────────
    AI_BOUNTY_CHALLENGE_DETECTED = "ai_bounty:challenge:detected"
    AI_BOUNTY_CHALLENGE_SCANNED = "ai_bounty:challenge:scanned"
    AI_BOUNTY_REPORT_READY = "ai_bounty:report:ready"
    AI_BOUNTY_OPPORTUNITY_ASSESSED = "ai_bounty:opportunity:assessed"

    # ── OSINT ────────────────────────────────────────────────────
    OSINT_DNS_RESOLVED = "osint:dns:resolved"
    OSINT_SUBDOMAIN_DISCOVERED = "osint:subdomain:discovered"

    # ── Investment / Revenue Multiplier ────────────────────────────
    INVESTMENT_CAPITAL_DEPLOYED = "investment:capital_deployed"
    INVESTMENT_TRADE_COMPLETED = "investment:trade_completed"
    INVESTMENT_STRATEGY_PAUSED = "investment:strategy:paused"
    INVESTMENT_STRATEGY_RESUMED = "investment:strategy:resumed"
    INVESTMENT_GLOBAL_PAUSED = "investment:global:paused"
    INVESTMENT_GLOBAL_RESUMED = "investment:global:resumed"
    INVESTMENT_PAYOUT_ALLOCATED = "investment:payout:allocated"
    INVESTMENT_DRAWDOWN_ALERT = "investment:drawdown:alert"

    # ── All event types for introspection ───────────────────────
    ALL = frozenset(
        {
            SYSTEM_BOOT_STARTING,
            SYSTEM_BOOT_COMPLETE,
            SYSTEM_READY,
            SYSTEM_ERROR,
            SYSTEM_DEGRADED,
            SYSTEM_ALERT,
            HEALTH_SCORE_UPDATED,
            FINDING_CREATED,
            FINDING_STATUS_CHANGED,
            FINDING_CONFIRMED,
            REPORT_GENERATED,
            REPORT_ACCEPTED,
            REPORT_REJECTED,
            FINANCIAL_CANDIDATE,
            INVOICE_REQUESTED,
            INVOICE_CREATED,
            INVOICE_APPROVED,
            PAYOUT_RECEIVED,
            PAYOUT_CONFIRMED,
            NOTIFICATION_REQUESTED,
            NOTIFICATION_SENT,
            EMAIL_SENT,
            COPILOT_ANALYSIS_COMPLETED,
            COPILOT_PLAN_CREATED,
            COPILOT_PLAN_EXECUTED,
            COPILOT_REVIEW_COMPLETED,
            COPILOT_AUDIT_COMPLETED,
            COPILOT_RECOMMENDATION,
            COPILOT_DECISION,
            COPILOT_HEARTBEAT,
            ARCA_CUIT_VALIDATED,
            ARCA_INVOICE_CREATED,
            TARGET_CREATED,
            DISCOVERY_COMPLETED,
            OPPORTUNITY_FOUND,
            OPPORTUNITY_UPDATED,
            QUICK_WIN_DETECTED,
            RECOVERY_STARTED,
            RECOVERY_SUCCESS,
            RECOVERY_FAILED,
            AUTO_OPTIMIZATION_APPLIED,
            ANOMALY_DETECTED,
            SCHEDULER_JOB_DUE,
            EXECUTION_WORKFLOW_CREATED,
            EXECUTION_WORKFLOW_STARTED,
            EXECUTION_WORKFLOW_COMPLETED,
            EXECUTION_WORKFLOW_FAILED,
            EXECUTION_WORKFLOW_CANCELLED,
            EXECUTION_STARTED,
            EXECUTION_PAUSED,
            EXECUTION_RESUMED,
            EXECUTION_COMPLETED,
            EXECUTION_FAILED,
            EXECUTION_CANCELLED,
            EXECUTION_NODE_STARTED,
            EXECUTION_NODE_COMPLETED,
            EXECUTION_NODE_FAILED,
            EXECUTION_NODE_RETRYING,
            EXECUTION_APPROVAL_REQUESTED,
            EXECUTION_APPROVAL_APPROVED,
            EXECUTION_APPROVAL_REJECTED,
            EXECUTION_APPROVAL_EXPIRED,
            EXECUTION_CHECKPOINT_SAVED,
            EXECUTION_CHECKPOINT_RESTORED,
            EXECUTION_ROLLBACK_STARTED,
            EXECUTION_ROLLBACK_COMPLETED,
            EXECUTION_INTENT_EXPRESSED,
            EXECUTION_INTENT_DESIGNED,
            EXECUTION_INTENT_VALIDATED,
            EXECUTION_INTENT_COMPILED,
            EXECUTION_INTENT_EXECUTING,
            EXECUTION_INTENT_COMPLETED,
            EXECUTION_INTENT_FAILED,
            EXECUTION_INTENT_REJECTED,
            EXECUTION_METRICS_COLLECTED,
            EXECUTION_VALIDATION_STARTED,
            EXECUTION_VALIDATION_COMPLETED,
            EXECUTION_VALIDATION_FAILED,
            EXECUTION_PLAN_CREATED,
            EXECUTION_JOURNAL_ENTRY,
            F1_DAILY_BRIEFING,
            F1_STATUS,
            F1_ALERT,
            F1_QUESTION,
            CLI_COMMAND_EXECUTED,
            NOTIFICATION_SMART,
            REVENUE_REPORT_SUBMITTED,
            REVENUE_SUBMISSION_FAILED,
            REVENUE_STATUS_CHANGED,
            REVENUE_SYNC_COMPLETED,
            REVENUE_SYNC_FAILED,
            REVENUE_PAYOUT_RECORDED,
            HERMES_ACTION_REQUESTED,
            HERMES_ACTION_APPROVED,
            HERMES_ACTION_STARTED,
            HERMES_ACTION_COMPLETED,
            HERMES_ACTION_FAILED,
            HERMES_PERMISSION_REQUIRED,
            HERMES_SECURITY_BLOCKED,
            COMMAND_EXECUTED,
            COMMAND_FAILED,
            COMMAND_REJECTED,
            INTEL_SIGNAL_DETECTED,
            INTEL_OPPORTUNITY_ASSESSED,
            INTEL_BRIEF_GENERATED,
            INTEL_SOURCE_UPDATED,
            INVESTMENT_CAPITAL_DEPLOYED,
            INVESTMENT_TRADE_COMPLETED,
            INVESTMENT_STRATEGY_PAUSED,
            INVESTMENT_STRATEGY_RESUMED,
            INVESTMENT_GLOBAL_PAUSED,
            INVESTMENT_GLOBAL_RESUMED,
            INVESTMENT_PAYOUT_ALLOCATED,
            INVESTMENT_DRAWDOWN_ALERT,
            ACCEPTANCE_OUTCOME_RECORDED,
            ACCEPTANCE_WEIGHTS_ADAPTED,
            ACCEPTANCE_PREDICTION_MADE,
            AI_ROUTER_SWITCH_REQUESTED,
            AI_ROUTER_SWITCHED,
            AI_ROUTER_SWITCH_FAILED,
            AI_ROUTER_FALLBACK_TRIGGERED,
            AI_ROUTER_PROVIDER_FAILED,
            HACKERONE_HACKTIVITY_FETCHED,
            HACKERONE_SCOPES_FETCHED,
            AI_BOUNTY_CHALLENGE_DETECTED,
            AI_BOUNTY_CHALLENGE_SCANNED,
            AI_BOUNTY_REPORT_READY,
            AI_BOUNTY_OPPORTUNITY_ASSESSED,
            OSINT_DNS_RESOLVED,
            OSINT_SUBDOMAIN_DISCOVERED,
        }
    )


# ── Correlation ID ──────────────────────────────────────────────


@dataclass
class CorrelationId:
    """Value object for a correlation ID that traces an end-to-end workflow."""

    value: str = field(default_factory=lambda: uuid4().hex)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"CorrelationId({self.value})"


# ── Event envelope ──────────────────────────────────────────────


@dataclass
class EventEnvelope:
    """Standard envelope for every event in the system."""

    event_type: str
    correlation_id: str
    source: str
    timestamp: float
    payload: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None
    user: str | None = None

    def to_dict(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "source": self.source,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }
        if self.duration_ms is not None:
            base["duration_ms"] = self.duration_ms
        if self.user is not None:
            base["user"] = self.user
        return base

    @classmethod
    def create(
        cls,
        event_type: str,
        source: str,
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        user: str | None = None,
    ) -> EventEnvelope:
        import time

        return cls(
            event_type=event_type,
            correlation_id=correlation_id or CorrelationId().value,
            source=source,
            timestamp=time.time(),
            payload=payload or {},
            duration_ms=duration_ms,
            user=user,
        )


# ── COPILOT Decision envelope ───────────────────────────────────


@dataclass
class Decision:
    """Standard decision output from COPILOT Decision Engine.

    Every decision includes priority, reason, confidence, recommended actions,
    estimated ROI, and whether human approval is required.
    """

    event_type: str  # what triggered this decision
    correlation_id: str
    priority: str  # critical / high / medium / low
    reason: str  # why the decision was made
    confidence: float  # 0.0 – 1.0
    actions: list[dict[str, Any]]  # recommended actions
    eta: str | None = None  # estimated time to complete
    roi: str | None = None  # estimated return
    human_required: bool = False
    source: str = "copilot"
    timestamp: float = 0.0
    duration_ms: float | None = None
    user: str | None = None

    def __post_init__(self) -> None:
        import time

        if not self.timestamp:
            self.timestamp = time.time()

    def to_envelope(self) -> EventEnvelope:
        return EventEnvelope(
            event_type=self.event_type,
            correlation_id=self.correlation_id,
            source=self.source,
            timestamp=self.timestamp,
            payload={
                "decision_event": self.event_type,
                "priority": self.priority,
                "reason": self.reason,
                "confidence": self.confidence,
                "actions": self.actions,
                "eta": self.eta,
                "roi": self.roi,
                "human_required": self.human_required,
            },
            duration_ms=self.duration_ms,
            user=self.user,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "priority": self.priority,
            "reason": self.reason,
            "confidence": self.confidence,
            "actions": self.actions,
            "eta": self.eta,
            "roi": self.roi,
            "human_required": self.human_required,
            "source": self.source,
            "timestamp": self.timestamp,
        }
