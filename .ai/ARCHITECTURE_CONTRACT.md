# ARCHITECTURE CONTRACT — Unified API DTOs for Cross-Device Sync

**Fecha:** 2026-08-26  
**Estado:** DEFINED  
**Versión:** 1.0.0

---

## 0. PURPOSE

Definir la **Single Source of Truth (SSOT)** para todos los contratos API del sistema. Este documento establece los DTOs canónicos que deben usar:

- Backend routers (`api/routers/*`)
- Cores (`cores/*`)
- Frontend (`frontend/src/`)
- Mobile (`android/app/`)
- Watch (`android/wear/`)

**Regla de oro:** No se permiten DTOs duplicados. Todo debe importar desde `cores/contracts/`.

---

## 1. CORE DTOs

### 1.1 Standard Response Wrapper

```python
class ApiResponse(BaseModel):
    success: bool = True
    message: str | None = None
    data: Any | None = None
    error: str | None = None
    timestamp: datetime
```

### 1.2 Paginated Response

```python
class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
```

### 1.3 Health Response

```python
class HealthResponse(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    uptime_seconds: float
    components: dict[str, Any]
    checks: dict[str, bool]
```

---

## 2. OPPORTUNITY DTOs

### 2.1 Categories (Canonical Taxonomy)

```python
class OpportunityCategory(StrEnum):
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
```

### 2.2 Status Lifecycle

```python
class OpportunityStatus(StrEnum):
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
```

### 2.3 Opportunity Model

```python
class Opportunity(BaseModel):
    id: str
    title: str
    description: str
    category: OpportunityCategory
    status: OpportunityStatus
    platform: str
    expected_value_usd: float | None
    human_time_hours: float | None
    automation_ratio: float
    difficulty: float  # 0-1
    confidence: float  # 0-1
    probability: float  # 0-1
    barrier_level: str
    risk_level: str
    created_at: datetime
    updated_at: datetime
    deadline: datetime | None
    tags: list[str]
    metadata: dict[str, Any]
```

---

## 3. WORK CYCLE DTOs

### 3.1 Cycle Types

```python
class WorkCycleType(StrEnum):
    SECURITY = "security"  # Rastro bug bounty
    FORGE = "forge"  # Dev bounty
    PULSE = "pulse"  # AI work
    VAULT = "vault"  # Wealth management
    ATLAS = "atlas"  # System monitoring
    DIRECT_WORK = "direct_work"  # Direct income tasks
```

### 3.2 Cycle Status

```python
class WorkCycleStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### 3.3 Cycle Stages

```python
class WorkCycleStage(StrEnum):
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
```

---

## 4. ECONOMIC DTOs

### 4.1 Payment Status

```python
class PaymentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
```

### 4.2 Revenue Breakdown

```python
class RevenueBreakdown(BaseModel):
    total_expected: float
    total_pending: float
    total_paid: float
    by_source: dict[str, dict[str, float]]
    by_category: dict[str, dict[str, float]]
    by_status: dict[str, float]
```

---

## 5. NOTIFICATION DTOs

### 5.1 Notification Levels

```python
class NotificationLevel(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
```

### 5.2 Notification Types

```python
class NotificationType(StrEnum):
    OPPORTUNITY = "opportunity"
    INCOME = "income"
    PAYMENT = "payment"
    DEADLINE = "deadline"
    SYSTEM = "system"
    SECURITY = "security"
    SYNC = "sync"
    ACTION_REQUIRED = "action_required"
```

---

## 6. DEVICE/SYNC DTOs

### 6.1 Device Types

```python
class DeviceType(StrEnum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    WATCH = "watch"
    WEB = "web"
```

### 6.2 Sync Status

```python
class SyncStatus(StrEnum):
    SYNCED = "synced"
    SYNCING = "syncing"
    OFFLINE = "offline"
    CONFLICT = "conflict"
    ERROR = "error"
```

---

## 7. MOBILE DTOs (NEW)

### 7.1 Mobile Status Snapshot

```python
class MobileStatus(BaseModel):
    findings_total: int
    findings_confirmed: int
    findings_pending: int
    targets_active: int
    scheduler_running: bool
    next_action: str | None
```

### 7.2 Mobile Quick Win

```python
class MobileQuickWin(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    target: str
```

### 7.3 Mobile Provider Status

```python
class MobileProviderStatus(BaseModel):
    available: bool
    type: str
    error: str | None
```

---

## 8. WATCH DTOs (NEW)

### 8.1 Watch Notification Levels

```python
class WatchNotificationLevel(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

### 8.2 Watch Notification

```python
class WatchNotification(BaseModel):
    notification_id: str
    title: str
    message: str
    level: WatchNotificationLevel
    requires_action: bool
    action_type: str | None
    read: bool
    created_at: datetime
```

### 8.3 Watch Approval Request

```python
class WatchApprovalRequest(BaseModel):
    request_id: str
    title: str
    description: str
    workflow_id: str | None
    approved: bool | None
    created_at: datetime
```

### 8.4 Watch Status

```python
class WatchStatus(BaseModel):
    system_online: bool
    backend_online: bool
    sync_status: str
    pending_notifications: int
    pending_approvals: int
    daily_income_usd: float | None
    weekly_income_usd: float | None
```

---

## 9. CROSS-DEVICE SYNC DTOs (NEW)

### 9.1 Sync Action Types

```python
class SyncActionType(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACKNOWLEDGE = "acknowledge"
    SYNC = "sync"
```

### 9.2 Sync Priority

```python
class SyncPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
```

### 9.3 Cross-Device Event

```python
class CrossDeviceEvent(BaseModel):
    event_id: str
    action_type: SyncActionType
    entity_type: str  # "opportunity", "notification", "finding", etc.
    entity_id: str
    source_device_id: str
    target_device_types: list[DeviceType]
    priority: SyncPriority
    timestamp: datetime
    state: dict[str, Any]
    version: int
    expires_at: datetime | None
    requires_ack: bool
    ack_timeout_seconds: int
```

### 9.4 Sync Acknowledgment

```python
class SyncAcknowledgment(BaseModel):
    event_id: str
    device_id: str
    acknowledged_at: datetime
    success: bool
    error: str | None
```

### 9.5 Sync Conflict

```python
class SyncConflict(BaseModel):
    conflict_id: str
    entity_type: str
    entity_id: str
    conflicting_events: list[CrossDeviceEvent]
    detected_at: datetime
    resolution_strategy: str | None  # "source_wins", "target_wins", "manual", "merge"
    resolved_at: datetime | None
    resolved_by: str | None
```

### 9.6 Sync Queue Item (Offline Support)

```python
class SyncQueueItem(BaseModel):
    event: CrossDeviceEvent
    queued_at: datetime
    retry_count: int
    max_retries: int
    next_retry_at: datetime | None
    status: SyncStatus
```

### 9.7 Device Sync State

```python
class DeviceSyncState(BaseModel):
    device_id: str
    device_type: DeviceType
    last_sync_time: datetime
    last_sync_version: int
    pending_events_count: int
    conflict_count: int
    status: SyncStatus
    capabilities: dict[str, bool]  # What this device can do
```

---

## 10. MIGRATION PATH

### 10.1 Current State

- ✅ `cores/contracts/api.py` — Core DTOs exist
- ✅ `cores/contracts/__init__.py` — Exports defined
- ✅ Mobile DTOs added
- ✅ Watch DTOs added
- ✅ Cross-Device Sync DTOs added

### 10.2 Migration Tasks

**Phase 1: Backend Routers**
- [ ] Migrate `api/routers/mobile.py` to use Mobile DTOs
- [ ] Migrate `api/routers/wear_os.py` to use Watch DTOs
- [ ] Audit all routers for duplicate DTOs
- [ ] Replace duplicates with imports from `cores/contracts/`

**Phase 2: Frontend**
- [ ] Create TypeScript types from Python DTOs
- [ ] Update `frontend/src/services/ownexData.ts`
- [ ] Update `frontend/src/types/`

**Phase 3: Mobile**
- [ ] Update Android Kotlin data classes
- [ ] Ensure API responses match contracts

**Phase 4: Watch**
- [ ] Update WearOS Java data classes
- [ ] Ensure API responses match contracts

**Phase 5: Sync Manager**
- [ ] Implement `cores/sync/manager.py` using Sync DTOs
- [ ] Add event bus integration
- [ ] Add conflict resolution

---

## 11. VALIDATION RULES

### 11.1 No Duplicate DTOs

**Forbidden:**
```python
# ❌ BAD - Duplicate DTO in router
class MobileStatus(BaseModel):
    findings_total: int
    # ...
```

**Required:**
```python
# ✅ GOOD - Import from contracts
from cores.contracts import MobileStatus
```

### 11.2 Strict Type Safety

- All enums must be `StrEnum`
- All datetime fields must have defaults
- All optional fields must be `T | None`
- All list fields must have default factories

### 11.3 Versioning

- DTOs are versioned via git, not via code
- Breaking changes require coordination across all surfaces
- Non-breaking changes (adding optional fields) are safe

---

## 12. NEXT STEPS

1. **P0-1: Decidir desktop implementation** (PySide6 vs Tauri)
2. **P0-2: Implementar cross-device sync manager** using Sync DTOs
3. **P0-3: Agregar tests mobile/watch** using Mobile/Watch DTOs
4. **Migrate backend routers** to use contracts
5. **Create TypeScript types** from contracts
6. **Update Android/WearOS** data classes

---

**Estado:** DEFINED  
**Siguiente acción:** Decidir desktop implementation (P0-1)
