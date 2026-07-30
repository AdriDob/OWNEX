# ARCHITECTURE — OWNEX OMEGA v7.0

**Generated from code investigation:** 2026-07-30

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        OWNEX OMEGA v7.0                         │
│           Autonomous Multi-Cycle Operating System               │
│    Bug Bounty │ Dev Bounties │ AI Work │ Data Annotation       │
└─────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│   FRONTEND    │           │    BACKEND    │           │  INFRASTRUCTURE │
│  (Vue 3 + TS) │           │   (FastAPI)   │           │   (Shared)     │
└───────┬───────┘           └───────┬───────┘           └───────┬───────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         EVENT BUS (Unified)                          │
│  Legacy EventBus ↔ New EventBus Bridge │ 12+ Event Types Published  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│  SCHEDULER    │           │    AGENTS     │           │  EXTENSIONS   │
│ (10-Stage     │           │  (7 Autonomous)│           │  (13 OSS)     │
│  Pipeline)    │           │               │           │               │
└───────────────┘           └───────────────┘           └───────────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     MULTI-CYCLE ORCHESTRATOR                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │  SECURITY   │  │   FORGE     │  │   PULSE     │                │
│  │   CYCLE     │  │   CYCLE     │  │   CYCLE     │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Backend Architecture (FastAPI)

### Router Organization (`api/routers/`)

| Router | Responsibility | Endpoints |
|--------|----------------|-----------|
| `mission.py` | Mission Control dashboard | `/api/mission/status`, `/api/mission/action` |
| `cycles.py` | Cycle management | `/api/cycles/*` |
| `security_cycle.py` | Security/Offensive cycles | `/api/security/cycle`, `/api/security/cycle/start` |
| `forge_cycle.py` | Forge/Dev bounty cycles | `/api/forge/cycle`, `/api/forge/cycle/start` (NEW) |
| `pulse_cycle.py` | Pulse/AI work cycles | `/api/pulse/cycle`, `/api/pulse/cycle/start` (NEW) |
| `opportunity_score.py` | Opportunity Engine API | `/api/opportunity/score`, `/api/opportunity/top5` |
| `targets.py` | Target management | `/api/targets/*` |
| `findings.py` | Finding CRUD | `/api/findings/*` |
| `reports_quality.py` | Report quality gate | `/api/reports/quality/*` |
| `reports_acceptance.py` | Acceptance optimizer | `/api/reports/acceptance/*` |
| `offensive.py` | Offensive intelligence | 8 endpoints |
| `orion.py` | ORION reasoning | `/api/orion/next-action`, `/api/orion/score` |
| `copilot.py` | COPILOT agent | `/api/copilot/recommend` |
| `commands.py` | Command system (107 cmds) | `/api/commands/*` |
| `system_state.py` | System health/state | `/api/system/state`, `/api/system/state/events` |
| `notifications.py` | Smart notifications | `/api/smart/*` |
| `ai_security.py` | AI/LLM security | `/api/ai-security/*` |
| `evolution.py` | Evolution engine | `/api/evolution/*` |
| `settings_unified.py` | Unified settings | `/api/settings/*` |
| `vault.py` | Secrets management | `/api/vault/*` |
| `backup.py` | Backup/restore | `/api/backup/*` |
| `cateye.py` | CATEYE integration | `/api/cateye/*` |

### Core Engines (`core/`, `cores/`)

```
core/
├── cycles/              # Security, Forge, Pulse, Executive Dashboard, Knowledge Capture
├── offensive/           # 5 reasoners (101 tests)
├── evidence/            # Composer: PoC, CVSS, CWE, CAPEC, OWASP, MITRE (37 tests)
├── reports/             # Quality gate, acceptance optimizer (18 tests)
├── learning/            # VerdictLearner ↔ AcceptanceLearner bridge
├── opportunity/         # Unified scorer, Top5, personal history (23 tests)
├── revenue/             # Metrics, USD/hour, payout tracking
├── finance/             # Core finance models
├── auto_hunter/         # AI Bounty (4 programs, 29 tests)
├── auto_submit/         # Auto-submission pipeline (12 tests)
├── target_intelligence/ # Prioritizer, EV + tech + attack plans (22 tests)
├── recon/               # NaabuRunner, dedup, ReconRunner (23 tests)
├── commands/            # 107 commands, 14 categories (45 tests)
├── evolution/           # 9 modules (stubs)
├── extension/           # SDK: Manifest, Hooks, Capabilities, Registry
├── secrets/             # Vault, AES-256-GCM (11 tests)
├── health/              # Unified checks, snapshots (25 tests)
├── workflows/           # Workflow engine
├── sync/                # Sync engine
├── documentation/       # Auto-generation platform
├── app_registry.py      # AppRegistry bridge
└── priority/            # EV Engine

cores/
├── agents/              # 7 autonomous agents + bus
├── events/              # EventBus + types (unified)
├── orion/               # Next action, EVH scoring
├── crypto/              # CoinGecko, technical analysis
├── financial/           # Takenos, dashboard, truth layer
├── tools/               # Amass, Naabu, Shodan, Uncover, Censys, Garak, Gitleaks, BrowserUse
├── bounty_scraper/      # Multi-platform program discovery
├── validation/          # Loop engine, challenger, confidence
├── pipeline/            # Hypothesis bridge, report service
├── notifications/       # Discord (12 events), intelligent manager
├── integrations/        # ARCA, Outlook
└── env/config.py        # Centralized config
```

---

## Frontend Architecture (Vue 3 + TypeScript)

### Pages (`frontend/src/pages/`)

| Page | Data Source | Status |
|------|-------------|--------|
| `MissionControl.vue` | `/api/mission/status` (7 endpoints) | ✅ Real |
| `SecurityCycle.vue` | `/api/cycles/security/*` | 🟡 Core works, needs scheduler bootstrap |
| `ForgeCycle.vue` | `/api/cycles/forge/*` | 🔴 Not created |
| `PulseCycle.vue` | `/api/cycles/pulse/*` | 🔴 Not created |
| `Opportunities.vue` | `/api/opportunity/*` | ✅ Real |
| `RevenueDashboard.vue` | `/api/targets/*` (EV tab) | ✅ Real |
| `GamingConsole.vue` | **Hardcoded fake data** (lines 39-48) | 🔴 Fake |
| `AgentFleet.vue` | `/api/system/state` (fallback static) | 🟡 Partial |
| `HealthCenter.vue` | `/api/core/health/*` | ✅ Real |
| `Workflows.vue` | `/api/workflows/*` | ✅ Real |
| `MobileCompanion.vue` | `/api/companion/*` | ✅ Real |
| `AISecurity.vue` | `/api/ai-security/*` | ✅ Real |
| `BabyMode.vue` | Local state | ✅ Real |

### Services (`frontend/src/services/`)

| Service | Purpose |
|---------|---------|
| `ownexData.ts` | Central API client — fetches mission, security, forge, pulse, opportunities, revenue, system state |
| `useAssistant.ts` | Assistant composable |
| `useCompanion.ts` | Mobile companion composable |

### Components (`frontend/src/components/`)

- `ui/` — DataTable, Drawer, Modal, Select (ShadCN Vue + Tailwind v4)
- `apps/aegis/` — Aegis security app components
- Charts, graphs, real-time widgets

---

## Scheduler Architecture (10-Stage Pipeline)

```
api/scheduler.py ──► ScanScheduler
    │
    ├─► STAGE_INTERVALS (seconds):
    │     discover: 3600      recon: 1800
    │     hypothesis: 900     auto_validate: 1800
    │     promote: 600        scope_check: 3600
    │     validate: 7200      report: 3600
    │     ai_bounty: 7200
    │
    ├─► PER-TARGET COOLDOWN: 3600s (1 hour)
    │
    ├─► PIPELINE STAGES (async, independent):
    │     1. DISCOVER     → scrape platforms → create targets → publish opportunity:found
    │     2. RECON        → scan targets (subfinder, amass, httpx, naabu) → ORION prioritization
    │     3. HYPOTHESIS   → generate vuln hypotheses (7 types + path-based fallback)
    │     4. AUTO_VALIDATE → Validation Engine → promote to Finding
    │     5. PROMOTE      → test hypotheses against real endpoints
    │     6. VALIDATE     → scope-aware validation (auth baseline/probe)
    │     7. REPORT       → auto-draft reports for confirmed findings
    │     8. AI_BOUNTY    → scan 4 AI bounty programs
    │
    ├─► PARALLEL RECOVERY (async):
    │     • Hacktivity learning (RewardLearner)
    │     • Economic memory refresh
    │     • Stale report generation
    │
    ├─► WAL CHECKPOINT (per cycle)
    │
    ├─► COOLDOWN PURGE (2x TARGET_COOLDOWN)
    │
    └─► TIME_WASTER DETECTION (>30min no medium+ findings)
```

### COPILOT Integration

- After each stage: `_copilot_hook(stage, result, pipeline_id)` 
- Publishes `EventType.PIPELINE_STAGE_COMPLETED` / `PIPELINE_FAILED`
- COPILOT recommends system actions (top 3 logged)

---

## Event Bus Architecture

```
Unified Event Bus (cores/events/event_bus.py)
    │
    ├─► Legacy EventBus Bridge (cores/agents/bus.py)
    │
    ├─► Event Types (cores/events/types.py):
    │     • Pipeline: PIPELINE_STAGE_COMPLETED, PIPELINE_FAILED
    │     • Discovery: discovery:program:new, discovery:program:updated
    │     • Opportunity: opportunity:found, opportunity:updated
    │     • Findings: finding:created, finding:updated, finding:confirmed
    │     • Reports: report:generated
    │     • Security: security:cycle:started, security:cycle:advanced
    │     • Forge: forge:cycle:started, forge:cycle:advanced (NEW)
    │     • Pulse: pulse:cycle:started, pulse:cycle:advanced (NEW)
    │     • Agent: agent:task:started, agent:task:completed
    │     • Commands: command:executed, command:failed
    │     • Notifications: 12 Discord event types
    │     • Hermes: 7 Hermes v2 events
    │
    └─► Subscribers (auto-wired):
          • Auto-report on finding:confirmed
          • Scheduler COPILOT hooks
          • Discord notifications
          • Health snapshots
```

---

## Agent Architecture (7 Autonomous + 12 OMEGA Agents)

### Current 7 Agents

```
cores/agents/
├── types.py              # EventType, AuthorityLevel, AgentCapability
├── bus.py                # AgentBus → EventBus bridge
├── base.py               # BaseAgent class
├── copilot/              # SENIOR_HUNTER — scheduler hooks, recommendations
├── recon/                # SCANNER — subfinder, amass, httpx, naabu
├── hypothesis/           # ANALYST — 7 vuln type generators
├── validation/           # VALIDATOR — loop engine, challenger, confidence
├── report/               # REPORTER — auto-draft, quality gate, acceptance
├── economic/             # TREASURER — revenue metrics, USD/hour, payouts
└── orion/                # STRATEGIST — next action, EVH scoring
```

Each agent:
- Registers capabilities on startup
- Subscribes to relevant EventBus events
- Publishes results via EventBus
- COPILOT coordinates cross-agent decisions

### OMEGA Autonomous Agents (12 New)

```
cores/agents/omega/
├── observer/             # Continuous monitoring per domain
├── researcher/           # Deep-dive analysis
├── planner/              # Opportunity → plan
├── architect/            # Solution design
├── developer/            # Code generation
├── reviewer/             # Quality gate
├── validator/            # Verification
├── documentation/        # Auto-docs
├── repair/               # Self-healing
├── infrastructure/       # Ops
├── learning/             # Post-cycle improvement
└── evolution/            # Self-evolution
```

---

## Extension Architecture

```
extensions/
├── lightrag/       # Knowledge graph RAG
├── cognee/         # Cognitive memory
├── graphiti/       # Temporal knowledge graph
├── skyvern/        # Browser automation
├── crawl4ai/       # Web crawling
├── composio/       # Tool orchestration
├── n8n/            # Workflow automation
├── kestra/         # Data orchestration
├── langfuse/       # LLM observability
├── graphify/       # Graph visualization
├── skill_seekers/  # Skill discovery
├── promptfoo/      # Prompt evaluation
└── nanobot/        # Micro-agents

core/extension/
├── registry.py     # ExtensionRegistry — discovery, load, capability index
├── manifest.py     # ExtensionManifest — id, version, capabilities, hooks, settings
├── hooks.py        # before/after hooks for pipeline stages
├── capabilities.py # Capability(domain, actions, requirements)
└── settings.py     # Declarative settings schema
```

**Integration Points (Not Yet Active):**
- `ExtensionRegistry.discover()` → loads 13 extensions
- `manifest.py` defines `Capability(domain=..., actions=...)`
- `hooks.py` can subscribe to pipeline stage events
- `verify_extensions.py` validates full load

---

## Evolution Architecture (Stubs)

```
core/evolution/
├── analyze.py              # Main analysis engine (16KB)
├── engine.py               # Evolution engine (16KB)
├── design_evolution.py     # Design proposals
├── infrastructure_auditor.py # Infra audit
├── self_healer.py          # Self-healing
├── self_tester.py          # Self-testing
├── supervisor.py           # Supervision
├── technology_watcher.py   # Tech monitoring
└── update_engine.py        # Update management

api/routers/evolution.py    # Router exists, endpoints stubbed
```

**Missing for Activation:**
- EventBus subscriptions
- Scheduler job registration
- API endpoint implementation
- Test coverage

---

## Desktop Architecture (Tauri v2)

```
src-tauri/
├── tauri.conf.json         # Config: CSP, permissions, sidecar
├── Cargo.toml              # Rust deps
├── src/
│   ├── main.rs             # Entry point
│   └── sidecar/            # Python backend sidecar
├── binaries/
│   └── start_backend.py    # FastAPI + WebSocket sidecar
└── icons/                  # App icons

Frontend (Vue) → WebSocket → Python sidecar (FastAPI on random port)
    │
    ├─► Terminal: xterm.js ↔ WebSocket ↔ terminal_ws.py (pty)
    ├─► API: All /api/* routes proxied
    └─► CSP: Must allow ws:// for terminal
```

**Build Pipeline (Untested):**
1. `npm run build` → Vue dist
2. `cargo tauri build` → Rust + sidecar bundled
3. PyInstaller → `start_backend.py` → `.exe` sidecar
4. NSIS/InnoSetup → Windows installer

---

## Data Flow: Multi-Cycle Operation

### Security Cycle (Bug Bounty)

```
1. DISCOVER (Scheduler)
   └─► BountyScraper → TargetIdentity → DB
   
2. RECON (Scheduler)
   └─► Subfinder/Amass/httpx/Naabu → Endpoint → DB
   
3. HYPOTHESIS (Scheduler)
   └─► Generators (7 types) → Hypothesis → DB
   
4. AUTO_VALIDATE (Scheduler)
   └─► ValidationEngine → AttackCandidate → Finding (promoted)
   
5. PROMOTE (Scheduler)
   └─► Real endpoint testing → Confirmed Finding
   
6. VALIDATE (Scheduler)
   └─► LoopEngine + Challenger → Verdict → Evidence
   
7. REPORT (Scheduler)
   └─► EvidenceComposer → QualityGate → AcceptanceOptimizer → Report
   
8. AUTO_SUBMIT (Pipeline)
   └─► Platform detection → Submission → Payout tracking
   
9. REVENUE (Economic Agent)
   └─► USD/ARS conversion → Metrics → Dashboard → USD/hour
```

### Forge Cycle (Dev Bounties) — NEW

```
1. DISCOVER (Scheduler)
   └─► Algora/Opire/Superteam/IssueHunt scrapers → BountyIssue → DB
   
2. ANALYZE (Scheduler)
   └─► CoderAgent.repo_analyzer + issue_analyzer → TechnicalPlan → DB
   
3. PLAN (Scheduler)
   └─► CoderAgent.code_generator + test_runner → Implementation → DB
   
4. VALIDATE (Scheduler)
   └─► CoderAgent.test_runner → Tests pass + Lint clean → PR Ready
   
5. SUBMIT (Scheduler)
   └─► CoderAgent.pr_builder + orchestrator → PR Submitted → Platform
   
6. REVENUE (Economic Agent)
   └─► Payout tracking → USD/ARS → Metrics → Dashboard
```

### Pulse Cycle (AI Work / Microtasks) — NEW

```
1. DISCOVER (Scheduler)
   └─► Outlier/Mindrift/DataAnnotation/Remotasks scrapers → TaskQueue → DB
   
2. QUALIFY (Scheduler)
   └─► Skill matching + qualification check → EligibleTasks → DB
   
3. EXECUTE (Scheduler)
   └─► BrowserAgent workers → Task completion → Evidence → DB
   
4. VALIDATE (Scheduler)
   └─► Quality check → Submission → Platform
   
5. REVENUE (Economic Agent)
   └─► Payout tracking → USD/ARS → Metrics → Dashboard
```

---

## Security Model

| Layer | Implementation |
|-------|----------------|
| **Secrets** | AES-256-GCM vault + env fallback (`core/secrets/manager.py`) |
| **Permissions** | 5 risk levels (SAFE → CRITICAL) — `apps/hermes/permissions.py` |
| **Path Validation** | Allowlist/denylist — `apps/hermes/security.py` |
| **Process Validation** | PID allowlist — `apps/hermes/security.py` |
| **Command System** | 107 commands, permission-gated — `core/commands/` |
| **CSP (Desktop)** | Configured in `tauri.conf.json` — needs `ws://` for terminal |
| **Auth Contexts** | Baseline/Probe tokens for validation — `cores/validation/replayer.py` |

---

## Observability Stack

| Component | Implementation |
|-----------|----------------|
| **Health Center** | `core/health/engine.py` — 25 checks, snapshots, green/yellow/red |
| **Audit Log** | `audit.jsonl` — rotation 10MB, 3 backups |
| **Event Bus Metrics** | All pipeline stages emit events |
| **Scheduler Stats** | `get_scheduler_stats()` — stage timing, cooldowns, pipeline_id |
| **COPILOT Logs** | Recommendations logged per stage |
| **Time Waster** | Auto-detection >30min no medium+ findings |
| **Discord Notifications** | 12 event types → webhook |

---

## Configuration (Centralized)

```
~/.orion/config.sh          # ORION ecosystem shared config
~/.bashrc                   # ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL
cores/env/config.py         # Python config loader (get_config())
api/main.py lifespan        # Startup: init_loop_engines, scheduler.start()
```

**Providers (Failover Chain):**
1. Ollama local — `qwen3-coder:8b`
2. FCC Proxy — `claude-sonnet-4-5` via OpenRouter (localhost:8082)
3. OpenCode built-in — `deepseek-v4-flash-free`, `nemotron-free`

---

## Deployment Architecture

```
Production:
├── API Server (FastAPI) — systemd / Docker
├── Frontend (Nginx + static) — port 80/443
├── Database (PostgreSQL) — managed
├── Scheduler — in-process (single instance)
├── Event Bus — in-memory (single process)
├── Redis — optional for distributed EventBus
├── Desktop — Tauri installer (Windows)
└── Monitoring — Health Center + Discord

Development (WSL):
├── API: localhost:8000 (uvicorn --reload)
├── Frontend: localhost:5173 (vite)
├── Database: SQLite (WAL mode)
├── Scheduler: in-process
├── Ollama: localhost:11434
├── FCC Proxy: localhost:8082
└── Rust: 1.97.0
```

---

## Key Architectural Decisions (See DECISIONS.md)

1. **Monolithic Modular** — Single FastAPI process, modular cores, EventBus for decoupling
2. **Unified EventBus** — Legacy + new bridged, single source of truth for events
3. **Revenue Rule** — Every feature must increase detection/evidence/acceptance/learning
4. **Self-Evolution Constitution** — DESIGN → PREPARE → VALIDATE → PROPOSE (OMEGA v7.0)
5. **Private Asset Model** — OWNEX works for operator, not sold as SaaS
6. **Multi-Adapter** — Bug bounty, freelance, dev, data annotation — diversify income
7. **Maximum Automation, Guided Detail** — Human-in-the-loop for decisions, auto-execution for tasks
8. **Multi-Cycle Orchestration** — Security + Forge + Pulse cycles run in parallel with shared agents/memory
9. **Continuous Observation** — Sensors per domain with frequency, priority, budget, retry, backoff, cache, dedup
10. **Self-Repair & Learning** — Auto-diagnose, repair, validate, log; post-cycle evaluation