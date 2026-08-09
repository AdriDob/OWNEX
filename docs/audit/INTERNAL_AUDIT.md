# OWNEX — Internal System Audit (2026-08-09)

> Classification: **EXISTENTE** (present, not yet wired) / **IMPLEMENTADO** (verified working)
> / **PARCIAL** (exists but incomplete) / **EXPERIMENTAL** (engine + tests, not exposed) /
> **DESCARTADO** (deliberately dropped).
> Every claim cites the verified source (module path or test file). No claims without evidence.

---

## 1. Core Platform (core/ + cores/)

| System | Class | Evidence |
|---|---|---|
| FastAPI application + middleware stack (auth, CSRF, rate limit, error handling) | IMPLEMENTADO | `api/main.py`, `tests/test_auth*` |
| Run pipeline bug bounty real (discover→recon→hypothesis→validate→report→ai_bounty) | IMPLEMENTADO | `api/scheduler.py` (`ScanScheduler`) runs in runtime |
| 7-stage Security Cycle with `run_pipeline()` | IMPLEMENTADO | `core/cycles/security.py`, `tests/test_e2e_security_pipeline.py` (8 passed) |
| QA Cycle engine + router + scheduler job | IMPLEMENTADO | `core/cycles/qa.py` (1151 L), `api/routers/qa_cycle.py`, `tests/test_qa_cycle_api.py` (7 passed) |
| Scheduler runtime (cron-aware, 28 jobs, event `scheduler:job_due`) | IMPLEMENTADO | `api/main.py` + `core/scheduler/jobs.py`, `tests/test_scheduler_jobs.py` (54 passed) |
| CoreEventBus + bridge to legacy event bus | IMPLEMENTED | `core/event_bus/`, persistence SQLite |
| Unified Memory (10 namespaces, SQLite) | IMPLEMENTED | `core/memory/store.py`, `tests/test_unified_memory.py` (24 passed) |
| Decision Journal | IMPLEMENTED | `core/decision_journal/` |
| Health Center (snapshots persisted) | IMPLEMENTED | `core/health/engine.py`, `api` `/api/core/health/summary` |
| IdentityVault (AES-256-GCM, random key, chmod 600) | IMPLEMENTED | `cores/identity_vault.py`, `tests/test_*vault*` |
| License validator (Ed25519) | IMPLEMENTED | `cores/license/validator.py`, 355 tests green (baseline) |
| Version backup + rollback (SQLite RecoveryStore) | IMPLEMENTED | `cores/version_backup/backup_system.py`, `tests/test_version_backup.py` (24 passed) |
| Cloud backup (S3/GCS, optional) | PARCIAL | `cores/cloud_backup/` — code complete, no credentials configured |
| OAR AI runtime (registry, router, cost, failover, cache) | IMPLEMENTED | engine + `cores/ai/runtime/` ; mounted API routers `/oar/*` |
| Career Engine (skill gaps, roadmap, training) | IMPLEMENTED | `cores/career_engine.py`, `api/routers/career.py`, 14 tests |
| Merlin assistant (office-retro, persistent memory, voice) | IMPLEMENTED | `cores/merlin/`, `MerlinInterface.vue` / `MerlinJarvis.vue` |
| Direct Work Engine (zero-barrier scoring, recommender, feedback loop) | IMPLEMENTED | `cores/direct_work_engine/`, `tests/test_direct_work_engine.py` (35 passed) |
| Work Bank (ready-to-deliver queue, success floor) | IMPLEMENTED | `cores/direct_work_engine/workbank.py`, `tests/test_workbank.py` (17 passed) |
| Daily Companion (one-call briefing) | IMPLEMENTED | `cores/direct_work_engine/daily_companion.py`, 7 tests |
| Market Evolution (OVOS, friction, retirement, KB) | IMPLEMENTED | `cores/direct_work_engine/market_evolution.py`, `tests/test_market_evolution.py` (21 passed) |
| Evolution / Learning layer (skill gaps, capabilities, performance) | IMPLEMENTED | `cores/direct_work_engine/evolution.py` |
| Income Dashboard + projection | IMPLEMENTED | `cores/direct_work_engine/income_dashboard.py` |
| Result-based opportunity model (S/A/B/C + first-day guide) | IMPLEMENTED | `cores/result_based.py` |
| Fiverr strategic engine + ethics gate | IMPLEMENTED | `cores/fiverr/engine.py` |
| Auto-submit pipeline (H1/BC/Intigriti) | IMPLEMENTED | `cores/auto_submit/pipeline.py` |
| CoderAgent + autonomous workflows | IMPLEMENTED | `core/autonomy/` (5 components), tests |
| Credentials Vault | IMPLEMENTED | `core/credentials/vault.py` |
| Tool Ecosystem Management + usage tracking | IMPLEMENTED | `cores/tools/ecosystem.py`, `TOOL_REGISTRY` (19 tools) |
| Tool Ecosystem — allowed list scan | PARCIAL | parts covered by registry checks, no OS-level sandbox |

---

## 2. Work Cycles (7)

| Cycle | Classification | Evidence |
|---|---|---|
| **Security** | IMPLEMENTADO | `core/cycles/security.py` + stages; dashboard `api/cycles/security/dashboard` |
| **Forge** (dev bounties) | IMPLEMENTADO | `core/cycles/forge.py` + `api/routers/forge_cycle.py` (mounted, status/dashboard/knowledge 200) |
| **Pulse** (AI work) | IMPLEMENTADO | `api/routers/pulse_cycle.py` (mounted) |
| **Vault** (wealth) | IMPLEMENTADO | `core/cycles/vault.py` + `api/routers/vault_cycle.py` (8 endpoints) |
| **Atlas** (intelligence) | IMPLEMENTADO | `core/cycles/atlas.py` + `api/routers/atlas_cycle.py` (8 endpoints) |
| **QA** | IMPLEMENTADO | `api/routers/qa_cycle.py`, job `qa_daily_cycle` |
| **Direct Work** | IMPLEMENTADO | `core/scheduler/jobs.py` `work_bank_daily_cycle` |
| LOLA cycles share status/dashboard API contract | IMPLEMENTADO | `api/cycles/*` + `tests/test_scheduler_jobs.py` (28 jobs) |

---

## 3. Frontend (Vue 3 + TS)

| Area | Classification | Evidence |
|---|---|---|
| Mission Control + mission-control components (NextBestAction, AgentFleet, OpportunityRadar, DirectWorkRadar, GoodMorning) | IMPLEMENTADO | `frontend/src/pages/MissionControl.vue` + `components/mission-control/` |
| Executive Dashboard (CEO view) | IMPLEMENTADO | `frontend/src/pages/ExecutiveDashboard.vue`, route `/security/executive` |
| Direct Work/Earn-work radar + Work Bank UI | IMPLEMENTADO | `DirectWorkRadar.vue` (3 rows in MissionControl) |
| Good Morning panel | IMPLEMENTADO | `GoodMorning.vue` mounted in MissionControl |
| MERLIN interface | IMPLEMENTADO | `MerlinInterface.vue` + `MerlinJarvis.vue` |
| Terminal (xterm.js + WS) | IMPLEMENTADO | `TerminalView.vue`, `api/routers/terminal_ws.py` |
| Welcome page (no-JARVIS) | IMPLEMENTADO | `WelcomePage.vue` (`/`); legacy JARVIS pages orphaned |
| DevOps: `vite build` OK, `vue-tsc` 0 err courtesy | IMPLEMENTADO | session verification 2026-08-04 |
| 254 tsc pre-existing fails on orphan pages | DEUDA KNOWN | see `.ai/KNOWN_DEBT.md` (pages without routes, not part of it) |
| Mobile companion (Capacitor Android) | IMPLEMENTADO | `android/` APK debug builds (namespace `ai.rastro.app`) |
| OMEGA mobile (Expo RN) | PARCIAL | `omega/` functional skeleton (Expo ~51, RN 0.74), not published |
| Wear OS smartwatch app | DESCARTADO | ROI-negative (commit `c420f8fb`); protocol defined in `ORION_SETUP_GUIDE.md` |

---

## 4. Desktop & Distribution

| Item | Classification | Evidence |
|---|---|---|
| Tauri v2 desktop shell | IMPLEMENTADO | `src-tauri/` — `cargo check` OK (AUD-13) |
| PyInstaller sidecar | IMPLEMENTADO | `dist/CATEYE` release artifact |
| Installer (WiX/NSIS) | PARCIAL | Windows packaging exists, unsupported for other OS |
| Android APK debug | IMPLEMENTADO | build verified 31-07 |

---

## 5. Data & Persistence

| Item | Classification | Evidence |
|---|---|---|
| SQLite dev / PostgreSQL prod (single DB) | IMPLEMENTADO | `database/db.py` (`SessionLocal`, tables) |
| Memory/knowledge persistence across restarts | IMPLEMENTADO | SQLite-backed MemoryStore + UnifiedMemory |
| Snapshots health persisted | IMPLEMENTADO | `health_snapshots` + `SystemState` |
| version-backups rotation (max 10) | IMPLEMENTED | `VersionBackupSystem` |
| Opportunity/market KB persisted (JSON) | IMPLEMENTED | `data/market_kb.json`, `data/workbank.json` |

---

## 6. Brand & Presentation

| Item | Classification | Evidence |
|---|---|---|
| Brand O+X mark + logo system | IMPLEMENTADO | `scripts/brand/generate_ownex_logo.py`, `docs/assets/branding/logo/` |
| Hero banner + OG social preview | IMPLEMENTADO | `scripts/brand/generate_ownex_banners.py`, `.github/social-preview.*` |
| Real product screenshots (Playwright) | IMPLEMENTADO | `scripts/capture_screenshots.mjs`, 9 desktop captures |
| Architecture diagram (Mermaid, embedded in README) | IMPLEMENTADO | `docs/assets/diagrams/architecture.mmd` + README block |
| Professional README (EN) | IMPLEMENTADO | `README.md` (v7.0.0) |
| Design tokens SSOT | IMPLEMENTADO | `assets/branding/design-tokens.json` (v3) + `themes/tesla.json` |
| Reproducible pipeline + validation | IMPLEMENTADO | `scripts/brand/regenerate.sh` (logo → banner → optimize → validate) |
| Legacy branding v2 (comfyui/FLUX) | DESCARTADO | removed (commit `c3ec593`) |
| Legacy brand assets v2 in `assets/logos` | REFACTORING | synced by pipeline `regenerate.sh` |

---

## 7. Tests & Quality

| Suite | Classification | Evidence |
|---|---|---|
| pytest (broad baseline) | 3154 passed / 14 failed pre-existing | session 2026-08-08, stash-verified unrelated |
| make check / dev check | IMPLEMENTADO | ruff 0 + mypy scoped + fast tests green |
| E2E pipeline (recon→evidence→report) | IMPLEMENTADO | `tests/test_e2e_security_pipeline.py` (8 passed) |
| test_security.py / test_vision_gateway.py / network tests | EXTERNAL (not CI) | deliberate exclusion in `make test` (debt #11) |

---

## 8. Open items / Known debt (excerpt)

See `.ai/KNOWN_DEBT.md` for full list. Top drivers:

1. Two trees `core/` vs `cores/` — decided `cores/` as SSOT, migration in progress (AUD-11).
2. 14 pre-existing suite failures unrelated to product code (documented).
3. Frontend orphan pages (not route-linked) + 254 pre-existing tsc errors (pages without maintenance; not in scope of the presentation).
4. OAR AI runtime router not yet exposed via `/api` (decision documented 2026-08-04).
5. SSOT caveat: `assets/logos` legacy copy kept in sync by `regenerate.sh` and marked deprecated.

---

*Audit date: 2026-08-09 — OWNEX v7.0.0 — source of truth `.ai/`*