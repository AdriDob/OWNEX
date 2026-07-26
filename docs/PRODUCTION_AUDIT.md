# Production Audit — ORION / Rastro v4.5.0

> **Date**: 2026-07-21
> **Python**: 3.14.4 (target: 3.10+)
> **Backend tests**: 1,787 pass / 13 fail / 8 error / 2 xfail (1,810 collected)
> **Frontend tests**: 157 pass / 8 fail (165 collected)
> **Frontend build**: ✅ Clean (TypeScript + Vite)
> **Lines of code**: ~170,420 Python, ~143 Vue components, 66 frontend pages
> **API endpoints**: 551 defined

---

## Architecture Overview

```
Rastro/
├── api/              # FastAPI application (routers, middleware, scheduler)
├── core/             # ORION platform modules (60+ subdirs, newer)
├── cores/            # CATEYE legacy modules (60+ subdirs, original)
├── apps/             # Hermes, Aegis, and other apps
├── database/         # SQLAlchemy models + DB setup
├── frontend/         # Vue 3 + TypeScript + Tailwind v4
├── desktop/          # Watchdog, tray icon
├── extensions/       # Extension SDK examples
├── docs/             # Documentation
├── scripts/          # Setup, install, Windows helpers
├── src-tauri/        # Tauri v2 desktop shell
└── tests/            # pytest + vitest suites
```

### Known architectural risks

- **Dual `core/` + `cores/` packages** — modules exist in both (e.g., `core/events/` + `cores/events/`, `core/validation/` + `cores/validation/`). Import paths are ambiguous.
- **No declared dependencies** — `pyproject.toml` has no `[project.dependencies]` section. All deps come from `requirements.txt` or implicit.
- **4 `core/` subpackages missing `__init__.py`** — `core/revenue/`, `core/plugin/`, `core/sync/`, `core/documentation/`.

---

## 🔴 CRITICAL — Blocks server boot

### C1. Missing `cores/recovery/health_monitor.py`

| Field | Value |
|---|---|
| **File** | `cores/recovery/health_monitor.py` |
| **Impact** | **Server cannot start.** 8 test errors. 1 collection error. Pipeline report generation blocked. |
| **Cause** | File was deleted during HealthCenter consolidation (FASE 6), but `cores/recovery/__init__.py:16` still imports from it. |
| **Cascade** | `api/main.py` → `api/routers/canonical.py` → `cores.intelligence.unified_orchestrator` → `cores.intelligence.reward_learning` → `cores.recovery.__init__` → 💥 |
| **Fix** | Restore file from git (`3aee7c1`) — it's a thin compatibility wrapper that delegates to `HealthCenter` in `core/health/engine.py`. |

---

## 🟠 HIGH — Runtime errors

### H1. Python 3.12 f-string syntax in `cores/health/engine.py`

| Field | Value |
|---|---|
| **File** | `cores/health/engine.py:107,123` |
| **Issue** | `f"{api_health_url.rsplit("/api/health", 1)[0]}/api/..."` — nested quotes inside f-strings require Python 3.12+. |
| **Impact** | SyntaxError on Python 3.10/3.11. Works on current 3.14 but violates project target. |
| **Fix** | Extract `base_url = api_health_url.rsplit("/api/health", 1)[0]` to a variable before the f-string. |

### H2. Missing `text` import in `cores/health/engine.py`

| Field | Value |
|---|---|
| **File** | `cores/health/engine.py:141` |
| **Issue** | `session.execute(text("SELECT 1"))` — `text` is not imported from SQLAlchemy. |
| **Impact** | `NameError` when DB health check runs. |
| **Fix** | Add `from sqlalchemy import text` to imports. |

---

## 🟡 MEDIUM — Test failures & lint

### M1. 12 Ruff errors (6 auto-fixable)

| File | Errors | Category |
|---|---|---|
| `api/scheduler.py` | 5 | Unused imports (2), unsorted imports, mid-file import, unused loop vars (2) |
| `cores/health/engine.py` | 5 | Unsorted imports, invalid f-string syntax (2), undefined `text` |
| `desktop/watchdog.py` | 1 | Unused `os` import |

**Auto-fixable**: 6 errors (F401, I001). **Manual**: 6 errors (B007, E402, invalid-syntax, F821).

### M2. 8 pre-existing backend test errors (all from missing `health_monitor.py`)

| Test | Root cause |
|---|---|
| `test_agents.py::TestAgentAPI` (8 tests) | ModuleNotFoundError cascade from `health_monitor` |

Once C1 is fixed, these 8 errors become passes.

### M3. 13 pre-existing backend test failures

| Test | Root cause | Severity |
|---|---|---|
| `test_backup.py::test_backup_create_endpoint` | Timeout (>60s, needs ~95s) | Low |
| `test_defi_tracker.py::test_strategy_zero_protocols` | Math bug (0 != 12 with 0 protocols) | Low |
| `test_feedback_pipeline.py` (2 tests) | Singleton state leak between tests | Low |
| `test_financial_hub.py` (2 tests) | Pre-existing | Low |
| `test_hermes.py::test_backup_attempts_execution` | Timeout | Low |
| `test_updates.py::test_prepare_update_creates_backup` | Pre-existing | Low |
| `test_vision_gateway.py::test_mcp_describe_image` | Assertion error | Low |
| `test_widget_system.py` (4 tests) | 404 on `/api/core/widgets` | Low |

All are pre-existing. None were introduced by current work.

### M4. 8 frontend test failures (vitest)

| Test | Root cause |
|---|---|
| `Dashboard.test.ts` (1) | KPI rendering with data |
| `MissionControl.test.ts` (5) | Error state, empty state, KPIs, toggle, stats |
| `settings.test.ts` (2) | localStorage init, API key merge/sync |

### M5. `api/routers/agents_router.py` naming

`api/routers/agents_router.py` exists (not `agents.py`). The `test_agents.py` tests use `TestClient(app)` — they don't import the router directly, so naming is not a blocker. However, the router name is inconsistent with other routers (most are `noun.py`, not `noun_router.py`).

---

## 🟢 LOW — Minor issues

### L1. 4 `core/` packages missing `__init__.py`

```
core/revenue/__init__.py       (missing)
core/plugin/__init__.py        (missing)
core/sync/__init__.py          (missing)
core/documentation/__init__.py (missing)
```

These packages can still be imported implicitly if Python finds them on `sys.path`, but explicit `__init__.py` is best practice for namespace packages.

### L2. No `[project.dependencies]` in `pyproject.toml`

Dependencies are managed via `requirements.txt` only, with no version pinning in `pyproject.toml`.

### L3. Desktop tests excluded

Tests for `desktop/vision_gateway.py` and `desktop/` hang in CI due to X server dependency.

---

## Detailed Findings

### Backend test suite

```
Collected: 1,810 (1 collection error from test_intelligence_loop.py)
Passed:    1,787
Failed:    13
Errors:    8
XFailed:   2
```

### Frontend test suite

```
Collected: 165
Passed:    157
Failed:    8 (3 test files)
```

### Frontend build

```
vite build:  Done in 30.78s
vue-tsc:     Clean (no errors)
```

### Server import test

```python
from api.main import app
# FAILS: ModuleNotFoundError: No module named 'cores.recovery.health_monitor'
```

---

## Immediate Fix Plan (Phase 1)

| # | Fix | Est. time | Risk |
|---|---|---|---|
| C1 | Restore `cores/recovery/health_monitor.py` from git | 5 min | Low — restores existing code |
| H1 | Fix f-string syntax in `cores/health/engine.py` | 5 min | Low — local extraction |
| H2 | Add `text` import to `cores/health/engine.py` | 2 min | Low — one-line add |
| M1 | Fix 12 Ruff errors | 15 min | Low — auto-fix + manual |
| — | Verify server boots | 5 min | — |
| — | Run full test suite | 30 min | — |

**Total**: ~60 min to clear all blockers.

After Phase 1: **1,809 tests pass** (from 1,787), **0 errors**, **server boots**, **pipeline unblocked**.
