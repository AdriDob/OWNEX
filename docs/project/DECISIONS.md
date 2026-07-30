# DECISIONS — OWNEX OMEGA

**Architectural decisions with evidence. Never lose context.**

---

## 2026-07-30: Living Documentation System

**Problem:** Project documentation (TASK_QUEUE.md, CURRENT_STATE.md, ROADMAP.md) was stale — 291 chars vs 200+ actual features. Agents couldn't onboard without re-investigating.

**Options Considered:**
1. Update existing .ai/ files incrementally
2. Create new `/docs/project/` with automated sync
3. Use external wiki (Notion, Obsidian)

**Decision:** Option 2 — `/docs/project/` with 12 specialized files, updated per-session from code evidence.

**Reasoning:**
- Single source of truth per concern (status, roadmap, modules, progress, decisions)
- Machine-readable structure for agent onboarding
- Co-located with code (git-tracked)
- No external dependency

**Impact:**
- +12 files in `/docs/project/`
- TASK_QUEUE.md rewritten from investigation (not assumptions)
- All percentages justified with evidence

**Files Affected:** All `/docs/project/*.md`, `.ai/TASK_QUEUE.md`

---

## 2026-07-30: Security Cycle Category Fix (Critical Bug)

**Problem:** `test_ensure_cycle` failed — expected `cycle.category == "security"` but core created `category="offensive"`.

**Root Cause:** `CycleCategory.OFFENSIVE = "offensive"` and `CycleCategory.SECURITY = "security"` are different enum values. Code used "offensive" in 4 places, test expected "security".

**Fix Applied:** Changed category to "security" in:
1. `core/cycles/security.py` — CycleDefinition registration
2. `core/cycles/security.py` — `_ensure_cycle` method
3. `core/cycles/models.py` — `DEFAULT_CYCLES[0]` category
4. `core/cycles/registry.py` — `registry.register` call

**Result:** 4/4 security cycle tests pass. Database record shows `category=security, status=running`.

**Files Affected:** 4 core files, 1 test file now passing.

---

## 2026-07-30: OMEGA Multi-Cycle Architecture

**Problem:** Single Security Cycle limits revenue to bug bounty only. Need parallel cycles for Dev Bounties (Forge) and AI Work/Microtasks (Pulse).

**Options Considered:**
1. Extend Security Cycle to handle all domains
2. Separate independent systems per domain
3. Multi-Cycle Orchestrator with shared infrastructure

**Decision:** Option 3 — Three independent cycles (Security, Forge, Pulse) with shared EventBus, Scheduler, Agents, Memory, Learning.

**Architecture:**
```
                    OWNEX OMEGA v7.0
                       |
               Mission Control
                       |
       -------------------------------
       |              |              |
   Security        Forge           Pulse
   Cycle           Cycle           Cycle
       |              |              |
    Rastro         Forge          Pulse
       |              |              |
Knowledge Engine  Knowledge     Knowledge
       |              Engine        Engine
       |              |              |
   Memory Layer  Memory Layer  Memory Layer
```

**Each Cycle Has:**
- Sensors (domain-specific, own frequency/priority/budget)
- Planner (classification, EV, difficulty, time, risk, priority, dependencies, deadline)
- Executor (domain-specific)
- Validator (domain-specific)
- Learning (post-cycle evaluation)
- Own State (independent)

**Shared Infrastructure:**
- EventBus (unified, 12+ event types)
- Scheduler (10-stage, per-cycle stages)
- 7 Core Agents + 12 OMEGA Agents
- Memory Layer (shared, cycle-aware)
- Revenue Engine (multi-platform, USD/ARS)

**Revenue Rule Compliance:** Each cycle directly increases Detection + Acceptance + Learning for its domain.

**Files Affected:** New: `core/cycles/forge.py`, `core/cycles/pulse.py`, `api/routers/forge_cycle.py`, `api/routers/pulse_cycle.py`, `core/cycles/orchestrator.py`, `cores/agents/omega/`, `core/sensors/`, `core/self_repair/`, `api/routers/companion.py`, `api/routers/activity.py`

---

## 2026-07-23: OWNEX v7.0 — Self-Evolution Constitution

**Problem:** System needed autonomous evolution capability without human bottleneck.

**Options Considered:**
1. External CI/CD with human approval gates
2. Internal Evolution Engine with constitution
3. Manual release process

**Decision:** Option 2 — OMEGA Constitution + Evolution Engine (`core/evolution/`)

**Constitution Principles:**
- DESIGN → PREPARE → VALIDATE → PROPOSE
- High-risk changes blocked without approval
- Revenue Rule: every feature must increase detection, evidence, acceptance, or learning
- Architecture Budget: max 2 files, 1 dep, 1 event, 1 capability, 1 contract, 20 tests per feature

**Impact:** 9 evolution modules created, API router added, not yet activated.

**Files Affected:** `core/evolution/*`, `api/routers/evolution.py`, `AGENTS.md` updated

---

## 2026-07-23: Multi-Adapter Revenue Model (FASE_18)

**Problem:** Single-platform dependency (bug bounty only) creates revenue risk.

**Options Considered:**
1. Deepen bug bounty only
2. Add freelance platform integration
3. Multi-adapter: Bug Bounty + Dev Bounty + Data Annotation + Freelance

**Decision:** Option 3 — 3 Work Cycles: Security (bug bounty), Forge (dev), Pulse (AI/data).

**Revenue Rule Applied:** Each adapter directly increases detection/evidence/acceptance/learning for its domain.

**Impact:** Core architecture supports pluggable work cycles. Revenue Engine handles USD/ARS, 5 payment methods.

**Files Affected:** `core/finance/`, `core/revenue/`, `cores/financial/`, `apps/aegis/`, `frontend/src/pages/RevenueDashboard.vue`

---

## 2026-07-23: EventBus Unification (FASE_2)

**Problem:** Two EventBus systems (legacy `cores/events/` + new `core/events/`) causing ghost events.

**Options Considered:**
1. Migrate all to new, delete legacy
2. Bridge both, gradual migration
3. Keep both isolated

**Decision:** Option 2 — Bridge in `cores/agents/bus.py`, unified publish/subscribe.

**Impact:** 8 ghost event types now have real publishers. All scheduler stages emit events. COPILOT hooks integrated.

**Files Affected:** `cores/events/event_bus.py`, `cores/agents/bus.py`, `api/main.py` lifespan, `api/scheduler.py`

---

## 2026-07-23: Scheduler + COPILOT Integration (FASE_3-4)

**Problem:** Pipeline stages ran blindly without strategic prioritization.

**Options Considered:**
1. Hardcoded priority weights
2. ORION next_action consultation per stage
3. COPILOT post-stage recommendations

**Decision:** Both 2 + 3 — Scheduler calls `ORION.get_next_action()` for target prioritization, emits COPILOT hooks after each stage.

**Impact:** 
- Per-target cooldown (1hr)
- ORION score multiplier in priority calc
- COPILOT logs: `[ORION] Auto-prioritized X (priority=Y, why=Z)`
- Time-waster detection (>30min no medium+ findings)

**Files Affected:** `api/scheduler.py`, `cores/orion/next_action.py`, `core/target_intelligence/prioritizer.py`

---

## 2026-07-23: Extension SDK (FASE_7)

**Problem:** Integrating 13 OSS tools (LightRAG, Cognee, Graphiti, Skyvern, Crawl4AI, Composio, n8n, Kestra, Langfuse, Graphify, SkillSeekers, Promptfoo, Nanobot) without creating maintenance burden.

**Options Considered:**
1. Fork each, embed directly
2. Subprocess wrappers
3. Extension SDK with Manifest + Hooks + Capabilities

**Decision:** Option 3 — Declarative extension system.

**Architecture:**
- `ExtensionManifest`: id, version, capabilities[], hooks{}, settings{}
- `ExtensionRegistry`: discover, load, capability index, hot reload
- `Hooks`: before/after pipeline stages, event filters
- `Capabilities`: domain, actions[], requirements[]

**Impact:** 13 extensions structured, discoverable, loadable. `verify_extensions.py` validates. Not yet wired to scheduler.

**Files Affected:** `core/extension/*`, `extensions/*/manifest.py`, `extensions/*/connector.py`, `verify_extensions.py`

---

## 2026-07-24: Revenue Intelligence (FASE_28)

**Problem:** No unified USD/hour metric across platforms; scheduler EV logging used raw payout.

**Options Considered:**
1. Manual spreadsheet tracking
2. Per-platform connector normalization
3. Revenue Intelligence layer: USD/hour in RevenueMetrics, dynamic platform speed in TargetPrioritizer, USD/hour in scheduler EV log

**Decision:** Option 3 — Cross-cutting revenue intelligence.

**Impact:**
- `RevenueMetrics.usd_per_hour` computed from `PayoutRecord`
- `TargetPrioritizer` uses dynamic platform speed (not static)
- Scheduler logs: `[SCHEDULER] EV=$X/hr` for each target
- 70 tests added across target_intelligence + revenue_pipeline + scheduler

**Files Affected:** `core/revenue/metrics.py`, `core/target_intelligence/prioritizer.py`, `api/scheduler.py`

---

## 2026-07-26: Opportunity Score Engine (FASE_29)

**Problem:** No unified scoring across 3 work cycles (Security, Forge, Pulse).

**Options Considered:**
1. Separate scorers per cycle
2. Unified scorer with cycle-aware weights
3. External ML ranking service

**Decision:** Option 2 — `core/opportunity/` with UnifiedScorer, Top5Engine, PersonalHistoryTracker.

**Formula:** `Score = EV × AcceptanceProb × (1/Difficulty) × (1/Competition) × PersonalFit × Confidence`

**Impact:** 23 tests, API router, Top5 diversification (max 2 per source), personal history from RevenueMetrics.

**Files Affected:** `core/opportunity/*`, `api/routers/opportunity_score.py`, `tests/test_opportunity_core.py`

---

## 2026-07-23: Tauri v2 Desktop Architecture

**Problem:** Web-only limits: no filesystem, no native shell, no system tray, no offline.

**Options Considered:**
1. Electron (heavy, Node.js)
2. Tauri v1 (legacy)
3. Tauri v2 (Rust, WebView2/WebKitGTK, sidecar)

**Decision:** Option 3 — Tauri v2 + Python FastAPI sidecar via WebSocket.

**Architecture:**
- Frontend: Vue 3 + xterm.js (TerminalView.vue)
- Backend: Python FastAPI WebSocket (terminal_ws.py)
- Sidecar: Tauri `start_backend.py` spawns Python
- CSRF middleware: early return for WebSocket upgrade
- CSP: configured for `ws://` in `tauri.conf.json`

**Impact:** `src-tauri/` complete, Rust 1.97.0 installed. **Never built.**

**Files Affected:** `src-tauri/*`, `frontend/src/views/TerminalView.vue`, `api/terminal_ws.py`, `bin/start_backend.py`

---

## 2026-07-23: ORION Infrastructure Freeze

**Problem:** Hermes, FCC Proxy, OpenCode, Cline, Aider, Ollama constantly changing, breaking agent workflows.

**Decision:** FREEZE v1.0 — Only modify for critical bug or security vuln.

**Current Stack:**
- Ollama (:11434) — qwen3-coder, hermes-orion
- FCC Proxy (:8082) — claude-sonnet-4-5 via OpenRouter (ANTHROPIC_API_KEY=orion-dev-local)
- OpenCode built-in — deepseek, nemotron, mimo (free)
- Config: `~/.orion/config.sh` → `~/.bashrc` exports

**Impact:** Stable agent orchestration. All development focused on Rastro/OWNEX.

**Files Affected:** `AGENTS.md`, `.ai/PRODUCTION_RULES.md`, `~/.orion/config.sh`

---

## 2026-07-23: Revenue Rule as Constitutional Constraint

**Problem:** Feature creep — architectural improvements with no revenue impact.

**Decision:** Hard gate — NO feature enters roadmap without increasing at least one:
- Vulnerability detection rate
- Evidence quality
- Acceptance probability 
- System learning

**Enforcement:** Strategic Audit Framework (18 dimensions, score 0-10). Sprint Review table mandatory.

**Impact:** Extensions (13) and Evolution (9) correctly deferred — they fail Revenue Rule today.

**Files Affected:** `.ai/AGENT_CHARTER.md`, `.ai/STRATEGIC_AUDIT.md`, `.ai/ROADMAP.md`

---

## 2026-07-23: Database — SQLite Dev / PostgreSQL Prod

**Problem:** Local dev needs zero-config; production needs concurrency.

**Decision:** SQLAlchemy with async, same models. SQLite (WAL mode) for dev, PostgreSQL for prod.

**Optimizations Added (FASE_6):**
- 14 missing indexes
- WAL checkpoint per scheduler cycle (`PRAGMA wal_checkpoint(TRUNCATE)`)
- Audit log rotation (10MB, 3 backups)
- Cooldown cyclic purge (2x TARGET_COOLDOWN)

**Files Affected:** `database/db.py`, `database/models.py`, `database/models_economic.py`, `api/scheduler.py`

---

## 2026-07-23: Validation Engine — Challenger + Confidence + Evidence Graph

**Problem:** False positives waste submission slots and reputation.

**Decision:** Three-layer validation (FASE_5):
1. **Challenger** (`cores/validation/challenger.py`) — 7 alternative explainers, contradiction tests, missing verification analysis
2. **Confidence** (`cores/validation/confidence.py`) — Uncertainty penalty, evidence weight, balance scoring
3. **Evidence Graph** (`core/evidence_graph/`) — Persistent for/against/neutral, edges, weights, balance score

**Impact:** Drastically reduced false positives. Auto-report gate uses quality score.

**Files Affected:** `cores/validation/*`, `core/evidence_graph/*`, `cores/pipeline/report_service.py`

---

## 2026-07-23: AI Security Module (FASE_26)

**Problem:** LLM/GenAI bug bounty programs emerging; no tooling.

**Decision:** Minimal viable module — Garak scanner + AI Bounty engine + 2-tab frontend.

**Scope:** Local model scanning (Garak), AI bounty program tracking (4 programs), simple UI.

**Impact:** 5 unit tests pass, 6 integration skipped (need local models). `core/intel/llm_scanner.py`, `api/routers/ai_security.py`, `frontend/src/pages/AISecurity.vue`

**Files Affected:** As above + `cores/tools/extra.py` (GarakTool)

---

## 2026-07-24: Censys Tool + Crypto TA (FASE_28)

**Problem:** Internet asset discovery limited to Shodan; no technical analysis for crypto revenue tracking.

**Decision:** Add CensysTool (certificates, hosts) + CoinGecko OHLC → RSI/SMA/MACD signals.

**Impact:** Censys registered in TOOL_REGISTRY. `get_technical_signals()` with interpretation.

**Files Affected:** `cores/tools/censys.py`, `cores/tools/extra.py`, `cores/tools/__init__.py`, `cores/crypto/coingecko.py`