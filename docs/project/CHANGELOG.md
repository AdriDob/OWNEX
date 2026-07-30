# CHANGELOG — OWNEX OMEGA

**All notable changes. Auto-updated per session from git + investigation.**

---

## [7.0.1] — 2026-07-30 — Security Cycle Fix + Living Documentation System

### Added
- **Living Documentation System** (`/docs/project/`) — 12 files, single concern each, evidence-based
  - `CURRENT_STATE.md` — Real project state from code investigation
  - `PROJECT_STATUS.md` — 85% global with evidence justification
  - `ROADMAP.md` — Authoritative progress from COMPLETED_FEATURES.json
  - `ARCHITECTURE.md` — 500+ lines, full architecture from code
  - `MODULE_INDEX.md` — 120+ modules cataloged (backend, frontend, extensions, DB, API)
  - `PROGRESS.md` — Evolution tracking from FASE_25 (2026-07-23)
  - `DECISIONS.md` — 19 architectural decisions with evidence
  - `KNOWN_LIMITATIONS.md` — 30+ honest limitations with fix mapping
  - `TECH_DEBT.md` — 35 debt items with evidence, paydown strategy
  - `NEXT_PRIORITIES.md` — Auto-ordered by Revenue Rule formula
  - `SESSION_HISTORY.md` — Chronological session record with template
  - `CHANGELOG.md` — This file, updated

### Fixed
- **Security Cycle category bug** — `test_ensure_cycle` expected `category=="security"`, core created `"offensive"`
  - Root cause: `CycleCategory.OFFENSIVE = "offensive"` ≠ `CycleCategory.SECURITY = "security"`, used inconsistently
  - Fixed in 4 files: `core/cycles/security.py` (2 locations), `core/cycles/models.py`, `core/cycles/registry.py`
  - Database record updated: `id=1, category=security, status=running` (verified via `check_cycle.py`)
  - Result: **All 44 backend tests pass (100%)**

### Changed
- `.ai/TASK_QUEUE.md` — Rewritten from investigation (was 291 chars stale, now 9.5KB real state)
- `.ai/CURRENT_STATE.md` — Updated with real state
- Project global %: **83% → 85%** (Security Cycle test fixed, living docs created)

### Tests
- Backend: **434/434 pass (100%)** — was 433/434
- Frontend: **All pass**

---

## [7.0.0] — 2026-07-30 — Self-Evolution Constitution & OMEGA Autonomy Framework

### Added
- **OMEGA Constitution** — DESIGN → PREPARE → VALIDATE → PROPOSE governance
- **Evolution Engine** (`core/evolution/`) — 9 modules: analyze, engine, design, infra_auditor, self_healer, self_tester, supervisor, tech_watcher, update_engine
- **Evolution API** (`api/routers/evolution.py`) — 5 endpoints (stubs)
- **Self-Evolution Memory** — persistent proposals, votes, executions

### Changed
- `AGENTS.md` — OMEGA Constitution integrated, Revenue Rule formalized
- `TASK_QUEUE.md` — rewritten from investigation (was 291 chars stale)
- Architecture Budget enforced: max 2 files, 1 dep, 1 event, 1 capability, 1 contract, 20 tests/feature

### Fixed
- None (foundation release)

---

## [6.5.0] — 2026-07-26 — Opportunity Score Engine (Phase 1)

### Added
- `core/opportunity/` — Unified scorer across Security, Forge, Pulse, Vault, Atlas
- `core/opportunity/scorer.py` — EV, acceptance, difficulty, competition, fit, confidence
- `core/opportunity/top5.py` — Top5Engine: exactly 5 diversified recommendations
- `core/opportunity/personal.py` — PersonalHistoryTracker from RevenueMetrics
- `api/routers/opportunity_score.py` — 5 endpoints
- `tests/test_opportunity_core.py` — 23 tests, 100% pass

### Revenue Rule
✅ Detection + Acceptance + Learning

---

## [6.4.0] — 2026-07-24 — Censys, Crypto TA, Smart Notifications, Revenue Intel

### Added
- `cores/tools/censys.py` — Asset discovery, certificate transparency (TOOL_REGISTRY)
- `cores/crypto/coingecko.py` — RSI, SMA, MACD, `get_technical_signals()` with interpretation
- `core/notifications/intelligent.py` — SmartNotificationManager (14 EventBus events)
- `api/routers/notifications.py` — 3 endpoints (GET /smart, GET+POST /smart/config)
- Revenue Intelligence: USD/hour in RevenueMetrics, dynamic platform speed in TargetPrioritizer, USD/hour in scheduler EV log

### Tests Added
- Target Intelligence: 22 tests
- Revenue Pipeline: 31 tests
- Scheduler: 17 tests
- **Total: 70 new tests**

---

## [6.3.0] — 2026-07-23 — FASE_18-25: Offensive + Evidence + Quality + Expansion (Revenue Ready)

### FASE_18: Offensive Intelligence + Evidence + Quality
- `core/offensive/` — 5 reasoners (IDOR, Auth Bypass, SSRF, XSS, SQLi) — **101 tests**
- `core/evidence/composer.py` — PoC, requests, responses, curl, Python exploit, timeline, CVSS, CWE, CAPEC, OWASP, MITRE, report readiness — **37 tests**
- `api/routers/reports_quality.py` — Report Quality Gate + Acceptance Optimizer
- `core/evolution/` — 9 modules (stubs)
- `api/routers/evolution.py` — Evolution API
- `api/routers/mission.py` — Mission Control API + `MissionControl.vue` (7 real endpoints)
- `api/routers/copilot.py` — Copilot API router
- `core/workflows/` — Workflows Engine
- `apps/aegis/` + `frontend/src/apps/aegis/` — Aegis security app
- `core/sync/` — Sync Engine
- `core/finance/` — Finance Core
- `core/reports/` — Reports Core
- `core/documentation/` — Documentation Platform (18 auto-registered modules)
- `cores/tools/amass.py`, `naabu.py`, `shodan.py`, `uncover.py` — Tool adapters
- `cores/notifications/discord.py` — 12 Discord event types
- `cores/integrations/arca/`, `outlook/` — Integration connectors
- `src-tauri/` — Tauri Desktop app (Rust + WebView)
- `scripts/setup.sh` — Linux setup
- `scripts/install_desktop_tools.ps1` — Windows 33 tools via winget
- `api/routers/settings_unified.py` — Unified settings
- `frontend/src/components/ui/` — DataTable, Drawer, Modal, Select

### FASE_19: Hermes v2 Professional Desktop Agent
- `core/events/types.py` — 7 Hermes event types
- `apps/hermes/publisher.py` — HermesEventPublisher
- `apps/hermes/permissions.py` — 5 risk levels — **14 tests**
- `apps/hermes/security.py` — PS/Path/PID validation — **24 tests**
- `apps/hermes/engine.py` — Security pipeline integration
- **48 tests total**

### FASE_20: Command System Fase 1
- `core/commands/models.py` — 5 permission levels, flags
- `core/commands/registry.py` — 107 commands, 14 categories
- `core/commands/dispatcher.py` — Dispatcher + EventBus
- `api/routers/commands.py` — 6 endpoints
- `core/events/types.py` — 3 command event types
- **45 tests**

### FASE_21: Pipeline Hypothesis Fix + Stability
- Path-based hypothesis fallback (6 vuln types) in `api/scheduler.py`
- VULN_TYPE_MAP extended (file_upload, graphql) in `core/pipeline/hypothesis_bridge.py`
- Orphaned test DBs cleanup: 1303 → 8
- 12 Ruff fixes (SIM114, B007, B024)

### FASE_22: Report Acceptance Optimizer
- `core/reports/acceptance/learner.py` — AcceptanceLearner (prediction + adaptation)
- `api/routers/reports_acceptance.py` — 7 endpoints
- `core/events/types.py` — 3 acceptance event types
- **18 tests**

### FASE_23: Recon Intelligence
- `core/target_intelligence/prioritizer.py` — TargetPrioritizer (EV + tech + attack plans)
- `api/scheduler.py` — Budget-aware EV integration
- **22 tests**

### FASE_24: Expansion Execution Plan
- `.ai/TECHNOLOGY_SCOUT_REPORT.md`
- `.ai/EXPANSION_INTELLIGENCE_REPORT.md`
- `.ai/EXPANSION_EXECUTION_PLAN.md`
- `cores/tools/extra.py` — Sprint 0 tools (Gitleaks, Garak, BrowserUse) — **24 tests**
- 8 Expansion Memory entries

### FASE_25: Expansion Sprints 4-10 (Revenue Ready)
- **S-4:** AI Bounty Auto-Hunter (`core/auto_hunter/`) — 4 programs, 2h scheduler, EV ranking — **29 tests**
- **S-5:** Revenue Dashboard V2 (`RevenueDashboard.vue`, Targets by EV tab)
- **UX-1:** Baby Mode (`BabyMode.vue`) — 3 main action buttons
- **S-6:** Auto-Submission Pipeline (`core/auto_submit/pipeline.py`) — Quality Gate, platform detection, EventBus — **12 tests**
- **S-7:** Target Discovery Automator (`cores/bounty_scraper/`) — ProgramChangeTracker, payout ranking — **25 tests**
- **S-8:** Report Optimizer V2 (`core/reports/optimizer.py`) — RemediationDB (12 types), CWE_MAP, ReportContextBuilder — **23 tests**
- **S-9:** Auto-Recon Enhancement (`cores/recon/`) — NaabuRunner, centralized dedup, ReconRunner — **23 tests**
- **S-10:** Verdict Auto-Learner (`core/learning/verdict_learner.py`) — FeedbackTuner ↔ AcceptanceLearner bridge, auto-outcome recording — **14 tests**

### Global Impact
- Project: 63% → 78%
- **400+ tests passing**
- All Revenue Rule dimensions covered

---

## [5.3.0] — 2026-07-16 to 2026-07-22 — FASE_1 to FASE_17 (Foundation)

### FASE_1: Base Stabilization
- Evidence Upload API, Target Scan Trigger, PWA Assets, 32 bare except:pass → logged

### FASE_2: Modules Connected
- OpportunityEngine → EventBus, Scheduler + ORION Score, Findings → EventBus, AgentBus → EventBus bridge, 8 Ghost events fixed

### FASE_3: Pipeline E2E
- DISCOVER, RECON, HYPOTHESIS, VALIDATE, REPORT stages all working
- Auto-report subscriber: finding confirmed → report draft

### FASE_4: ORION Automation
- Auto-prioritization (Scheduler consults ORION.get_next_action)
- Auto-explanation logging, EVH scoring, RewardLearner feedback loop

### FASE_5: ORION Reasoning Layer
- Hypothesis Challenger: AlternativeExplainer (7 types), ContradictionTestDesigner, MissingVerificationsAnalyzer, uncertainty_penalty
- Evidence Graph: SQLite persistent, for/against/neutral, weight/confidence, edges, balance scoring
- FeedbackLearner pipeline: FeedbackTuner accumulates + applies weight adjustments — **12 tests**
- Adaptive Report Gate: pending

### FASE_6: Release Hardening (14 fixes)
- FinancialSyncScheduler event-loop fix, NotificationPoller stop flag, Watchdog bus fix, research.py imports, 14 DB indexes, 3 create_task orphans tracked, WAL checkpoint, CorrelationEngine dedup cache limit, ensure_future error logging, cooldown prune, open() → with open(), audit.jsonl rotation (10MB, 3 backups)

### FASE_7: ORION Platform v4.0.0
- Extension SDK: Manifest, hooks, capabilities, declarative settings, hot reload, failure isolation
- Secrets Manager: IdentityVault bridge (AES-256-GCM), env fallback, cache, REST API — **11 tests**
- Health Center: Unifies 3 legacy systems, green/yellow/red, snapshots, unified summary — **25 tests**
- AppRegistry bridge, Core API Endpoints (/extensions, /secrets, /health under /api/core)

### FASE_8: ORION Financial Layer
- CoinGecko price feed (30+ crypto, 24h change, cache, free tier)
- Takenos connector: Balance manual, CSV import, Solana USDC sync
- Unified Financial Dashboard: Patrimonio total, breakdown, objetivo libertad 30K, ingresos mes, alertas
- Financial Truth Layer: Dashboard endpoint, integrations status, reconciliation, withdrawal tracking
- Coinbase HMAC fix, Kraken portfolio fix

### FASE_9: Hermes Automation Agent
- EventBus events, publisher, permissions (5 levels), security (PS/Path/PID), engine integration

### FASE_10-17: Continuous Hardening + Features
- Progressive stabilization, test coverage expansion, UI components, integrations

---

## [4.5.0] — 2026-07-15 and Earlier — Pre-Formalization

### Key Milestones
- Initial FastAPI + Vue 3 setup
- SQLite + SQLAlchemy models
- Basic bug bounty pipeline concept
- Early EventBus implementation
- First scheduler iterations

---

## Changelog Format (For Future)

```markdown
## [X.Y.Z] — YYYY-MM-DD — <Title>

### Added
- <feature> — <evidence: tests, files, endpoints>

### Changed
- <modification> — <reason>

### Fixed
- <bug> — <root cause> — <fix>

### Removed
- <deletion> — <reason>

### Revenue Rule
✅/❌ <dimension(s)> — <justification>

### Tests
- <count> new, <count> total, <pass rate>%

### Migration Notes
- <breaking changes, config updates>
```