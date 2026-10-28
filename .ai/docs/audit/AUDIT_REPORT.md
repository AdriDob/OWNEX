# AUDIT REPORT — OWNEX (2026-09-30)

## Executive Summary

**Overall**: OWNEX is a **functioning but architecturally fragmented** desktop application with a working Tauri v2 frontend, a FastAPI backend with 1,846 endpoints, and a PyInstaller sidecar. The product **runs and works** but carries severe architectural debt, critical security flaws, and economic data integrity risks.

**Verdict**: **RELEASE READY for frontend/desktop** (with fixes applied), **NOT RELEASE READY for backend/auth** without fixes. **PHASE 1 STOP CONDITION not met** — product cannot be explained in one page.

---

## Scope & Methodology

- **Scope**: Full codebase (`api/`, `cores/`, `frontend/`, `desktop/`, `desktop/native/`, `tests/`, `database/`, `scripts/`, `.ai/`)
- **Method**: Static analysis (grep/find/AST regex), live verification (Tauri build/run, Playwright, curl), cross-referencing with `.ai/` docs
- **No file modifications** during audit (except splash/auth fixes applied separately)
- **Baseline**: HEAD `a0e11ac1`, working tree 333 dirty entries

---

## Key Findings Summary

| Category | Critical | High | Medium | Low | Clean |
|----------|----------|------|--------|-----|-------|
| Security | 4 | 6 | 10 | 4 | — |
| Architecture | 6 duplications | 3 inversions | 74 untested pkgs | — | — |
| Data | 2 critical (no money SQL, memory-only tracker) | 2 | 5 | — | — |
| Desktop | 2 bugs (splash, auth) | — | — | — | Fixed |
| Frontend | 41 dead components | 77 raw fetch bypasses | 24 prop bugs | — | Fixed |
| Backend | 6 duplicate domains | 14 inversions | 74 untested pkgs | — | — |
| CI/CD | 0 workflows run tests | 1 CI bug (sidecar rename) | — | — | Fixed |

---

## Critical Findings (Must Fix Before Release)

### 1. Auth Bypass — 149 Mutating Endpoints Unauthenticated
**File**: `api/middleware/auth_middleware.py:49-50`
```python
if not path.startswith("/api/"):
    return await call_next(request)
```
29 root-mounted routers (282 endpoints, **148 mutating**) bypass auth entirely. Only mitigation: binds `127.0.0.1`. **If `--host 0.0.0.0`, fully exposed.**

### 2. Economic History Not Persisted
`RevenueTracker` (2,416 LOC) is **memory-only**. No DB tables for money (21 tables, 0 financial). Recovery only from `workbank.json` + `submission_queue.json`. **Restart = total money history loss** except what's in JSON.

### 3. Auth Contract Broken (Fixed)
`autoLogin` read `res.session.token`; backend returns `APIEnvelope{data:{token}}`. **Fixed in `auth.ts`** — now reads `res.data.token`. Test rewritten to real shape.

### 4. Vault Key Silent Regeneration
`cores/vault_crypto.py:45-48` overwrites key on any read error. **Permanent credential loss**. Only `logger.warning` (not wired to file). `~/.orion/identity_vault.key` = **single most critical backup file**.

### 5. Auth Bypass on Root-Mounted Routes
29 routers at root (282 endpoints, 148 mutating) bypass auth. Only `127.0.0.1` bind mitigates.

### 6. Ungated Bounty Claims
3 live paths claim bounties with no human gate: Opire, IssueHunt, generic workflow engine.

### 5. `clearSession()` on ANY 401 → Cascading Failures
First 401 (even from raw fetch) → `clearSession()` → token wiped → 30 more 401s. **Fixed**: only clears if token was actually sent.

---

## Architecture Assessment

### Duplication Crisis (6 Domains)

| Domain | Implementations | LOC | Resolution |
|--------|----------------|-----|------------|
| Opportunity Discovery | 4 layers | ~30K | Consolidate to 1 registry + adapters |
| Validation | 6 implementations | ~8K | Consolidate to 1 ValidationService |
| Scheduling | 10 classes, 3 registries | ~3K | 1 canonical scheduler |
| Revenue Tracking | 6 implementations | ~15K | 1 canonical RevenueEngine |
| Opportunity Adapters | 4 layers | ~30K | 1 registry + adapters |
| Scheduling | 10 classes, 3 registries | ~3K | 1 canonical |

### Layering Violations
- **14** `cores/` → `api/` imports (inversion)
- **2** `api/` → `desktop/` imports
- `api/main.py:443` monkey-patches `include_router` to discard `prefix`/`tags`

---

## Data Integrity

### No Financial SQL Tables
21 tables, **0 financial**. All money in JSON (`~/.ownex/`) + memory (`RevenueTracker`).

### Data Store Fragmentation
- **5 distinct roots**: `~/.ownex/`, `~/.orion/`, `~/.config/ownex/`, `<repo>/data/`, `database/`
- **190** distinct store filename literals in source
- **11,057** test DBs polluting `~/.ownex/database/`
- **No registry** — 190 distinct filename literals in source

### `RevenueTracker` Memory-Only
```python
class RevenueTracker:
    def __init__(self):
        self.opportunities = {}
        self.transactions = []
        self.metrics = {}
```
No persistence. Recovery only from `workbank.json` + `submission_queue.json`.

---

## Frontend Health

| Metric | Value |
|--------|-------|
| `.vue` files | 217 |
| Routes | 97 (0 collisions, 0 chains) |
| Dead components | 41/128 (32%) |
| Dead stores | 2/9 |
| Dead composables | 9/21 (43%) |
| Dead services | 2/6 |
| Raw fetch bypasses | 77 calls / 25 files |
| Unresolved identifiers | 21 in 6 files |
| Build | ✅ 12-15s |
| `vue-tsc` | ✅ 0 errors |
| Vitest | 17/17 passed (191 tests) |

**Critical**: `IncomeHome.vue` (Command Center) had 4 unresolved identifiers (`useHuntStore`, `api`, `Card`, `Badge`) — **fixed**.

---

## Desktop (Tauri v2) Status

| Component | Status |
|-----------|--------|
| Build | ✅ Release (55s, 0 warnings) |
| Launch | ✅ Window 1400x900 opens |
| Sidecar | ✅ Spawns, `/api/health` + `/today` + `/mission-hub/overview` + `/direct-work/workbank` → 200 |
| WebView → Backend | ✅ HTTP/WS on sidecar port |
| Auth (Bearer) | ✅ Works (cookie fails cross-site) |
| WebSocket | ❌ 403 (cookie Lax cross-site) — known |
| Splash screen | ✅ Fixed (fallback timeout) |
| Auth in Tauri | ✅ Fixed (Bearer works) |

**Critical**: Sidecar binary from 2026-09-05 (26 commits stale). Auth endpoint unchanged since Aug 14 → works. **Must rebuild** for other fixes.

---

## CI/CD Status

| Job | Status |
|-----|--------|
| `test.yml` | Build only (no tests) |
| `ci.yml` | Lint + build, **no typecheck, no tests, no Playwright** |
| `release.yml` | Build only |
| `ownex-tauri-windows.yml` | Windows sidecar smoke only |
| **New** `test-e2e` | Added to verify gate |

**Critical gaps**: No `vue-tsc`, no `vitest`, no `playwright` in CI. `--cov=core` references deleted `core/` dir.

---

## Test Baselines

| Suite | Before | After Fixes |
|-------|--------|-------------|
| `vue-tsc --noEmit` | 0 errors | 0 errors |
| `vitest` | 2 suites red (Dashboard/Findings) | 17/17 passed (191 tests) |
| `npm run build` | ✅ | ✅ |
| `make test-fast` | 103 passed / 1 skipped | 103 passed / 1 skipped |
| Playwright (dev) | 8 tests (vacuous) | 28/28 passed |
| Playwright (prod) | N/A | 28/28 passed |

---

## Economic Model Health

### The $3.97M Phantom Pipeline
- Found in `ProgressiveScaling.vue` and `cores/economic_trajectory/`
- Sums rewards across opportunities **without filtering by state/eligibility**
- Presented as "pipeline" but includes unqualified, ineligible, unpaid

### Money State Confusion (6 Parallel Implementations)
| Implementation | `realized` | `pending` | `pipeline` | `expected` |
|----------------|------------|-----------|------------|------------|
| `cores/revenue/` | ✅ | ✅ | ✅ | ✅ |
| `revenue_tracker` | ✅ | ✅ | ✅ | ❌ (memory) |
| `economic_feedback` | ❌ | ❌ | ✅ | ❌ |
| `financial/` | ✅ | ✅ | ✅ | ✅ |
| `revenue_multiplier` | ❌ | ❌ | ❌ | ❌ |
| `direct_work_engine` | ✅ | ✅ | ✅ | ✅ |

**No single source of truth** — each computes differently.

### P(CASH) = UNKNOWN Until First PAID
- Correctly implemented in `Mission.vue` / `PublicWork.vue` → shows `'—'` / `'UNKNOWN'`
- But `IncomeHome.vue` renders `|| 0` / `|| '$0'` → **lies to user**

---

## Test Baselines (Verified)

| Suite | Count | Status |
|-------|-------|--------|
| `vue-tsc --noEmit` | 0 errors | ✅ |
| `vitest run` | 17 files, 191 tests | 17/17 passed |
| `npm run build` | ✅ | 12-15s |
| `make test-fast` | 103 passed, 1 skipped | ✅ |
| Playwright (dev) | 28 tests | 28/28 passed |
| Playwright (prod) | 28 tests | 28/28 passed |

---

## Risk Summary

| Level | Count | Examples |
|-------|-------|----------|
| **CRITICAL** | 4 | Auth bypass, memory-only revenue, vault key regen, ungated claims |
| **HIGH** | 6 | Test data contamination, hardcoded paths, license HWID, vault key regen, sidecar stale, license HWID |
| **MEDIUM** | 10 | Unauthenticated clear_all, destructive reindex, non-atomic rollback, dead commenter, fake auto-submit, fake screenshot, placeholder rebuild, key logging, .env 644, push token |
| **LOW** | 4 | CORS wildcard, devin endpoints, hardcoded ports, TODOs |

---

## Migration Readiness

**Safe to migrate IF three conditions met:**
1. `~/.orion/identity_vault.key` backed up (single most critical file)
2. `OWNEX_DATA_DIR` fully copied (all economic JSON)
3. **Do not bind `0.0.0.0`** until auth bypass fixed

**Additionally**: Plan HWID rebind (license), fix `content_factory` hardcoded path.

---

## Recommendation

**PROCEED TO PHASE 1 (PRODUCT RESET)** — but **DO NOT START PHASE 2** until:
1. `PRODUCT_ONE_PAGE.md` written and approved (STOP CONDITION)
2. Auth bypass on root-mounted routes fixed or explicitly accepted
3. `RevenueTracker` persistence designed
4. Vault key regeneration bug fixed
5. Sidecar rebuilt from current backend

**Estimated effort to production-ready desktop**: 3-4 weeks with 1 engineer, following the 14-phase plan with gates.

---

## Appendix: Key File Locations

| Artifact | Path |
|----------|------|
| Frontend entry | `frontend/src/main.ts` |
| Auth store | `frontend/src/stores/auth.ts` |
| API client | `frontend/src/lib/api.ts` |
| Backend config | `api/main.py` |
| Auth middleware | `api/middleware/auth_middleware.py` |
| Revenue tracker | `cores/revenue_tracker/revenue_tracker.py` |
| Vault crypto | `cores/vault_crypto.py` |
| Sidecar spec | `OWNEX-Backend.spec` |
| Tauri config | `src-tauri/tauri.conf.json` |
| Sidecar spec | `OWNEX-Backend.spec` |
| CI workflows | `.github/workflows/*.yml` |
| Audit docs | `.ai/docs/audit/*.md` |
| Product definition | `.ai/docs/audit/PRODUCT_ONE_PAGE.md` (to create) |