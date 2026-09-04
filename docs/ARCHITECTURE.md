# OWNEX Architecture

> **Generated from actual codebase** — This document reflects the real implementation, not aspirational design.

## System Overview

OWNEX is a **Personal Autonomous Work Operating System** implemented as a modular monolith with Event-Driven architecture. It combines a FastAPI backend with a Vue 3 frontend, packaged as a Tauri v2 desktop application.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        OWNEX SYSTEM                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  Frontend (Vue 3 + TypeScript + Tailwind v4)                          │
│  ├── Desktop: Tauri v2 (Rust WebView2)                                │
│  ├── Mobile: Android (Kotlin + Compose)                               │
│  └── Watch: Wear OS                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python 3.11+)                                     │
│  ├── API Layer (171 routers)                                          │
│  ├── Core Business Logic (cores/)                                     │
│  ├── Legacy CATEYE (core/)                                            │
│  ├── Database (SQLite/PostgreSQL via SQLAlchemy)                      │
│  └── Event Bus (in-memory + SQLite persistence)                       │
├─────────────────────────────────────────────────────────────────────────┤
│  AI Orchestration (OAR)                                               │
│  ├── Local: Ollama (qwen2.5:3b-instruct)                             │
│  ├── FCC Proxy: Anthropic models via OpenRouter                       │
│  ├── OmniRoute: Auto/* model selection                                │
│  └── Fallback chain with cost/health monitoring                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **Monolithic Modular** | Single FastAPI process, 171 routers organized by domain |
| **Event-Driven** | CoreEventBus with SQLite persistence, priority classification |
| **Single Source of Truth** | `.ai/` directory for docs, VERSION file for versioning |
| **Twin Tree** | `core/` (legacy CATEYE) + `cores/` (new OWNEX) — gradual migration |
| **Revenue Rule** | No feature without measurable impact on detection/evidence/acceptance/learning |

## Backend Structure

### API Layer (`api/`)
- **Entry Point**: `api/main.py` — FastAPI app with lifespan management
- **171 Routers** mounted at `/api/<domain>` prefixes
- **Middleware Stack**: CORS → SecurityHeaders → CSRF → RateLimit → Auth → ErrorHandling
- **Health Endpoints**: `/api/health`, `/api/system/status`, `/api/version`, `/api/stats`, `/api/metrics`

### Core Business Logic (`cores/`)
```
cores/
├── agents/           # Multi-agent system
├── ai/               # AI providers, OAR runtime
├── auth/             # Token service, session management
├── autonomy/         # Autonomous workflows
├── backup/           # Version backup system
├── capital/          # Capital allocation, tracking
├── career/           # Career engine, skill gaps
├── credentials/      # Vault, rotation
├── cycles/           # Work cycles (security, forge, pulse, vault, atlas)
├── direct_work_engine/  # DWE: opportunities, workbank, recommendations
├── events/           # EventBus, event types
├── financial/        # Revenue tracking, sync scheduler
├── health/           # Health monitoring
├── knowledge/        # Knowledge bridge (Obsidian)
├── learning/         # Learning engine, profiles
├── license/          # License validation (Ed25519)
├── market/           # Market intelligence
├── memory/           # UnifiedMemoryStore (SQLite)
├── merlin/           # MERLIN AI assistant
├── operations/       # 24/7 operations manager
├── opportunity/      # Opportunity engine, executors
├── orchestrator/     # Scan service, discovery
├── payment_compat/   # Payment compatibility engine
├── productivity/     # Daily planning, onboarding
├── recovery/         # Recovery engine, healing rules
├── revenue_tracker/  # Revenue pipeline
├── scheduler/        # Job definitions (47 jobs, 12 cycles)
├── security/         # Security orchestrator, validator
├── setup/            # Personalization wizard
├── supabase/         # Supabase sync
├── system/           # System state, HHD tracker
├── trading/          # Copy trading, strategy DNA
├── validation/       # Hypothesis challenger, contradiction runner
├── voice/            # Voice interface
└── workflow/         # Workflow engine, handoffs
```

### Legacy CATEYE (`core/`)
```
core/
├── acceptance/       # Acceptance intelligence
├── ai/               # AI providers, router
├── autonomy/         # CoderAgent, workflow engine
├── backup/           # Backup engine
├── bugbounty/        # Bug bounty coordinator
├── cycles/           # Security/Forge/Pulse/Vault/Atlas cycles
├── execution/        # Compiler + runtime state machine
├── health/           # Health center
├── investment/       # Investment adapters
├── mcp/              # MCP servers
├── opportunity/      # Opportunity engine, executors
├── recon/            # Recon engine
└── scheduler/        # CoreScheduler
```

## Database

- **ORM**: SQLAlchemy 2.0 (async)
- **Dev**: SQLite (`%LOCALAPPDATA%/OWNEX/database/cateye.db` on Windows, `~/.ownex/database/cateye.db` on Linux)
- **Prod**: PostgreSQL
- **Tables**: targets, endpoints, findings, scan_runs, verdicts, evidence, memory_records, revenue records, etc.
- **Migrations**: `metadata.create_all()` (no Alembic)

## Event Bus

- **Implementation**: `cores/events/event_bus.py` (CoreEventBus)
- **Persistence**: SQLite (`EventBusEntry` table)
- **Priority**: `critical` > `high` > `medium` > `low`
- **Wildcard Handlers**: `*` handlers for cross-cutting concerns
- **Bridge**: Connects to legacy CATEYE EventBus

## Scheduler

- **CoreScheduler**: `core/scheduler/scheduler.py` (cron-aware via croniter)
- **Jobs**: 47 jobs across 12 cycles (security, forge, pulse, vault, atlas, direct_work, trading, knowledge, qa, delivery, outlook, etc.)
- **Handlers**: Resolved via dotted-path (`module:attr`, `module.Class.method`)

## Work Cycles

| Cycle | Priority | Domains | Status |
|-------|----------|---------|--------|
| Security | 1 | Bug bounty (Rastro) | ✅ Active |
| Forge | 3 | Dev bounty, code execution | ✅ Active |
| Pulse | 5 | AI work, training | ✅ Active |
| Vault | 7 | Wealth, capital | ✅ Active |
| Atlas | 5 | Intelligence, markets | ✅ Active |
| Direct Work | 6 | Opportunity discovery | ✅ Active |
| Trading | - | Copy trading | ✅ Active |
| Knowledge | - | Obsidian sync | ✅ Active |
| QA | - | Quality assurance | ✅ Active |

## AI Orchestration (OAR)

### Provider Chain (Failover Order)
1. **OmniRoute** — Primary (unlimited), `http://localhost:20128/v1`
2. **FCC Proxy** — Anthropic via OpenRouter, `http://localhost:8082`
3. **Ollama** — Local (`qwen2.5:3b-instruct`), `http://localhost:11434`
4. **OpenCode Built-in** — Free models (DeepSeek, Nemotron, Mimo)

### OAR Runtime (`cores/ai/runtime/`)
- `ProviderRegistry` — Model capabilities, routing
- `SmartRouter` — Task-type routing (CODE→local, etc.)
- `CostTracker` — Daily budget USD, per-provider tracking
- `FailoverEngine` — Circuit breaker per provider
- `HealthMonitor` — Periodic health checks
- `LearningEngine` — Routing preferences by TaskType
- `SemanticCache` — Response caching

### Model Configuration
- **Hermes**: `claude-sonnet-4-20250514` via FCC (primary), OmniRoute fallback
- **OpenCode**: `deepseek-coder-6.7b` via FCC (primary), OmniRoute/Ollama fallbacks
- **Default Spend**: $0/day (explicit opt-in for paid tiers)

## Frontend Architecture

### Stack
- **Framework**: Vue 3 + TypeScript (strict)
- **Build**: Vite
- **Styling**: Tailwind CSS v4 + ShadCN Vue
- **State**: Pinia stores
- **API**: Centralized `@/services/ownexData.ts`

### Key Pages (61 routed)
```
/                          → WelcomePage
/dashboard                 → GamingConsole
/mission-control           → MissionControl
/security/executive        → ExecutiveDashboard
/intelligence/*            → Findings, Hypothesis, Evidence, Investigation
/targets/*                 → Targets, Discovery, AttackSurface
/capital                   → Capital (unified)
/reports/*                 → ReportCenter, Queue, History
/operations/*              → Terminal, VersionBackup
/merlin                    → MerlinInterface
/autopilot                 → OneActionCard
/settings                  → Settings (unified)
```

### Design System (OWNEX v1.0)
- **Colors**: `--ownex-bg-deep: #050505`, `--ownex-blue: #3B82F6`, `--ownex-gold: #F59E0B`, `--ownex-green: #10B981`, `--ownex-red: #EF4444`, `--ownex-yellow: #FBBF24`
- **Fonts**: Space Grotesk (display), Inter (body), JetBrains Mono (mono)
- **Components**: OwnexCard, OwnexButton, OwnexBadge, OwnexKPI, OwnexTabs, CommandPalette
- **Layout**: Global Status Bar (40px), Collapsible Sidebar (280px→64px), Tabbed Workspace

## Desktop (Tauri v2)

### Architecture
```
OWNEX.app / OWNEX.exe
├── Frontend (Vue 3 dist)
├── src-tauri/
│   ├── main.rs              # Entry, window config
│   ├── python_sidecar.rs    # Spawns FastAPI sidecar
│   ├── ollama_manager.rs    # Auto-starts Ollama
│   ├── ipc/                 # Tauri commands/events
│   ├── system_tray.rs       # Tray integration
│   ├── window_state.rs      # Persist position/size
│   └── updater.rs           # GitHub Releases auto-update
├── python/                  # Bundled FastAPI (PyInstaller ONEFILE)
└── resources/
    └── icon.ico/.icns, splash.png
```

### Key Configuration
- **Identifier**: `com.ownex.app`
- **CSP**: Allows `ws://localhost:*` for terminal WebSocket
- **Sidecar**: `ownex-backend.exe` (PyInstaller ONEFILE, self-contained)
- **Port**: 8000 (backend), 5173 (Vite dev)
- **Data Dir**: `%LOCALAPPDATA%/OWNEX` (Windows), `~/.ownex` (Linux)
- **Auto-start**: Backend spawns in background thread, health-poll until ready

### Python Sidecar
- **Build**: `OWNEX-Backend.spec` → PyInstaller ONEFILE (`ownex-backend.exe`)
- **Health Check**: `GET /api/health` polling (1.5s timeout, 5s cache)
- **Auto-restart**: Rust watchdog restarts sidecar on health failure

## Mobile (Android)

### Stack
- **Language**: Kotlin + Compose Multiplatform
- **Architecture**: MVVM with shared ViewModels
- **Push**: Firebase Cloud Messaging
- **Auth**: Biometric (fingerprint/face) for approvals

### Features
- Critical notifications (findings, approvals, errors)
- One-tap approvals ("Start cycle", "Submit report")
- Opportunity Radar Mobile (top 5, swipe actions)
- Agent Fleet Status (compact 🟢🟡🔴 + current task)
- Vault/Wallet (balance, pending payouts)
- System Health (🟢🟡🔴 + key metrics)
- COPILOT Summary (decisions, daily brief)

## Watch (Wear OS)

### Philosophy
**Alert/Status/Quick Action surface — NOT a miniature Desktop.**

### Features
- Critical alerts (findings, approvals, capital, health)
- Status: 🟢 ORION ONLINE, N cycles active, M approvals pending
- Next Action preview (title, reward, confidence, time)
- One-tap Approve/Defer
- Swipe gestures for detail/dismiss
- Battery-conscious (minimal rendering, no polling)

### UI Example
```
┌─────────────────────┐
│ 🟢 ORION ONLINE     │
│ 3 ciclos activos    │
│ 2 aprobaciones 🔔   │
├─────────────────────┤
│ ⚡ Próxima acción   │
│ Validar IDOR Target X│
│ $800 · 87% · 25m    │
│ [Aprobar] [Luego]   │
├─────────────────────┤
│ 🤖 Agentes: 5/6 🟢  │
│ 💰 $2.4k este mes   │
└─────────────────────┘
```

## Synchronization Model

### Canonical State
- **Backend** = Single Source of Truth
- **Frontend** = Reactive views (Pinia stores + composables)
- **Mobile/Watch** = Cached subsets + push notifications

### Sync Mechanism
- **HTTP Polling** (Desktop/Mobile): Configurable intervals
- **WebSocket** (Terminal, real-time updates): `/api/ws/terminal`
- **Push Notifications** (Mobile/Watch): FCM → local notification
- **Idempotency**: Server-side deduplication via `external_id`
- **Conflict Resolution**: Server wins (last-write-wins with timestamps)

### Offline Support
- **Desktop**: Full local backend (sidecar) = always online
- **Mobile**: Queued actions (pending sync), cached reads
- **Watch**: Read-only cached state, no offline writes

## Security Model

### Authentication
- **Device ID**: Auto-generated UUID, stored in localStorage (`CATEYE-device-id`)
- **Session**: JWT (30 min) + Refresh token (24h) + httpOnly cookie (`ownex-session`)
- **CSRF**: Double-submit cookie (header `X-CSRF-Token` + cookie `csrf-token`)
- **Rate Limit**: Token bucket per identity (Bearer → sub, fallback IP), burst 50, sustained 30/s

### Credential Storage
- **IdentityVault**: AES-256-GCM, random key (chmod 600), file-based
- **License**: Ed25519 asymmetric (public key embedded, private on license server)
- **No Secrets in Repo**: All keys via env vars or vault

### Audit Logging
- **Format**: JSONL append-only, chmod 600
- **Events**: login, logout, token_stored, financial operations
- **Rotation**: 10MB daily

## Data Flow Examples

### Opportunity Discovery → Revenue
```
1. Scheduler triggers `direct_work_daily_cycle` (cron 15 6 * * *)
2. UniversalDiscovery discovers from registered adapters (Opire, IssueHunt, Freelancer)
3. ZeroBarrierScorer scores 0-100 (15 weighted factors, sum=1.0)
4. IntelligentRecommender ranks by EV > acceptance > barrier > compatibility > speed
5. WorkBank.daily_cycle() filters, prepares WorkItems (ready_to_deliver/needs_access)
6. User reviews in Mission Control → Prepare delivery (AssistedExecutor)
7. User approves → WorkItem marked delivered → RevenueTracker records outcome
8. Feedback loop updates UserProfile success rates → improves future scoring
```

### Security Pipeline
```
1. Scheduler triggers `advance_security_pipeline` (every 30 min)
2. run_pipeline() executes 7 stages: recon → attack_surface → hypothesis → validation → evidence → report → learning
3. Each stage uses stage executors (Nuclei, HTTP probes, contradiction engine)
4. Findings persist → KnowledgeCapture → UnifiedMemoryStore (namespace=cateye)
5. Executive Dashboard aggregates: verdict, weekly/monthly revenue, pipeline status
```

### Investment Execution
```
1. TradingIntelligence discovers traders (Jupiter DEX, CEX APIs)
2. TraderScorer evaluates (BacktestValidator, LiveTraderMonitor)
3. StrategyDNA analyzes winning strategies (DecisionCorrelator + AutoParamOptimizer)
4. User approves params → CopyTradingEngine replicates (DRY_RUN default)
5. Risk checks every 5 min (drawdown, equity cap)
6. Emergency stop releases on breach
```

## Configuration

### Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | DB connection | sqlite:///./database/catseye.db |
| `CATEYE_DATA_DIR` | Data directory | Platform-specific |
| `OWNEX_DESKTOP` | Desktop mode flag | `1` in Tauri sidecar |
| `ANTHROPIC_API_KEY` | FCC proxy key | `orion-dev-local` |
| `OPENROUTER_API_KEY` | OmniRoute key | `sk-...` |
| `CATEYE_CSRF_DISABLED` | Disable CSRF | `0` |

### Config Files
- `pyproject.toml` — Python deps, ruff, mypy, pytest
- `package.json` / `package-lock.json` — Frontend deps (workspace root)
- `src-tauri/Cargo.toml` — Rust deps, Tauri config
- `src-tauri/tauri.conf.json` — Tauri bundle config
- `~/.hermes/config.yaml` — Hermes CLI config
- `~/.config/opencode/config.json` — OpenCode config

## Versioning

- **SSOT**: `VERSION` file at repo root
- **Sync Script**: `scripts/sync_version.py` → propagates to pyproject.toml, package.json, Cargo.toml, tauri.conf.json
- **Current**: `7.0.0`

## Testing

### Commands
```bash
# Fast smoke (scoring + opportunity + scheduler)
make test-fast                    # 100 passed, 1 skipped

# Full suite (excludes test_security.py, test_vision_gateway.py, test_scheduler.py)
make test                         # ~3000+ tests

# Lint + typecheck + fast tests
make check

# Lint (with fixes)
make fmt
```

### Coverage
- **Backend**: pytest (400+ tests), pytest-timeout (60s default)
- **Frontend**: Vitest (226 tests), vue-tsc (strict)
- **Desktop**: pytest-qt (offscreen, 54 tests)
- **Security**: CSRF, rate limit, CORS, auth cookie — all tested

## Deployment

### Desktop Installer
- **MSI**: WiX Toolset (Windows Store compatible)
- **NSIS**: Traditional installer
- **Artifacts**: Built via GitHub Actions (`ownex-tauri-windows.yml`)
- **Verification**: `scripts/win/VERIFY-INSTALL.ps1` (health check, restart test, optional 24h soak)

### CI/CD
- **GitHub Actions**: 3 workflows (test, CI, release)
- **Lockfile**: Single `package-lock.json` at workspace root (SSOT)
- **Rust**: `cargo check` + `tauri build` in CI

## Known Limitations

| Area | Limitation |
|------|------------|
| Twin Trees | `core/` vs `cores/` not consolidated (runtime uses both) |
| Mobile Offline | Partial — queued actions only, no full offline DB |
| Watch | Read-only, no complex workflows |
| Supabase | Optional (Mobile only), degrades gracefully |
| AI Cost Tracking | Daily budget only, no per-request attribution |
| Investment Live | DRY_RUN only, no real money execution yet |

## Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| 7.0.0 | 2026-08-26 | RELEASE CANDIDATE: Capital spine, freqtrade, unified snapshot, Windows artifacts |
| 1.0.1-alpha | 2026-08-25 | Economic engine, CEO IncomeHome, DESIGN_SYSTEM SSOT |
| 4.7.0 | 2026-08-17 | DESKTOP LOCAL MODE, sidecar, DB in APPDATA, Add Target |
| 4.6.0 | 2026-08-11 | OAR, Career Engine, Android namespace unified, Tauri compiles |
| 4.5.0 | 2026-08-10 | SELF-1..8 resolved, Payment Compat, Knowledge Bridge, Threat Intel |

---

*Document generated from codebase audit. Last verified: 2026-08-27*