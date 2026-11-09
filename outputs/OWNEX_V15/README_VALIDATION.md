# README_VALIDATION — OWNEX V15

**Date:** 2026-11-09 · **Scope:** every quantitative/functional claim in the
rewritten `README.md`, checked against the tree at commit `c9efe41d`+.

## Claim-by-claim verification

| README claim | Verdict | Evidence |
|---|---|---|
| "150+ sources in catalog" | ✅ VERIFIED | `cores/opportunity/global_sources.py::get_sources()` returns **151** live (executed). README updated from stale "135+" |
| 5 real feeds: Remotive, Arbeitnow, RemoteOK, Jobicy, WeWorkRemotely | ✅ VERIFIED | `job_feeds.py`: `fetch_remotive` L41, `fetch_arbeitnow` L74, `fetch_remoteok` L104, `fetch_jobicy` L139 (geo=argentina default), `fetch_weworkremotely` L178, `FEEDS` registry L221 |
| explainable match score → profile → tracker → draft | ✅ VERIFIED | `remote_job_matcher.py`, `user_profile.py`, `job_tracker.py`, `application_drafter.py` all present; pipeline endpoints exist |
| endpoints `/remote-jobs/{search,save,saved,import,draft,transition}` | ✅ VERIFIED | `api/routers/opportunities.py` L37–122 |
| employment classification + `OWNEX_REMOTE_JOBS_SCOPE` | ✅ VERIFIED | `cores/opportunity/employment.py`, `income_plan.py` (commit `5276a65f`) |
| income plan unified | ✅ VERIFIED | `cores/direct_work_engine/income_plan.py`, `tests/test_income_plan.py` exists |
| IOL/PPI/Binance read-only INTEGRATION_PENDING | ✅ HONEST | `cores/connections/`, `api/routers/connection_manager.py` exist; no live-credential validation on record |
| income→ledger bridge, explicit action | ✅ VERIFIED | `cores/ledger/`, `tests/test_financial_connections.py` exists |
| MCP server: 9 read-only tools + consent + audit | ✅ VERIFIED | `core/mcp_ownex_server.py`: `TOOLS` list has exactly 9 `Tool(` entries (L37–101), `mcp_consent.check_tool_allowed` L260 |
| scheduler canonical `core/scheduler/jobs.py` | ✅ VERIFIED | per twin-tree audit; runtime uses core copy |
| security pipeline DRY_RUN default | ✅ VERIFIED (code) | `core/trading/` exists; live opt-in documented |
| frontend ~79 pages, `vite build` green | ✅ VERIFIED (count corrected) | 79 `.vue` files in `frontend/src/pages/`; router has 141 `path:` records (nested). README says "~79" — accurate for page components |
| desktop Tauri v2 + PyInstaller sidecar | ✅ BUILD_VERIFIED | `src-tauri/`, `desktop/` exist |
| Android BUILD_VERIFIED | ⚠️ DOWNGRADED confidence | `android/` Gradle project + prior build intermediates exist; **appId mismatch found** (`capacitor.config.json` = `ownex.desktop.app` vs `build.gradle` = `ai.rastro.app`) — see ANDROID_WEAROS_UPDATE.md §1. Build claim stands for past artifacts; next build needs the ID fix |
| Wear OS EXPERIMENTAL | ✅ HONEST — corrected from old "Completed" | `cores/wear_os/integration.py` is backend-only; NO watch app/module exists |
| quant PLANNED | ✅ VERIFIED | `core/quant/`, `cores/quant/` dirs exist, empty |
| Upwork EXCLUDED | ✅ VERIFIED | removed from active catalog V12.1 |
| License section (MIT vs proprietary, pending) | ✅ HONEST | `LICENSE` = MIT (commit `5ae7280e`); contradiction documented, no false claim |
| install commands (`run.py`, `install.py`, `npm run dev`) | ✅ VERIFIED | all files exist; `Makefile` targets `test`/`test-fast`/`check`/`fmt` confirmed |
| "~4,500 tests" — NOT claimed in README | ✅ avoided | `def test_` count ≈ 4,451 across `tests/`; suite result varies with env-dependent exclusions — deliberately omitted from README |

## Corrections applied to README during validation

1. "135+ sources" → **"150+ sources"** — `get_sources()` executed → 151.
2. Page count → "79 page components / 140+ routes" (router `path:` records
   = 141 including nested entries).
3. Android row links the appId-mismatch finding rather than overclaiming.

## Still unverified (honest residue)

- ~~Exact source-catalog size~~ — resolved: 151.
- Whether `core_event_log` has readers outside `core/events/` (checked:
  none found — only the bus itself).
- Live credential validation for IOL/PPI/Binance — external blocker.
- Windows installer artifacts on GitHub Releases — not checked from CLI.
