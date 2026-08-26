"""CATEYE/OWNEX Unified Contracts — Single Source of Truth for API contracts.

This module defines the canonical contracts for the entire system:
- API DTOs (Data Transfer Objects)
- Enums for all system states
- Categories and types
- Action definitions
- Income/metric definitions
- Notification contracts
- Authentication contracts
- Device identity
- Synchronization contracts
- Error contracts

All routers and components MUST import from here. No duplicate DTOs allowed.
"""

from .api import (
    ApiResponse,
    AuthToken,
    CrossDeviceEvent,
    CycleExecution,
    DeviceInfo,
    DeviceSyncState,
    DeviceType,
    EconomicMetric,
    HealthResponse,
    IncomeProjection,
    MobileNotificationRequest,
    MobileProvidersResponse,
    MobileProviderStatus,
    MobileQuickWin,
    MobileQuickWinsResponse,
    MobileStatus,
    Notification,
    NotificationLevel,
    NotificationType,
    Opportunity,
    OpportunityCategory,
    OpportunityFilter,
    OpportunityScore,
    OpportunityStatus,
    PaginatedResponse,
    PaymentStatus,
    PendingAction,
    Permission,
    RevenueBreakdown,
    SyncAcknowledgment,
    SyncActionType,
    SyncConflict,
    SyncEvent,
    SyncPriority,
    SyncQueueItem,
    SyncStatus,
    UserProfile,
    WatchApprovalRequest,
    WatchNotification,
    WatchNotificationLevel,
    WatchStatus,
    WorkCycle,
    WorkCycleStage,
    WorkCycleStatus,
    WorkCycleType,
)
from .base import (
    Artifact,
    ArtifactProtocol,
    Bundle,
    CacheProtocol,
    DependencyGraphProtocol,
    EventProtocol,
    InvalidationPolicy,
)

__all__ = [
    # Core DTOs
    "ApiResponse",
    "PaginatedResponse",
    "HealthResponse",
    # Opportunity DTOs
    "Opportunity",
    "OpportunityCategory",
    "OpportunityStatus",
    "OpportunityScore",
    "OpportunityFilter",
    # Work Cycle DTOs
    "WorkCycle",
    "WorkCycleType",
    "WorkCycleStatus",
    "WorkCycleStage",
    "CycleExecution",
    # Economic DTOs
    "EconomicMetric",
    "IncomeProjection",
    "RevenueBreakdown",
    "PaymentStatus",
    # Notification DTOs
    "Notification",
    "NotificationLevel",
    "NotificationType",
    "PendingAction",
    # Device/Sync DTOs
    "DeviceInfo",
    "DeviceType",
    "DeviceSyncState",
    "SyncEvent",
    "SyncStatus",
    "SyncActionType",
    "SyncPriority",
    "CrossDeviceEvent",
    "SyncAcknowledgment",
    "SyncConflict",
    "SyncQueueItem",
    # Mobile DTOs
    "MobileStatus",
    "MobileQuickWin",
    "MobileQuickWinsResponse",
    "MobileProviderStatus",
    "MobileProvidersResponse",
    "MobileNotificationRequest",
    # Watch DTOs
    "WatchStatus",
    "WatchNotification",
    "WatchNotificationLevel",
    "WatchApprovalRequest",
    # Authentication DTOs
    "AuthToken",
    "UserProfile",
    "Permission",
    # Base contracts
    "Artifact",
    "ArtifactProtocol",
    "Bundle",
    "CacheProtocol",
    "DependencyGraphProtocol",
    "EventProtocol",
    "InvalidationPolicy",
]
