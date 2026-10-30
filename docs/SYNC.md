# OWNEX Synchronization Model

> **Generated from actual codebase** — This document reflects the real implementation.

## Overview

OWNEX uses a **backend-as-source-of-truth** synchronization model. All surfaces (Desktop, Mobile, Watch) are reactive views of the canonical backend state.

```
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (Canonical)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Database  │  │  Event Bus  │  │   API + WebSocket   │  │
│  │  (SQLite)   │◄─┤  (SQLite)   │──┤  (REST + WS)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
    ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
    │ Desktop │          │ Mobile  │          │  Watch  │
    │(Tauri)  │          │(Capacitor)        │(Wear OS)│
    └─────────┘          └─────────┘          └─────────┘
```

## Synchronization Channels

### 1. HTTP REST (Primary)
- **All Surfaces**: Desktop, Mobile
- **Pattern**: Request/Response
- **Auth**: Bearer JWT + httpOnly cookie
- **Caching**: Client-side (Pinia stores + localStorage)

### 2. WebSocket (Real-time)
- **Endpoint**: `/api/ws/terminal` (also carries live events)
- **Desktop**: Persistent connection, auto-reconnect
- **Mobile**: On-demand, background runner
- **Events**: `finding:created`, `approval:requested`, `system:health`, `agent:status`

### 3. Push Notifications (FCM)
- **Mobile**: High-priority for critical alerts
- **Topics**: `findings`, `approvals`, `alerts`, `system`
- **Payload**: Routes to specific screen + action

### 4. Wear OS Data Layer API
- **Phone ↔ Watch**: Google Play Services Data Layer
- **Paths**: `/ownex/status`, `/ownex/notification`, `/ownex/approval`
- **Direction**: Phone → Watch (push), Watch → Phone (approval response)

## Device Identity

### Registration Flow
```
1. App starts → generates UUID (if not exists)
2. POST /api/auth/device-login {device_id, platform}
3. Backend creates/updates device record
4. Returns JWT + sets httpOnly cookie
5. Device ID persisted:
   - Desktop: %LOCALAPPDATA%/OWNEX/desktop_device.json
   - Mobile: localStorage (CATEYE-device-id)
   - Watch: Synced from phone via Data Layer
```

### Device Record (Backend)
```python
class Device:
    device_id: str(UUID)
    platform: DESKTOP | ANDROID | WEAR_OS
    name: str
    last_seen: datetime
    capabilities: list[str]  # ["notifications", "approvals", "voice", "terminal"]
    push_token: str | None  # FCM token
    paired_devices: list[str]  # device_ids
```

## State Management

### Backend (Canonical)
- **Database**: SQLite/PostgreSQL — all persistent state
- **Event Bus**: SQLite — audit trail + real-time distribution
- **Memory**: In-process caches (LRU, TTL)

### Desktop (Tauri)
- **Pinia Stores**: Reactive caches (`useMissionStore`, `useCapitalStore`, etc.)
- **WebSocket**: Live updates → store mutations
- **Polling**: 10s auto-refresh for Mission Control views
- **Persistence**: None (always online via sidecar)

### Mobile (Capacitor)
- **Pinia Stores**: Same as desktop + offline queue
- **localStorage**: `CATEYE-device-id`, cached API responses
- **IndexedDB**: `outbox` (queued mutations), `cache` (GET responses)
- **Background Runner**: Flushes outbox on network restore

### Watch (Wear OS)
- **No Local State**: All data from phone via Data Layer
- **Cache**: Last 50 notifications, 20 approvals (phone-side)
- **Complications**: Cached by Wear OS system

## Synchronization Protocols

### GET Requests (Read)
```
Client → GET /api/resource
Backend → 200 OK + JSON
Client → Update store, render
```
- **Cache-Control**: `no-cache` for mutable, `max-age=60` for static
- **ETag**: Not implemented (use timestamps)

### POST/PUT/PATCH (Write)
```
Client → POST /api/resource {data, idempotency_key}
Backend → Validate → Persist → Event Bus → 201/200
Event Bus → WebSocket → All connected clients
Clients → Refetch affected resources
```
- **Idempotency**: `Idempotency-Key` header (UUID v4)
- **Optimistic UI**: Immediate local update, rollback on error

### WebSocket Events

| Event | Payload | Consumers |
|-------|---------|-----------|
| `finding:created` | `{finding_id, target_id, severity}` | Desktop, Mobile |
| `finding:updated` | `{finding_id, status}` | Desktop, Mobile |
| `approval:requested` | `{approval_id, title, workflow_id}` | Desktop, Mobile, Watch |
| `approval:responded` | `{approval_id, approved}` | Desktop, Mobile, Watch |
| `system:health` | `{score, status, components}` | Desktop, Mobile, Watch |
| `agent:status` | `{agent_id, status, task}` | Desktop, Mobile |
| `workflow:stage_changed` | `{workflow_id, stage, progress}` | Desktop, Mobile |
| `capital:snapshot` | `{total, pending, invested}` | Desktop, Mobile |

## Conflict Resolution

### Strategy: Server Wins (Last-Write-Wins with Timestamps)

```
1. Client sends update with `updated_at` timestamp
2. Backend compares with stored `updated_at`
3. If client timestamp < stored → 409 Conflict + current state
4. If client timestamp ≥ stored → Apply update, broadcast event
5. All clients refetch on event receipt
```

### Idempotency

- **All Mutations**: Require `Idempotency-Key` header
- **Storage**: `idempotency_keys` table (key, response, expires_at)
- **TTL**: 24 hours
- **Duplicate**: Returns original response, no side effects

## Offline Support

### Desktop
- **Always Online**: Sidecar runs locally
- **No Offline Mode**: N/A

### Mobile
| Operation | Offline Behavior |
|-----------|------------------|
| GET (read) | Returns cached response (stale-while-revalidate) |
| POST (mutate) | Queued in IndexedDB `outbox`, processed on reconnect |
| WebSocket | Disconnected, reconnects on network change |
| Push (FCM) | Received via system, wakes app if critical |

### Outbox Processing
```typescript
// On network restore:
for (const mutation of outbox) {
  try {
    await api.request(mutation.method, mutation.url, mutation.body, {
      headers: { 'Idempotency-Key': mutation.idempotencyKey }
    });
    outbox.remove(mutation.id);
  } catch (e) {
    if (e.status === 409) {
      // Conflict: refresh cache, retry with new data
      await refreshCache(mutation.url);
      // Re-queue with updated data
    } else {
      // Transient error: re-queue with backoff
      mutation.retryCount++;
      scheduleRetry(mutation);
    }
  }
}
```

### Watch
- **No Offline**: Requires phone connection for all operations
- **Cached Reads**: Last known status (phone-side persistence)

## Network Failure Handling

### Desktop (Sidecar)
- **Health Check**: `GET /api/health` every 5s (1.5s timeout)
- **Failure**: 3 consecutive failures → restart sidecar
- **Recovery**: Auto-restart, frontend polls until healthy

### Mobile
| Failure Type | Detection | Recovery |
|--------------|-----------|----------|
| API Timeout | 30s default | Retry 3x with exponential backoff |
| Network Error | `navigator.onLine` false | Queue mutations, retry on `online` event |
| WebSocket Close | `onclose` event | Reconnect with exponential backoff (max 30s) |
| FCM Failed | Token invalid | Re-register token on next app start |

### Watch
- **No Direct Network**: All via phone Data Layer
- **Phone Unreachable**: Shows "Disconnected" status
- **Recovery**: Automatic on phone reconnect

## Sync Schedules

| Surface | Mechanism | Frequency |
|---------|-----------|-----------|
| Desktop | WebSocket + 10s polling | Real-time + 10s |
| Mobile (foreground) | WebSocket + API | Real-time |
| Mobile (background) | Background Runner | 15 min (configurable) |
| Mobile (push) | FCM | Immediate |
| Watch | Data Layer | On change + 5 min status |

## Error Handling

### Retry Policy
```python
# Exponential backoff with jitter
delay = min(base * (2**attempt) + random(0, 1000), max_delay)
# base=1000ms, max_delay=30000ms
```

### Circuit Breaker
- **Threshold**: 5 consecutive failures
- **State**: OPEN → blocks requests for 60s
- **Half-Open**: Allows 1 request to test
- **Closed**: Resets on success

### Dead Letter Queue
- **Failed Mutations**: After 5 retries → `dead_letter` table
- **Manual Review**: Admin UI to inspect/replay
- **Alert**: Logged to `ownex.error` logger

## Monitoring

### Metrics (Prometheus)
```
ownex_sync_requests_total{surface, method, status}
ownex_sync_latency_seconds{surface, method}
ownex_sync_conflicts_total{surface, resource}
ownex_sync_outbox_size{surface}
ownex_watch_sync_failures_total
```

### Health Checks
- **Backend**: `/api/health` (includes sync health)
- **Desktop**: Sidecar health + WebSocket connected
- **Mobile**: Last successful sync timestamp
- **Watch**: Last Data Layer sync timestamp

## Security

### Transport
- **Desktop**: `http://localhost:8000` (local only)
- **Mobile**: `https://<ip>:8000` (TLS, self-signed cert pinned)
- **Watch**: Data Layer (encrypted by Google Play Services)

### Authentication
- **All Requests**: Bearer JWT + httpOnly cookie
- **CSRF**: Double-submit cookie (header + cookie)
- **Device Binding**: JWT `device_id` claim validated

### Rate Limiting
- **Per Identity**: 30 req/s burst 50
- **No-Limit Paths**: `/health`, `/version`, `/docs`, `/api/auth/*`
- **WebSocket**: 1 connection per device

## Testing Sync

### Unit Tests
```bash
# Backend sync logic
pytest tests/test_financial_scheduler_persist.py
pytest tests/test_payment_compat.py

# Mobile sync (mocked)
# In android/app/src/test/... (not yet implemented)
```

### Integration Tests
```bash
# Desktop sidecar + frontend
pytest tests/test_desktop_native.py

# E2E sync scenarios
pytest tests/test_income_chain_e2e.py
```

### Manual Testing
```bash
# 1. Start backend
python -m api.main

# 2. Start desktop
cd src-tauri && cargo tauri dev

# 3. Start mobile (emulator)
cd android && ./gradlew installDebug

# 4. Verify:
# - Desktop Mission Control shows real data
# - Mobile shows same dashboard data
# - Trigger finding → appears on both in <2s
# - Approve on watch → reflects on desktop/mobile
# - Disconnect network → mobile queues, reconnects → syncs
```

---

*Document generated from codebase. Last verified: 2026-08-27*