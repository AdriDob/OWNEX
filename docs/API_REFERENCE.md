# CATEYE API Reference

> Complete REST API documentation for CATEYE v4.1.0. All endpoints return JSON unless otherwise noted.
> Base URL: `http://localhost:8000`
> Auth: Bearer JWT token (obtained via POST /api/auth/login)

---

## 1. Core System

### GET /api/health

System health check — no auth required.

**Response** `200`:
```json
{
  "status": "ok",
  "app": "CATEYE API",
  "version": "4.1.0"
}
```

### GET /api/system/status

Enhanced system health with watchdog, pipeline, agents, resource usage.

**Response** `200`:
```json
{
  "status": "healthy",
  "version": "4.1.0",
  "pid": 12345,
  "uptime_seconds": 124800.0,
  "watchdog": {"running": true, "last_check": "..."},
  "system": {
    "memory_percent": 15.2,
    "memory_rss_mb": 245.6,
    "cpu_percent": 8.3,
    "num_threads": 12
  },
  "pipeline": {"total_pipelines": 47},
  "agents": {"active": 3, "idle": 2},
  "database": {"file_size_mb": 24.5}
}
```

### GET /api/system/state

Full system state summary with service health details.

**Response** `200`:
```json
{
  "state": {"system_state": "healthy", "services_count": 5},
  "services": {"backend": "healthy", "frontend": "healthy", "intelligence": "healthy"}
}
```

### GET /api/system/state/events

Recent EventBus history.

**Query params**: `event_type` (optional filter), `limit` (default 50, max 200).

### GET /api/system/definitions

System definitions consumed by frontend for Settings, Connections, Identity.

**Response** `200`:
```json
{
  "platforms": [
    {"id": "hackerone", "name": "HackerOne", "color": "#00d46a"},
    {"id": "bugcrowd", "name": "Bugcrowd", "color": "#f56e2f"}
  ],
  "tools": [
    {"id": "nuclei", "name": "Nuclei", "desc": "Template-based scanner"},
    {"id": "subfinder", "name": "Subfinder", "desc": "Passive subdomain discovery"}
  ],
  "osint_services": [
    {"id": "shodan", "name": "Shodan", "free": true, "url": "https://account.shodan.io"}
  ]
}
```

### GET /api/core/extensions

List all discovered ORION Platform extensions.

**Response** `200`: Extension registry status with loaded/failed counts.

### GET /api/core/secrets

List secret keys (not values).

**Response** `200`: `{"keys": ["OPENAI_API_KEY", "SHODAN_API_KEY"]}`

### GET /api/core/secrets/{key}

Get a specific secret value.

**Response** `200`: `{"key": "OPENAI_API_KEY", "value": "sk-...", "found": true}`
**Response** `404`: Secret not found.

### PUT /api/core/secrets/{key}

Store a secret.

**Request**:
```json
{"value": "your-api-key"}
```

**Response** `200`: `{"key": "SHODAN_API_KEY", "stored": true}`

### DELETE /api/core/secrets/{key}

Delete a secret.

**Response** `200`: `{"key": "SHODAN_API_KEY", "deleted": true}`

### GET /api/core/health

Unified ORION Platform health status.

**Response** `200`:
```json
{
  "status": "green",
  "checks": {"database": true, "extensions": true, "secrets": true},
  "details": {}
}
```

### GET /api/core/status

Platform-wide status — apps, extensions, databases, scheduler jobs.

### GET /api/metrics

Prometheus-style metrics endpoint.

**Response** `200` (text/plain):
```
CATEYE_pipeline_timing{stat="avg_ms"} 1234
CATEYE_intelligence{stat="patterns_learned"} 42
```

---

## 2. Auth

### POST /api/auth/login

Authenticate a device. Creates session and returns JWT token.

**Request**:
```json
{
  "device_id": "device-abc-123",
  "device_info": {"os": "linux", "browser": "firefox"}
}
```

**Response** `200`:
```json
{
  "status": "ok",
  "data": {
    "token": "eyJ...",
    "refresh": "rt_...",
    "device_id": "device-abc-123",
    "user_id": "local"
  }
}
```

### POST /api/auth/logout

End a device session.

**Request**:
```json
{"device_id": "device-abc-123"}
```

**Response** `200`: `{"status": "ok", "data": {"status": "logged_out", "device_id": "device-abc-123"}}`

### GET /api/auth/session

Get session info for a device.

**Query params**: `device_id` (required).

### GET /api/auth/me

Validate current token.

**Header**: `Authorization: Bearer <token>`

**Response** `200`: `{"status": "ok", "data": {"device_id": "...", "user_id": "local", "authenticated": true}}`

### POST /api/auth/refresh

Refresh an expiring token.

**Request**:
```json
{
  "device_id": "device-abc-123",
  "refresh_token": "rt_..."
}
```

---

## 3. Targets

### GET /api/targets

List all targets (paginated).

**Query params**: `skip` (default 0), `limit` (default 100, max 500), `sort_by` (default "name"), `sort_order` ("asc"/"desc"), `search` (max 200 chars).

**Response** `200`:
```json
{
  "items": [{"id": 1, "name": "Acme Corp", "domain": "acme.com"}],
  "total": 12,
  "skip": 0,
  "limit": 100
}
```

### POST /api/targets

Create a new target.

**Request**:
```json
{
  "name": "Acme Corp",
  "domain": "acme.com",
  "mode": "FAST"
}
```

**Response** `200`: Created target object.

### GET /api/targets/{id}

Get target detail.

### POST /api/targets/{id}/scan

Trigger a scan on a target.

**Request**:
```json
{"mode": "quick"}
```

**Response** `200`: Scan launch result.

**Status codes**: `200` scan started, `404` target not found.

### GET /api/targets/{id}/summary

Get target summary with endpoint classification and unified scoring.

---

## 4. Findings

### GET /api/findings

List findings (paginated).

**Query params**: `target_id`, `endpoint_id`, `skip` (0), `limit` (100, max 500), `sort_by` ("severity"), `sort_order` ("desc"), `search` ("").

**Response** `200`:
```json
{
  "items": [
    {
      "id": 1,
      "target_id": 1,
      "endpoint_id": 10,
      "title": "SQL Injection in /api/users",
      "severity": "critical",
      "description": "...",
      "status": "open",
      "created_at": "2026-07-10T12:00:00"
    }
  ],
  "total": 47,
  "skip": 0,
  "limit": 100
}
```

### POST /api/findings

Create a new finding.

**Request**:
```json
{
  "target_id": 1,
  "endpoint_id": 10,
  "title": "SQL Injection in /api/users",
  "severity": "critical",
  "description": "Parameter id is vulnerable to SQLi"
}
```

Publishes `finding:created` event to EventBus.

### GET /api/findings/stats

Aggregate findings statistics — total count, severity breakdown, new in 24h.

### GET /api/findings/{id}

Get single finding detail.

### PUT /api/findings/{id}/status

Update finding status.

**Request**:
```json
{"status": "confirmed"}
```

Valid statuses: `open`, `confirmed`, `rejected`, `in_progress`. Publishes `finding:status_changed` event.

### PATCH /api/findings/{id}

Update finding notes and/or status.

**Request**:
```json
{
  "notes": "Verified manually — confirmed",
  "status": "confirmed"
}
```

### POST /api/findings/{id}/classification

Run rule-based classification on a finding. Detects: sqli, xss, csrf, rce, ssrf, idor, open-redirect, other.

### GET /api/findings/{id}/evidence

List evidence items associated with a finding.

### POST /api/findings/{id}/generate-report

Generate a draft report from a finding.

### GET /api/findings/{id}/export-markdown

Export finding as Markdown attachment.

### GET /api/findings/{id}/export-pdf

Export finding as PDF (HTML version for now).

---

## 5. Reports

### GET /api/reports

List reports with filtering.

**Query params**: `limit` (20, max 100), `offset` (0), `status` (comma-separated), `search`, `sort_by` ("created_at"), `sort_order` ("desc"), `date_from`, `date_to`.

**Response** `200`:
```json
{
  "items": [{"id": 1, "title": "SQLi Report", "status": "draft"}],
  "total": 5
}
```

### POST /api/reports

Create a report from findings.

**Request**:
```json
{
  "finding_ids": [1, 2, 3],
  "program": "Starbucks BB",
  "severity": "critical"
}
```

**Response** `200`: Full report object.
**Response** `400`: Invalid finding IDs.

### GET /api/reports/{id}

Get single report detail.

### PUT /api/reports/{id}

Update report fields.

### GET /api/reports/{id}/export

Export report in various formats.

**Query params**: `format` — one of `markdown`, `html`, `pdf`, `txt`.

### GET /api/reports/{id}/versions

List version history for a report.

### POST /api/reports/{id}/versions

Save a new version snapshot.

### POST /api/reports/{id}/submit

Submit report to a bug bounty platform.

**Request**:
```json
{"platform": "hackerone"}
```

### GET /api/reports/{id}/submissions

Get submission status for a report.

### GET /api/reports/stats

Report statistics.

### GET /api/reports/submissions

List all submission records across all reports.

### GET /api/reports/reward-learning

Run reward learning analysis and return payout predictions by vuln type and program.

---

## 6. Financial

### GET /api/financial/dashboard

Unified financial dashboard — patrimonio total, objetivo libertad, liquidity breakdown, crypto prices, monthly income, alerts.

**Response** `200`:
```json
{
  "patrimonio_total": 47234.50,
  "objetivo_libertad": {
    "meta_usd": 30000.0,
    "progreso": 78.0,
    "restante": 0.0
  },
  "liquidez": {
    "disponible": 35000.0,
    "congelado": 5000.0,
    "pendiente": 7234.50
  },
  "breakdown": {
    "plataformas_bounty": {"total": 12000.0, "detalle": {"hackerone": 4500.0}},
    "crypto": {"total": 28000.0, "detalle": {"BTC": 15000.0, "ETH": 8000.0}},
    "takenos": {"total": 1500.0},
    "atlas_inversiones": {"total": 5734.50}
  },
  "ingresos": {
    "total_mes": 3420.0,
    "por_plataforma": {"hackerone": 2500.0, "bugcrowd": 920.0}
  },
  "precios": {"BTC": 61234.0, "ETH": 3456.0, "SOL": 145.0},
  "alertas": [
    {"tipo": "sync_fallo", "severidad": "warning", "plataforma": "binance", "mensaje": "3 sincronizaciones fallidas"}
  ]
}
```

### GET /api/financial/integrations/status

Status of all financial integrations — platforms, crypto wallets, Takenos, CoinGecko.

**Response** `200`:
```json
{
  "overall": "green",
  "total_integraciones": 8,
  "integradas": 6,
  "parciales": 1,
  "fallidas": 1,
  "integraciones": {
    "hackerone": {"estado": "green", "balance_usd": 4500.0},
    "coingecko": {"estado": "green"},
    "takenos": {"estado": "yellow", "balance_usd": 1500.0}
  }
}
```

### GET /api/financial/sync/status

Financial auto-sync scheduler status.

### POST /api/financial/sync/all

Trigger full sync of all platforms and crypto.

### POST /api/financial/sync/platforms

Sync only bounty platform balances.

### POST /api/financial/sync/crypto

Sync only crypto wallet balances.

### GET /api/financial/sync/history

Last N sync reports.

**Query params**: `limit` (default 10).

### GET /api/financial/state

Full financial truth layer state.

### GET /api/financial/state/summary

Compact financial summary with all balance types.

### GET /api/financial/state/by-category

Financial state broken down by ValueCategory.

### GET /api/financial/state/by-platform

Financial state per platform with sync health.

### GET /api/financial/state/sync-health

Per-platform sync health status.

### GET /api/financial/ledger

Financial ledger history.

**Query params**: `limit` (default 100).

### POST /api/financial/adjustment

Record a manual financial adjustment (e.g., correcting a balance, adding an off-platform payment).

**Request**:
```json
{
  "amount": 500.00,
  "currency": "USD",
  "description": "Manual payout from private program",
  "platform": "manual"
}
```
Publishes `financial:sync_completed` event to EventBus.

### GET /api/financial/withdrawals

List withdrawals with optional filtering by `status` (pending, confirmed, failed) and `platform`.

### POST /api/financial/withdrawals

Request a new withdrawal. Publishes `financial:withdrawal_completed` or `financial:sync_completed` event.

### GET /api/financial/withdrawals/summary

Withdrawal statistics.

### GET /api/financial/reconciliation/state

Reconciliation engine state.

### GET /api/financial/reconciliation/history

Reconciliation history.

---

## 7. Evidence

### POST /api/evidence/upload

Upload an evidence file.

**Request**: multipart/form-data with `file` (UploadFile) and optional `finding_id` (int).

**Response** `200`:
```json
{
  "status": "ok",
  "path": "/home/user/.orion/evidence/abc123.png",
  "size": 45678,
  "finding_id": 1
}
```

Files stored in `~/.orion/evidence/` with UUID filenames.

### GET /api/evidence

List evidence files (paginated).

**Query params**: `verdict_id`, `skip` (0), `limit` (100, max 500), `sort_by` ("id"), `sort_order` ("desc"), `search` ("").

---

## 8. Opportunities

### GET /api/opportunities

List opportunities (paginated).

**Query params**: `skip` (0), `limit` (200, max 500), `sort_by` ("roi"), `sort_order` ("desc"), `search` ("").

**Response** `200`:
```json
{
  "items": [{"id": 1, "name": "Starbucks BB", "roi": 9.2}],
  "total": 6,
  "skip": 0,
  "limit": 200
}
```

---

## 9. Settings

### GET /api/settings/unified

Get all settings as a flat key-value dict.

**Response** `200`:
```json
{
  "settings": {"scan_mode": "DEEP", "orion_enabled": true},
  "count": 42
}
```

### GET /api/settings/unified/{key}

Get a single setting by key path.

**Response** `200`: `{"key": "scan_mode", "value": "DEEP"}`
**Response** `404`: Setting not found.

### PUT /api/settings/unified

Save multiple settings (batch).

**Request**:
```json
{
  "settings": {
    "scan_mode": "FAST",
    "orion_enabled": true,
    "deprecated_key": null
  }
}
```

Keys with `null` value are deleted.

### DELETE /api/settings/unified/{key}

Delete a single setting.

---

## 10. System & Operations

### GET /api/system/timeline

Event timeline with filtering — provides a chronological view of all system activity.

**Query params**: `target_id`, `limit` (100, max 500), `offset` (0), `event_type`.

### GET /api/system/replay

List targets that have replay data available (scans with recorded HTTP interactions).

### GET /api/system/replay/{target_id}

Build a complete replay for a specific target — reconstructs the scan sequence with all HTTP requests and responses.

### GET /api/system/update-check

Check for available CATEYE updates by querying the configured update server. Returns current version and available update URL if a new version exists.

**Response** `200` (update available):
```json
{
  "available": true,
  "version": "4.2.0",
  "download_url": "...",
  "current_version": "4.1.0"
}
```

### GET /api/system/confidence

Confidence audit — evaluate how confident the system is in its verdicts and findings.

**Query params**: `item_type` — "verdict" or "finding", `limit` (default 50, max 200).

**Response** `200`:
```json
{
  "total_audited": 29,
  "avg_confidence": 0.74,
  "by_outcome": {"confirmed": 15, "rejected": 8, "inconclusive": 4, "pending": 2}
}
```

### GET /api/system/confidence/{type}/{item_id}

Get the confidence audit for a single item (verdict or finding).

**Response** `404`: Item not found.

### GET /api/system/review

Build and return the current review queue — items that need human attention.

**Query params**: `limit` (default 100, max 500).

**Response** `200`:
```json
{
  "items": [{"id": 1, "type": "finding", "priority": "high", "title": "SQL Injection"}],
  "total_items": 8
}
```

---

## 11. WebSocket

### WS /ws

WebSocket endpoint for real-time EventBus events. No authentication required for local connections.

**Example (JavaScript)**:
```javascript
const ws = new WebSocket("ws://localhost:8000/ws");
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.event_type, data.payload);
};
```

**Event types**: `finding:created`, `finding:status_changed`, `report:generated`, `opportunity:found`, `opportunity:updated`, `discovery:completed`, `system:boot:complete`, `agent:*`, `financial:*`.

---

## 12. Prometheus Metrics

### GET /api/metrics

Prometheus-style metrics endpoint at `/api/metrics` (text/plain content type).

Metrics include:
- Pipeline stage timing (avg_ms, count, total_ms per stage)
- Intelligence layer stats (patterns_learned, recommendations_generated)
- System stats (timeline_events, replays_generated, confidence_audits, review_queue_items)
- Opportunity intelligence stats (total, providers_active, average_score, by_priority, by_category)
- Execution layer stats (total, by_type with avg_score, avg_duration, errors)
- Accountability stats (success_rate, avg_outcome_score, active_decisions, memory_usage)

All metrics use the `CATEYE_` prefix for easy scraping by Prometheus or any OpenMetrics-compatible collector.

---

## Appendix: Status Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Bad request (invalid params, validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (CSRF token missing) |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

Rate limiting: 60 requests/minute per device. Redis-backed when available, SQLite fallback.

## Appendix: Middleware Stack

The API applies middleware in this order (outermost first):

1. **SecurityHeadersMiddleware** — CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
2. **CSRFMiddleware** — Double-submit cookie pattern, exempted for GET and HEAD
3. **RateLimitMiddleware** — 60 req/min per device, Redis or SQLite backend
4. **AuthMiddleware** — JWT token validation on all routes except /api/auth and /api/health
5. **ErrorHandlingMiddleware** — Catches unhandled exceptions, returns generic 500 response

All error responses follow the format:
```json
{
  "detail": "Human-readable error message"
}
```
