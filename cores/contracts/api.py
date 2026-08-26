"""Unified API Contracts — Single Source of Truth for all API DTOs.

This module defines the canonical contracts for the entire system.
All routers and components MUST import from here. No duplicate DTOs allowed.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# ============================================================================
# CORE DTOs
# ============================================================================


class ApiResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool = True
    message: str | None = None
    data: Any | None = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class HealthResponse(BaseModel):
    """System health response."""

    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    uptime_seconds: float
    components: dict[str, Any]
    checks: dict[str, bool]


# ============================================================================
# OPPORTUNITY DTOs
# ============================================================================


class OpportunityCategory(StrEnum):
    """Canonical opportunity categories."""

    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    AI_TRAINING = "ai_training"
    FREELANCE = "freelance"
    DATA_ANNOTATION = "data_annotation"
    QA_TESTING = "qa_testing"
    SECURITY_RESEARCH = "security_research"
    OPEN_SOURCE = "open_source"
    COMPETITION = "competition"
    OTHER = "other"


class OpportunityStatus(StrEnum):
    """Canonical opportunity status."""

    DISCOVERED = "discovered"
    ANALYZED = "analyzed"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Opportunity(BaseModel):
    """Canonical opportunity model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    category: OpportunityCategory
    status: OpportunityStatus = OpportunityStatus.DISCOVERED
    platform: str
    expected_value_usd: float | None = None
    human_time_hours: float | None = None
    automation_ratio: float = 0.0
    difficulty: float = 0.5  # 0-1 scale
    confidence: float = 0.5  # 0-1 scale
    probability: float = 0.5  # 0-1 scale
    barrier_level: str = "medium"
    risk_level: str = "medium"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpportunityScore(BaseModel):
    """Opportunity scoring metrics."""

    opportunity_id: str
    expected_value: float
    human_hourly_value: float
    effective_value: float
    confidence_score: float
    acceptance_probability: float
    risk_score: float
    time_to_payment_days: float | None = None
    overall_score: float


class OpportunityFilter(BaseModel):
    """Opportunity filter parameters."""

    categories: list[OpportunityCategory] | None = None
    platforms: list[str] | None = None
    status: list[OpportunityStatus] | None = None
    min_expected_value: float | None = None
    max_expected_value: float | None = None
    min_confidence: float | None = None
    max_difficulty: float | None = None
    barrier_levels: list[str] | None = None
    risk_levels: list[str] | None = None
    tags: list[str] | None = None


# ============================================================================
# WORK CYCLE DTOs
# ============================================================================


class WorkCycleType(StrEnum):
    """Canonical work cycle types."""

    SECURITY = "security"  # Rastro bug bounty
    FORGE = "forge"  # Dev bounty
    PULSE = "pulse"  # AI work
    VAULT = "vault"  # Wealth management
    ATLAS = "atlas"  # System monitoring
    DIRECT_WORK = "direct_work"  # Direct income tasks


class WorkCycleStatus(StrEnum):
    """Canonical work cycle status."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkCycleStage(StrEnum):
    """Canonical work cycle stages."""

    DISCOVERY = "discovery"
    RECON = "recon"
    HYPOTHESIS = "hypothesis"
    VALIDATION = "validation"
    EVIDENCE = "evidence"
    REPORT = "report"
    LEARNING = "learning"
    SUBMISSION = "submission"
    APPROVAL = "approval"
    PAYMENT = "payment"


class WorkCycle(BaseModel):
    """Canonical work cycle model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    cycle_type: WorkCycleType
    status: WorkCycleStatus = WorkCycleStatus.IDLE
    current_stage: WorkCycleStage | None = None
    target_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)


class CycleExecution(BaseModel):
    """Work cycle execution record."""

    cycle_id: str
    stage: WorkCycleStage
    started_at: datetime
    completed_at: datetime | None = None
    status: str
    output: dict[str, Any] | None = None
    error: str | None = None


# ============================================================================
# ECONOMIC DTOs
# ============================================================================


class PaymentStatus(StrEnum):
    """Canonical payment status."""

    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class EconomicMetric(BaseModel):
    """Economic metric."""

    name: str
    value: float
    unit: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncomeProjection(BaseModel):
    """Income projection."""

    optimistic_max_usd: float
    realistic_max_usd: float
    conservative_max_usd: float
    probability_distribution: dict[str, float]
    time_horizon_days: int
    confidence_level: float


class RevenueBreakdown(BaseModel):
    """Revenue breakdown by source."""

    total_expected: float
    total_pending: float
    total_paid: float
    by_source: dict[str, dict[str, float]]
    by_category: dict[str, dict[str, float]]
    by_status: dict[str, float]


# ============================================================================
# NOTIFICATION DTOs
# ============================================================================


class NotificationLevel(StrEnum):
    """Canonical notification levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class NotificationType(StrEnum):
    """Canonical notification types."""

    OPPORTUNITY = "opportunity"
    INCOME = "income"
    PAYMENT = "payment"
    DEADLINE = "deadline"
    SYSTEM = "system"
    SECURITY = "security"
    SYNC = "sync"
    ACTION_REQUIRED = "action_required"


class Notification(BaseModel):
    """Canonical notification model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    type: NotificationType
    requires_action: bool = False
    action_type: str | None = None
    action_id: str | None = None
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PendingAction(BaseModel):
    """Pending action requiring user approval."""

    action_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    workflow_id: str | None = None
    priority: str = "medium"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# DEVICE/SYNC DTOs
# ============================================================================


class DeviceType(StrEnum):
    """Canonical device types."""

    DESKTOP = "desktop"
    MOBILE = "mobile"
    WATCH = "watch"
    WEB = "web"


class SyncStatus(StrEnum):
    """Canonical sync status."""

    SYNCED = "synced"
    SYNCING = "syncing"
    OFFLINE = "offline"
    CONFLICT = "conflict"
    ERROR = "error"


class DeviceInfo(BaseModel):
    """Device information."""

    device_id: str = Field(default_factory=lambda: str(uuid4()))
    device_type: DeviceType
    device_name: str
    os_version: str | None = None
    app_version: str
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class SyncEvent(BaseModel):
    """Synchronization event."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    entity_type: str
    entity_id: str
    device_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: int
    state: dict[str, Any]
    status: SyncStatus = SyncStatus.SYNCED


# ============================================================================
# AUTHENTICATION DTOs
# ============================================================================


class AuthToken(BaseModel):
    """Authentication token."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
    issued_at: datetime = Field(default_factory=datetime.utcnow)


class UserProfile(BaseModel):
    """User profile."""

    user_id: str
    username: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime
    settings: dict[str, Any] = Field(default_factory=dict)


class Permission(BaseModel):
    """Permission."""

    permission_id: str
    name: str
    description: str | None = None
    resource: str
    action: str


# ============================================================================
# MOBILE DTOs
# ============================================================================


class MobileNotificationRequest(BaseModel):
    """Mobile notification request."""

    title: str
    message: str
    url: str | None = None
    type: str = "info"


class MobileStatus(BaseModel):
    """Mobile status snapshot."""

    findings_total: int
    findings_confirmed: int
    findings_pending: int
    targets_active: int
    scheduler_running: bool
    next_action: str | None = None


class MobileQuickWin(BaseModel):
    """Mobile quick win finding."""

    id: str
    title: str
    severity: str
    status: str
    target: str


class MobileQuickWinsResponse(BaseModel):
    """Mobile quick wins response."""

    quick_wins: list[MobileQuickWin]


class MobileProviderStatus(BaseModel):
    """Mobile AI provider status."""

    available: bool
    type: str
    error: str | None = None


class MobileProvidersResponse(BaseModel):
    """Mobile providers response."""

    providers: dict[str, MobileProviderStatus]
    total: int
    available: int


# ============================================================================
# WATCH DTOs
# ============================================================================


class WatchNotificationLevel(StrEnum):
    """Watch notification levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class WatchNotification(BaseModel):
    """Watch notification."""

    notification_id: str
    title: str
    message: str
    level: WatchNotificationLevel = WatchNotificationLevel.MEDIUM
    requires_action: bool = False
    action_type: str | None = None
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WatchApprovalRequest(BaseModel):
    """Watch approval request."""

    request_id: str
    title: str
    description: str
    workflow_id: str | None = None
    approved: bool | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WatchStatus(BaseModel):
    """Watch system status."""

    system_online: bool
    backend_online: bool
    sync_status: str
    pending_notifications: int
    pending_approvals: int
    daily_income_usd: float | None = None
    weekly_income_usd: float | None = None


# ============================================================================
# CROSS-DEVICE SYNC DTOs
# ============================================================================


class SyncActionType(StrEnum):
    """Cross-device sync action types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACKNOWLEDGE = "acknowledge"
    SYNC = "sync"


class SyncPriority(StrEnum):
    """Sync priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class CrossDeviceEvent(BaseModel):
    """Cross-device synchronization event."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: SyncActionType
    entity_type: str  # "opportunity", "notification", "finding", etc.
    entity_id: str
    source_device_id: str
    target_device_types: list[DeviceType]  # Which devices should receive this
    priority: SyncPriority = SyncPriority.NORMAL
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    state: dict[str, Any]
    version: int = 1
    expires_at: datetime | None = None
    requires_ack: bool = False
    ack_timeout_seconds: int = 300  # 5 minutes default


class SyncAcknowledgment(BaseModel):
    """Sync acknowledgment from device."""

    event_id: str
    device_id: str
    acknowledged_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool
    error: str | None = None


class SyncConflict(BaseModel):
    """Sync conflict record."""

    conflict_id: str = Field(default_factory=lambda: str(uuid4()))
    entity_type: str
    entity_id: str
    conflicting_events: list[CrossDeviceEvent]
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolution_strategy: str | None = None  # "source_wins", "target_wins", "manual", "merge"
    resolved_at: datetime | None = None
    resolved_by: str | None = None  # device_id or "system"


class SyncQueueItem(BaseModel):
    """Item in sync queue for offline support."""

    event: CrossDeviceEvent
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 5
    next_retry_at: datetime | None = None
    status: SyncStatus = SyncStatus.SYNCING


class DeviceSyncState(BaseModel):
    """Per-device sync state."""

    device_id: str
    device_type: DeviceType
    last_sync_time: datetime
    last_sync_version: int
    pending_events_count: int
    conflict_count: int
    status: SyncStatus
    capabilities: dict[str, bool] = Field(default_factory=dict)  # What this device can do
