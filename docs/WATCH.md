# OWNEX Watch — Wear OS Alert Surface

> **Generated from actual codebase** — This document reflects the real implementation.

## Philosophy

**WATCH IS NOT A MINIATURE DESKTOP.**

The Wear OS app exists solely for:
- **Critical Alerts** — Findings, approvals, system health
- **Quick Status** — System online, active cycles, pending approvals
- **One-Tap Approvals** — Approve/Defer workflow actions
- **Next Action Preview** — What to do next, reward, confidence

It does NOT support:
- Complex workflows
- Data entry
- Full dashboards
- Settings management

## Architecture

```
Wear OS App (ai.rastro.watch)
├── MainActivity (standalone watch app)
├── Data Layer API (phone ↔ watch sync)
├── Ongoing Activity (persistent notification)
├── Complications (watch face integration)
└── Notifications (FCM + local)
```

## Implementation (`android/wear/`)

### Configuration

**Package**: `ai.rastro.watch` (separate from phone `ai.rastro.app`)

**build.gradle**:
```gradle
namespace 'ai.rastro.watch'
applicationId "ai.rastro.watch"
minSdk 30 (Wear OS 3)
targetSdk 34
compileSdk 34
```

**Dependencies**:
```gradle
implementation 'com.google.android.gms:play-services-wearable:18.2.0'
implementation 'androidx.wear:wear:1.3.0'
implementation 'androidx.wear:wear-ongoing:1.0.0'
implementation 'androidx.lifecycle:lifecycle-service:2.8.4'
```

### Manifest
```xml
<uses-permission android:name="android.permission.WAKE_LOCK" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<uses-feature android:name="android.hardware.type.watch" />

<application ...>
    <meta-data
        android:name="com.google.android.wearable.standalone"
        android:value="false" />  <!-- Requires phone companion -->
</application>
```

## Backend Integration (`cores/wear_os/integration.py`)

### Data Models

```python
class WatchNotification:
    notification_id: str
    title: str
    message: str
    level: CRITICAL | HIGH | MEDIUM | LOW
    created_at: ISO8601
    read: bool
    requires_action: bool
    action_type: str | None


class WatchApprovalRequest:
    request_id: str
    title: str
    description: str
    workflow_id: str | None
    created_at: ISO8601
    responded: bool
    approved: bool | None


class WatchStatus:
    system_online: bool
    scheduler_running: bool
    active_workflows: int
    pending_approvals: int
    findings_total: int
    findings_confirmed: int
    targets_active: int
    health_score: float
    last_updated: ISO8601
```

### API Endpoints (`api/routers/wear_os.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wear-os/status` | GET | System status for watch face |
| `/wear-os/notification` | POST | Send notification to watch |
| `/wear-os/notifications` | GET | List notifications (filter: level, unread, limit) |
| `/wear-os/notification/{id}/read` | PUT | Mark notification read |
| `/wear-os/approval-request` | POST | Request approval from watch |
| `/wear-os/approvals/pending` | GET | List pending approvals |
| `/wear-os/approval/{id}/respond` | POST | Respond to approval (approved: bool) |
| `/wear-os/clear-notifications` | POST | Clear old notifications (days) |

### Data Persistence

- **Storage**: `~/.ownex/wear_os/` (phone-side)
- **Files**: `notifications.json`, `approvals.json`
- **Retention**: 50 notifications, 20 approval requests (FIFO)
- **Sync**: Phone → Watch via Data Layer API

## UI Specification

### Watch Face Layout (Primary Screen)

```
┌─────────────────────┐
│ 🟢 ORION ONLINE     │  ← System status indicator
│ 3 ciclos activos    │  ← Active work cycles
│ 2 aprobaciones 🔔   │  ← Pending approvals badge
├─────────────────────┤
│ ⚡ Próxima acción   │  ← Next Best Action preview
│ Validar IDOR Target X│
│ $800 · 87% · 25m    │  ← Reward, confidence, time
│ [Aprobar] [Luego]   │  ← One-tap actions
├─────────────────────┤
│ 🤖 Agentes: 5/6 🟢  │  ← Agent fleet summary
│ 💰 $2.4k este mes   │  ← Monthly revenue
└─────────────────────┘
```

### Notification Cards

```
┌─────────────────────┐
│ 🔴 CRITICAL         │  ← Level badge (color-coded)
│ Hallazgo confirmado │  ← Title
│ IDOR en API /users  │  ← Message
│ [Ver] [Desestimar]  │  ← Actions (if requires_action)
│ 2m ago              │  ← Timestamp
└─────────────────────┘
```

### Approval Request

```
┌─────────────────────┐
│ 🟡 APROBACIÓN       │
│ Iniciar ciclo val.  │  ← Title
│ Target: acme.com    │  ← Description
│ Reward: $800        │
│ [✅ Aprobar] [⏭️ Luego]│
└─────────────────────┘
```

### Interactions

| Gesture | Action |
|---------|--------|
| Tap notification | Open detail / mark read |
| Tap "Aprobar" | POST `/wear-os/approval/{id}/respond` with `{"approved": true}` |
| Tap "Luego" | POST with `{"approved": false}` (defer) |
| Swipe up | Detail view |
| Swipe down | Dismiss / mark read |
| Long press | Open in mobile app |

## Sync Mechanism

### Phone → Watch (Data Layer API)

```kotlin
// Triggered on:
// - New notification (send_notification)
// - New approval request (request_approval)
// - Status change (periodic, every 5 min)
// - Manual sync from phone app

Wearable.getDataClient(context)
    .putDataItem(DataMap.toPutDataRequest("/ownex/status", dataMap))
```

### Data Paths

| Path | Payload | Direction |
|------|---------|-----------|
| `/ownex/status` | `WatchStatus` | Phone → Watch |
| `/ownex/notification` | `WatchNotification` | Phone → Watch |
| `/ownex/approval` | `WatchApprovalRequest` | Phone → Watch |
| `/ownex/approval_response` | `{request_id, approved}` | Watch → Phone |

### Sync Schedule

| Trigger | Frequency |
|---------|-----------|
| Critical notification | Immediate (high priority) |
| Approval request | Immediate |
| Status update | Every 5 minutes |
| Manual sync (phone app) | On demand |
| Watch wake/resume | On resume |

## Complications (Watch Face)

### Supported Complication Types

| Complication | Data Source | Update Frequency |
|--------------|-------------|------------------|
| `SHORT_TEXT` | Health score (95%) | Every 5 min |
| `RANGED_VALUE` | Pending approvals (0-10) | On change |
| `SMALL_IMAGE` | System status icon (🟢🟡🔴) | On change |

### Complication Data Provider

```kotlin
class OwnexComplicationProvider : ComplicationDataSourceService() {
    override fun onComplicationRequest(request: ComplicationRequest) {
        when (request.complicationType) {
            ComplicationData.TYPE_SHORT_TEXT -> provideHealthScore()
            ComplicationData.TYPE_RANGED_VALUE -> providePendingApprovals()
            ComplicationData.TYPE_SMALL_IMAGE -> provideStatusIcon()
        }
    }
}
```

## Battery Optimization

### Strategies

| Strategy | Implementation |
|----------|----------------|
| **No Polling** | Watch never polls; receives push via Data Layer |
| **Minimal Rendering** | Only updates on data change |
| **Ongoing Activity** | For active approvals (keeps screen accessible) |
| **Wake Lock** | Only during user interaction |
| **Network** | Zero direct network; all via phone Data Layer |

### Expected Battery Impact

- **Idle**: < 1% per day
- **Active (approvals)**: ~3-5% per day
- **Complications**: ~1-2% per day

## Build & Release

### Debug APK
```bash
cd android
./gradlew :wear:assembleDebug
# Output: android/wear/build/outputs/apk/debug/wear-debug.apk
```

### Release APK
```bash
cd android
./gradlew :wear:assembleRelease
# Output: android/wear/build/outputs/apk/release/wear-release.apk
```

### Installation

1. **Via Phone App**: "Install on Watch" button (uses `PackageInstaller`)
2. **Manual ADB**: `adb install wear-release.apk`
3. **Play Store**: Future (requires separate listing)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Watch not receiving notifications | Check Data Layer API permission, re-pair watch |
| Approvals not syncing | Clear Data Layer cache, re-pair |
| Complications not updating | Verify `ComplicationDataSourceService` running |
| Battery drain | Disable complications, reduce sync frequency |
| "Standalone" not working | Set `standalone=true` in manifest (requires phone unpair) |

## Known Limitations

| Limitation | Details |
|-----------|---------|
| No voice input | No microphone access on current Wear OS version |
| No keyboard | Approvals only (no text entry) |
| Limited storage | 50 notifications / 20 approvals max |
| No offline queue | Requires phone connection for all actions |
| Complications API | Requires Wear OS 3+ (minSdk 30) |

---

*Document generated from codebase. Last verified: 2026-08-27*