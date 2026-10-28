# BACKEND MAP — OWNEX (2026-09-30)

## API Topology

```
api/
├── main.py                 # FastAPI app (946 lines), monkey-patches include_router
├── lifespan.py             # Startup/shutdown, scheduler, job handlers
├── scheduler.py            # ScanScheduler (1,326 LOC)
├── routers/ (199 files)
│   ├── __init__.py         # 182 router imports + 18 aliased
│   ├── _archived/          # 5 files, not imported
│   └── *.py                # 194 router modules
├── adapters/ (22 files)
├── middleware/ (6)
│   ├── auth_middleware.py      # Auth gate (49-50: early return for non-/api/)
│   ├── csrf_middleware.py      # CSRF (exempt: /api/health, /api/auth/*, /api/license/activate)
│   ├── rate_limit_middleware.py
│   ├── error_handling.py
│   └── security_headers.py
├── services/ (3)
│   ├── data_service.py
│   └── ...
└── schemas.py              # Pydantic models + APIEnvelope
```

---

## Router Inventory (201 mounted, 0 dead)

### By Mount Type

| Mount Type | Count | Prefix Examples |
|------------|-------|-----------------|
| `/api/<ns>/...` | 165 | `/api/targets`, `/api/findings`, `/api/reports` |
| `/api` exact | 2 | `/api` (control, overview) |
| Root-mounted (no `/api`) | 29 | `/direct-work`, `/finance`, `/today` |
| Bare `APIRouter()` | 2 | `ws.py`, `terminal_ws.py` |

### Root-Mounted Routers (29, 282 endpoints, 148 mutating unauthenticated)

| Prefix | File | Endpoints | Mutating |
|--------|------|-----------|----------|
| `/direct-work` | `direct_work.py` | 59 | 40 |
| `/finance` | `finance.py` | 34 | 14 |
| `/life-management` | `life_management.py` | 19 | 10 |
| `/first-money` | `first_money.py` | 16 | 7 |
| `/mission-hub` | `mission_hub.py` | 11 | 6 |
| `/wear-os` | `wear_os.py` | 7 | 4 |
| `/mobile` | `mobile.py` | 8 | 4 |
| `/enhanced-personalization` | `enhanced_personalization.py` | 10 | 4 |
| `/fiverr` | `fiverr.py` | 9 | 5 |
| `/supabase` | `supabase.py` | 8 | 4 |
| `/wear-os` | `wear_os.py` | 7 | 4 |
| `/voice` | `voice.py` | 7 | 4 |
| `/productivity` | `productivity.py` | 7 | 4 |
| `/version-backup` | `version_backup.py` | 6 | 3 |
| `/oar` | `oar.py` | 5 | 3 |
| `/remote` | `remote_control.py` | 5 | 3 |
| `/dev-bounty` | `dev_bounty.py` | 5 | 2 |
| `/onboarding` | `onboarding.py` | 5 | 2 |
| `/opensource` | `opensource.py` | 5 | 2 |
| `/result-based` | `result_based.py` | 4 | 2 |
| `/webhook` | `webhook.py` | 3 | 2 |
| `/decision` | `decision.py` | 2 | 1 |
| `/revenue-timeline` | `revenue_timeline.py` | 3 | 1 |
| `/zero-barrier` | `zero_barrier.py` | 5 | 1 |
| `/auth` | `auth_user.py` | 5 | 4 |
| `/decision` | `decision.py` | 2 | 1 |
| `/platform-guides` | `platform_guides.py` | 7 | 0 |
| `/today` | `today.py` | 1 | 0 |

**Total root-mounted mutating: 148** — all accessible without auth due to `auth_middleware.py:49-50` early return.

---

## Router Classification (198 files)

| Class | Count | Criteria |
|-------|-------|----------|
| Direct DB access | 44 | `database` import / `SessionLocal` / `.query()` / `db.add` / `commit()` |
| Business logic | 25 | ≥2 private helpers, no direct DB |
| Thin transport | 129 | 0 direct DB, <2 private helpers |

### Direct-DB Routers (44)

`alerts, atlas_app, attack, auth_user, auth_users, auto_submit, command_center, connections, copilot, cycles, daily, daily_digest, differential_intelligence, discovery, economic, findings, forge_app, help_center, hunter, hypotheses, idor, investigations, mission_hub, mobile, mobile_approvals, notifications, observation, operations, outlook, overview, pulse_app, quick_wins, report_pipeline, reports, reports_acceptance, reports_quality, roi, scans, screenshots, settings_unified, targets, validation, vault_app, version_backup`

---

## Core Business Logic (193 subpackages, 357K LOC)

### Largest Packages

| Package | Files | LOC | Purpose |
|---------|-------|-----|---------|
| `cores/opportunity/` | 83 | 24,865 | Opportunity engine, adapters, executors |
| `cores/direct_work_engine/` | 61 | 23,402 | Work execution, workbank, autonomous discovery |
| `cores/trading/` | 42 | 12,366 | Trading engine |
| `cores/ai/` | 45 | 11,366 | AI providers, agents, tools |
| `cores/engine/` | 34 | 9,966 | Orchestration |
| `cores/offensive/` | 44 | 8,969 | Red team / validation |
| `cores/execution/` | 54 | 8,310 | Work execution pipeline |
| `cores/cycles/` | 25 | 7,196 | Scheduler cycles |
| `cores/validation/` | 23 | 6,589 | Validation engine |
| `cores/agents/` | 7 | 6,484 | Agent framework |
| `cores/financial/` | 14 | 4,729 | Financial sync, truth layer |

---

## Duplicate Implementations (Critical)

| Domain | Count | Locations |
|--------|-------|-----------|
| **Opportunity Discovery** | 4 layers | `cores/opportunity/adapters/`, `executors/`, `api/adapters/`, `direct_work_engine/` |
| **Validation** | 6 implementations | `cores/validation/`, `engine/validation`, `execution/validation`, `cycles/stages/validation_executor`, `api/routers/validation`, `offensive/*` |
| **Scheduling** | 10 classes | `api/scheduler.py`, `cores/scheduler/*.py` (3), `life_scheduler`, `runs`, `financial`, `cloud_backup`, `execution/runtime`, `self_healer`, `interfaces` |
| **Revenue Tracking** | 6 implementations | `revenue/`, `revenue_tracker/`, `economic_feedback/`, `financial/`, `ledger/`, `revenue_multiplier/` |

### Concrete Collisions (Same Name, Different Implementation)

| Symbol | Count | Locations |
|--------|-------|-----------|
| `class RevenueState` | 2 | `revenue/ledger.py:22`, `revenue_tracker.py:30` |
| `class RevenueMetrics` | 2 | `revenue/metrics.py:28`, `revenue_tracker.py:321` |
| `class RevenueEngine` | 2 | `revenue/engine.py:20`, `revenue/engine.py:165` |
| `class RevenuePipeline` | 1 | `revenue/pipeline.py:60` |
| `class RevenueOpportunity` | 2 | `revenue_engine.py:42`, `revenue_tracker.py:202` |
| `class RevenueMetrics` | 2 | `revenue/metrics.py:28`, `revenue_tracker.py:321` |

---

## Scheduler Architecture (10 classes, 3 job registries)

| # | Class | File | Role |
|---|-------|------|------|
| 1 | `ScanScheduler` | `api/scheduler.py` (1,326 LOC) | Production pipeline |
| 2 | `CoreScheduler` | `cores/scheduler/scheduler.py` | Timing only |
| 3 | `EnhancedScheduler` | `cores/scheduler/scheduler_v2.py` | Circuit breakers (parallel #2) |
| 4 | `LifeScheduler` | `cores/scheduler/life_scheduler.py` | 3rd orchestration loop |
| 5 | `SchedulerRunLedger` | `cores/scheduler/runs.py` | JSONL ledger |
| 6 | `FinancialSyncScheduler` | `cores/financial/scheduler.py` | Financial sync |
| 7 | `CloudBackupScheduler` | `cores/cloud_backup/scheduler.py` | Backup |
| 8 | `RuntimeScheduler` | `cores/execution/runtime/scheduler.py` | Execution |
| 9 | `SelfHealerScheduler` | `cores/self_healer/scheduler.py` | Self-healing |
| 10 | `IScheduler` | `cores/interfaces/scheduler.py` | ABC |

**Job Registries (3)**:
1. **Canonical**: `cores/scheduler/jobs.py` (17 cycle keys, 20 `get_*_jobs()`)
2. `cores/scheduler/jobs/bug_bounty.py` (LifeScheduler wrapper)
3. Inline `JobDefinition` in `api/lifespan.py:505-517`

**Handler Resolvability**: 56/57 resolve. 1 fails (`run_autonomous_research_cycle` — `aiohttp` missing).

---

## Revenue Tracking (6 Parallel Implementations)

| # | Path | Core Class | Key Issue |
|---|------|------------|-----------|
| 1 | `cores/revenue/` | `RevenueEngine`, `RevenueLedger` | `RevenueState` enum in `ledger.py:22` |
| 2 | `cores/revenue_tracker/` | `RevenueTracker` (memory-only!) | **No persistence** |
| 3 | `cores/economic_feedback/` | `ChannelEconomics` | Per-channel net/hour |
| 4 | `cores/financial/` | `FinancialSyncScheduler`, `ExecutionRevenueSync` | Sync layer |
| 5 | `cores/ledger/` | `LedgerEvent`, `LedgerEntryData` | 3rd ledger |
| 6 | `cores/revenue_multiplier/` | `RevenueMultiplierOrchestrator` | Multiplier engine |

**CRITICAL**: `RevenueTracker` (2,416 LOC) is **memory-only** — no file/DB persistence. Recovery only from `workbank.json` + `submission_queue.json`.

---

## Scheduler Job Registries (3)

1. **Canonical**: `cores/scheduler/jobs.py` (884 LOC, 17 cycle keys, 20 `get_*_jobs()`)
2. `cores/scheduler/jobs/bug_bounty.py` (190 LOC) — LifeScheduler wrapper
3. Inline `JobDefinition` in `api/lifespan.py:505-517`

**Handler Resolvability**: 56/57 resolve. 1 fails: `run_autonomous_research_cycle` (missing `aiohttp`).

---

## External API Adapters (22 files)

| Adapter | Platform | Type |
|---------|----------|------|
| `direct_work_algora.py` | Algora | REST |
| `direct_work_opire.py` | Opire | REST |
| `direct_work_github.py` | GitHub | GraphQL |
| `direct_work_bugbounty.py` | BugBountyHQ | REST |
| `direct_work_polar.py` | Polar | REST |
| `direct_work_legacy.py` | Legacy | Wrapper |
| `security/hackerone.py` | HackerOne | GraphQL |
| `security/bugcrowd.py` | Bugcrowd | REST |
| `security/intigriti.py` | Intigriti | REST |
| `security/yeswehack.py` | YesWeHack | REST |
| `security/synack.py` | Synack | REST |
| `security/immunefi.py` | Immunefi | REST |
| `security/cantina.py` | Cantina | REST |
| `security/hackenproof.py` | HackenProof | REST |
| `security/onlydust.py` | OnlyDust | REST |
| `security/code4rena.py` | Code4rena | REST |
| `security/bugbounty.py` | BugBountyHQ | REST |
| `security/opire.py` | Opire | REST |
| `security/forge.py` | Forge | REST |
| `security/code4rena.py` | Code4rena | REST |
| `security/immunefi.py` | Immunefi | REST |
| `security/issuehunt.py` | IssueHunt | REST |

---

## Auth & Auth Middleware

### `api/middleware/auth_middleware.py:49-50` — **CRITICAL BUG**
```python
if not path.startswith("/api/"):
    return await call_next(request)  # BYPASSES AUTH for 29 root-mounted routers
```

**Impact**: 29 root-mounted routers (282 endpoints, 148 mutating) have NO auth.

### Public Paths (exempt)
- Exact: `/api/health`, `/api/agents/health`, `/api/version`, `/api/system/health`, `/api/docs`, `/api/openapi.json`, `/api/redoc`, `/api/this-will-definitely-fail`
- Prefix: `/api/auth`, `/api/license`

### CSRF Exempt
`/api/health`, `/api/license/activate`, `/api/auth/login`, `/api/auth/register`, `/api/auth/logout`, `/api/auth/users/verify`, `/api/auth/desktop-session`, `/api/system/restart` + all safe methods

### Rate Limit Exempt
`/api/health`, `/api/version`, `/api/docs`, `/api/openapi.json`, `/api/redoc`

---

## Auth Flow

1. `main.ts:46` → `ensureDeviceId()` → `localStorage.setItem('CATEYE-device-id')`
2. `router.beforeEach` → `isPublicRoute()` → `auth.autoLogin()`
3. `auth.ts:63-86` `autoLogin()` → `POST /api/auth/login` with `{device_id, device_info}`
4. Backend `api/routers/auth.py:31` → `ok(result)` → `APIEnvelope{data:{token,refresh,device_id,user_id,existing}}`
5. Frontend expects `res.session.token` — **MISMATCH** (fixed in `auth.ts` to read `res.data.token`)

---

## WebSocket Endpoints

| Path | File | Auth |
|------|------|------|
| `/api/ws` | `api/routers/sync.py:94` | Token in query param |
| `/api/ws/approvals` | `mobile_approvals.py:416` | Token in query |
| `/api/ws/terminal` | `TerminalView.vue:71` | Token in query |

**Critical**: Backend sets `SameSite=lax` cookie. In Tauri (`tauri://localhost` origin), cookie NOT sent (cross-site). Frontend uses Bearer token via `wsUrl(path, token)` — **works if token exists**.

---

## Known Backend Bugs (Verified)

| Bug | File:Line | Impact |
|-----|-----------|--------|
| Auth bypass root-mounted | `auth_middleware.py:49-50` | 148 mutating endpoints unauthenticated |
| `RevenueTracker` memory-only | `revenue_tracker.py:355` | History lost on restart |
| Vault key regeneration | `vault_crypto.py:35-50` | Silent key overwrite → credential loss |
| `aiohttp` missing | `autonomous_discovery.py:19` | 1 handler unresolvable |
| `content_factory` hardcoded path | `content_factory/service.py:55` | Breaks on other machines |
| License HWID-bound | `license/hardware.py` | New machine = invalid license |
| `runSystemChecks` random failure | `SteamBigPictureSplash.vue:48` | 8% failure per check |
| `clearSession()` on ANY 401 | `api.ts:149-151` | Cascades 1 early 401 → 30 401s |
| 77 raw `fetch()` bypass auth | 25 files, 77 calls | Auth bypass |
| `/today` missing from Vite proxy | `vite.config.ts` | Dev-only 404 |