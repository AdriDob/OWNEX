# ORION Platform Architecture

> Version 4.1.0 — July 2026

## 1. System Overview

ORION is a multi-app intelligence platform for bug bounty hunting, investment management, and gambling analytics. It is NOT a microservices architecture. It is a modular monolith: a single Python process with self-contained applications (`apps/`) sharing a common platform layer (`core/` and `cores/`).

The system is designed around three principles:

1. **Monolithic modular** — single deployable unit, no network overhead between apps
2. **Event-driven communication** — apps communicate via EventBus, never via direct imports
3. **App isolation via manifests** — each app declares its dependencies, database, routers, and frontend routes in a declarative manifest

The codebase currently has 77 modules in `cores/`, 16 modules in `core/`, 3 registered apps (`cateye`, `atlas`, `odyssey`), and 516 passing tests. Development data lives under `~/.orion/` (SQLite databases, encrypted vault key, config, audit log, evidence files). The system can run as a desktop application (PyInstaller + pywebview), a browser-only application, or a Windows service.

```
+-------------------------------------------------------+
|                    ORION PLATFORM                      |
|                                                        |
|  +----------+  +----------+  +----------+             |
|  |  CATEYE  |  |  ATLAS   |  | ODYSSEY  |  ...apps   |
|  |  (bounty)|  | (invest) |  | (gambl.) |             |
|  +----------+  +----------+  +----------+             |
|       |              |             |                   |
|  +----------------------------------------------+     |
|  |          ORION Shared Platform (core/)       |     |
|  |  AppRegistry | EventBus | Extensions | Health|     |
|  |  Secrets     | Scheduler| DB Manager         |     |
|  +----------------------------------------------+     |
|       |                                                |
|  +----------------------------------------------+     |
|  |       CATEYE Legacy Modules (cores/)         |     |
|  |  EventBus | IdentityVault | Auth | Recovery  |     |
|  |  Financial| Crypto | Validation | Scheduler  |     |
|  +----------------------------------------------+     |
|       |                                                |
|  +----------------------------------------------+     |
|  |           SQLite / PostgreSQL                  |     |
|  +----------------------------------------------+     |
+-------------------------------------------------------+
```

## 2. App Architecture

### 2.1 ORION Core (`core/` + `cores/`)

The platform layer is split into two directories:

**`core/`** — ORION Platform shared services (introduced in v4.0.0):
- `core/app_registry.py` — discovers and loads apps from `apps/*/manifest.py`
- `core/events/event_bus.py` — `CoreEventBus`, a namespaced event bus with SQLite persistence and a bridge to the legacy CATEYE EventBus
- `core/extension/` — plugin system with `ExtensionManifest`, `HookRegistry`, `CapabilityRegistry`, and declarative settings
- `core/health/` — `HealthCenter`, a unified health monitoring engine that consolidates three legacy health systems (SystemHealthEngine, HealthMonitor, Watchdog)
- `core/secrets/` — `SecretsManager`, a centralized credentials store backed by IdentityVault with env var fallback
- `core/scheduler/` — core scheduler for app-level jobs
- `core/database/` — `DBManager` for multi-tenant database registration
- `core/api/routers.py` — platform-level REST endpoints (`/api/core/apps`, `/api/core/extensions`, `/api/core/secrets`, `/api/core/health`)

**`cores/`** — CATEYE legacy modules (the original bug bounty system):
- `cores/events/event_bus.py` — original async pub/sub EventBus with SQLite persistence (EventPriority, EVENT_PRIORITY_MAP)
- `cores/identity_vault.py` — `IdentityVault`, AES-256-GCM encrypted credential store for 8+ bug bounty providers
- `cores/auth/` — `TokenService` (encrypted token storage) + `SessionStore` (device-bound sessions)
- `cores/financial/` — `FinancialSyncScheduler`, `TruthLayer`, `Dashboard`, `TakenosConnector`, withdrawal management
- `cores/crypto/` — `CoinGeckoFeed`, `CryptoManager`, wallet connectors (BTC, EVM, Solana, Tron)
- `cores/recovery/` — `RecoveryEngine`, `CircuitBreaker`, `HealthMonitor`, `HealingRules`, `RecoveryStore`
- `cores/orion/` — ORION AI decision-making (`next_action.py`, `orion_agent.py`)
- `cores/validation/` — Hypothesis Challenger, Confidence Scorer, Validation Loop Engine
- `cores/agents/` — Multi-agent system with AgentBus (`bus.py`), agent types, coordinator

### 2.2 CATEYE (`apps/cateye/`)

Bug bounty intelligence system. The original application wrapped as an ORION Platform app.

- **Manifest**: `apps/cateye/manifest.py` — declares frontend routes, widgets, order=1
- **Database**: Uses the existing `database/db.py` (no separate DB)
- **Routers**: Auto-discovered from `api/routers/` by `api/main.py`
- **Scheduler**: Existing `api/scheduler.py` manages the autonomous pipeline (DISCOVER → RECON → HYPOTHESIS → VALIDATE → REPORT)
- **Frontend**: Vue 3 routes under `/cateye/`

### 2.3 ATLAS (`apps/atlas/`)

Personal investment management system for crypto, stocks, ETFs, bonds, and DeFi.

- **Manifest**: `apps/atlas/manifest.py` — declares `atlas.db` database, `Asset`/`Portfolio`/`Transaction`/`Wallet` models, its own API router, and 2 scheduler jobs (hourly price sync, daily rebalance check)
- **Connectors**: `apps/atlas/connectors/coinbase/`, `apps/atlas/connectors/kraken/` — exchange API integrations with HMAC-SHA256 / HMAC-SHA512 authentication
- **Frontend**: Vue 3 routes under `/atlas/`
- **Portfolio Engine**: `apps/atlas/engines/portfolio.py` — calculates total portfolio value, integrated with the financial dashboard

### 2.4 ODYSSEY (`apps/odyssey/`)

Gambling analytics and prediction markets. Analytical only — no automated betting.

- **Manifest**: `apps/odyssey/manifest.py` — declares `odyssey.db`, `Bankroll`/`Bet`/`Strategy` models, API router, 2 scheduler jobs (hourly bet sync, 6-hourly analytics calculation)
- **Frontend**: Vue 3 routes under `/odyssey/`

### 2.5 Hermes (`apps/hermes/`)

Communications module — future. Not yet implemented.

## 3. Core Subsystems

### 3.1 EventBus

There are THREE event bus systems in ORION:

| Bus | Location | Purpose | Persistence |
|---|---|---|---|
| CATEYE EventBus | `cores/events/event_bus.py` | System-wide events (findings, opportunities, reports) | SQLite via `EventBusEntry` model |
| ORION CoreEventBus | `core/events/event_bus.py` | App-level events with namespacing | SQLite via `EventRecord` in `orion_core.db` |
| AgentBus | `cores/agents/bus.py` | Agent-to-agent communication | In-memory (max 1000 events) |

The `CoreEventBus` bridges events to the CATEYE EventBus, so app events reach legacy subscribers. The `AgentBus` is bridged to the CATEYE EventBus via `bridge_agent_bus_to_eventbus()` in `api/main.py`.

```
       AgentBus ──> bridge_agent_bus_to_eventbus() ──> CATEYE EventBus
                                                              ^
       CoreEventBus ──> _bridge_to_legacy() ──────────────────┘
```

### 3.2 IdentityVault

`cores/identity_vault.py` provides AES-256-GCM encrypted credential storage for bug bounty platforms (HackerOne, Bugcrowd, Huntr, Immunefi, Intigriti, YesWeHack, GitHub, Synack).

- **Key**: Random 32-byte key generated via `secrets.token_bytes(32)`, stored in `~/.orion/identity_vault.key` (chmod 600)
- **Migration**: Automatically migrates vaults from the old machine-id-derived key (CVE-2 fix)
- **Usage**: Used by auth modules, financial modules, and the SecretsManager

### 3.3 Extension SDK

`core/extension/` provides a complete plugin system:

- **Manifest** (`manifest.py`): Declarative metadata — id, name, version, capabilities, hooks, settings, dependencies
- **Registry** (`registry.py`): Discovers extensions from `extensions/*/manifest.py`, validates dependencies, registers hooks and capabilities
- **Hooks** (`hooks.py`): 14 predefined hook points (`before_scan`, `after_report`, `before_publish`, etc.) with sync callbacks and short-circuit support
- **Capabilities** (`capabilities.py`): `{domain}:{name}` format, used for dependency resolution
- **Settings** (`settings.py`): Declarative settings with auto-generated UI
- **Hot reload**: Extensions can be loaded/unloaded at runtime
- **Failure isolation**: Exceptions in hook handlers don't crash the system

### 3.4 Health Center

`core/health/engine.py` provides a unified health monitoring system that consolidates three legacy systems:

- **HealthChecks**: Registered by name, with a check function and category (`system`, `background`, `integration`)
- **Status**: Green (all pass), Yellow (non-critical failures), Red (critical failures)
- **Snapshots**: In-memory (last 100), available via REST API at `/api/core/health`
- **Default checks**: event_bus, scheduler, database, identity_vault, hook_registry, extension_registry

### 3.5 Secrets Manager

`core/secrets/manager.py` provides a single point of access for all API keys and credentials:

- **Priority**: IdentityVault → Environment variable → Default value
- **Cache**: In-memory cache with per-key TTL
- **API**: REST endpoints at `/api/core/secrets` (GET, PUT, DELETE)

### 3.6 ORION AI Layer

`cores/orion/` and `cores/intelligence/` provide the AI decision-making layer that drives autonomous operation:

- **Next Action** (`cores/orion/next_action.py`): ORION evaluates all active targets and recommends the single highest-impact next action. The scheduler consults this to prioritize targets (1.5x priority boost for ORION-recommended targets).
- **RewardLearner** (`cores/intelligence/reward_learning.py`): Analyzes past outcomes (confirmed findings vs false positives) and adjusts vulnerability type weights. Successful finding types get higher priority in future scans. Adjustments range from 0.5x to 2.0x.
- **PriorityEngine** (`cores/intelligence/priority_engine.py`): Consumes data from OpportunityEngine, QuickWinDetector, and system alerts. Ranks all items by urgency and potential impact.
- **Auto-explain**: The scheduler logs `[ORION] Auto-prioritized X (priority=Y, why=Z)` for every ORION-driven decision, making the reasoning transparent.

### 3.7 Validation Pipeline with Hypothesis Challenger

`cores/validation/` implements a multi-stage validation pipeline that questions its own hypotheses before accepting them:

- **Hypothesis Generators** (`cores/engine/hypothesis/generators.py`): Generate vulnerability hypotheses from recon data and ZAP scan results.
- **HypothesisChallenger** (`cores/validation/challenger.py`): Before validating a hypothesis, the Challenger generates alternative explanations (7+ types: public resource, cache/stub, CDN, WAF, third-party, configuration, intended behavior), designs contradiction tests with info_gain scoring, and lists missing verifications.
- **ValidationLoopEngine** (`cores/validation/loop_engine.py`): Runs the challenger, then evaluates the hypothesis using the replayer. Produces a Verdict that includes alternative explanations, missing verifications, and uncertainty level.
- **ConfidenceScorer** (`cores/validation/confidence.py`): Calculates a confidence score (0.0-1.0) with an uncertainty penalty (-0.00 to -0.12) based on unresolved alternative explanations.

### 3.8 Multi-Agent System

`cores/agents/` implements an autonomous multi-agent architecture:

- **AgentBus** (`cores/agents/bus.py`): An in-process event bus with IEventBus interface. Agents publish and subscribe to typed events (AgentEvent with EventType, source, target, correlation_id, priority). Full traceability via `replay(correlation_id)`.
- **Agent types**: Specialized agents for discovery, recon, analysis, validation, and reporting. Each runs independently and communicates via the AgentBus.
- **Coordinator** (`cores/agents/coordinator.py`): Orchestrates multi-step pipelines. Tracks active pipelines, handles failures, and supports retry.
- **EventBus bridge**: All AgentBus events are forwarded to the system-wide CATEYE EventBus as `agent:*` events, enabling UI visibility and notification integration.

### 3.9 Scheduler Architecture

`api/scheduler.py` implements an autonomous pipeline scheduler with three key innovations:

- **Adaptive intervals**: Each pipeline stage has its own interval (discover=1h, recon=30min, hypothesis=15min, scope_check=1h, validate=2h, report=1h), allowing high-frequency hypothesis generation without overwhelming the system.
- **Per-target cooldown**: Targets are not re-scanned within 1 hour of their last scan, preventing redundant work on recently analyzed targets.
- **ORION-driven prioritization**: Targets are sorted by priority score before scanning. The score incorporates RewardLearner adjustments (vuln-type weights), ORION SCORE from Program records, recency of activity, and ORION's next-action recommendation. Stale cooldown entries are purged every cycle to prevent memory leaks.
- **WAL checkpoint**: At the end of every pipeline cycle, `PRAGMA wal_checkpoint(TRUNCATE)` prevents unbounded WAL growth on 24/7 systems.

### 3.10 Financial Layer

`cores/financial/` provides a comprehensive financial management system:

- **TruthLayer** (`truth_layer.py`): Single source of truth for all financial data with categories (verified, pending, withdrawn, estimated, manual, disputed)
- **Dashboard** (`dashboard.py`): Unified view of patrimonio total, breakdown by category, monthly income, goal tracking (Objetivo Libertad: $30,000)
- **CoinGecko** (`cores/crypto/coingecko.py`): Price feed for 30+ crypto assets with 60s cache, free tier
- **Takenos** (`cores/financial/takenos/`): Virtual USD wallet connector for LATAM freelancers with CSV import, manual balance entry, Solana USDC sync
- **Sync Scheduler** (`scheduler.py`): Periodic auto-sync for platforms and crypto wallets at configurable intervals
- **Withdrawal** (`withdrawal.py`): Complete withdrawal lifecycle (request → pending → complete/fail)
- **Reconciliation** (`reconciliation.py`): Discrepancy detection and resolution

## 4. Architecture Principles

### Monolithic Modular

Everything runs in a single Python process. Apps are isolated by convention, not by process boundaries. This gives us:

- **Simple deployment**: One process, one build, one binary (PyInstaller)
- **Shared infrastructure**: IdentityVault, secrets, health, database — all shared
- **No network overhead**: EventBus is in-process async pub/sub

### EventBus Communication

Apps NEVER import each other directly. They communicate through events:

- CATEYE events: `finding:created`, `opportunity:found`, `report:generated`, etc.
- Agent events: `PIPELINE_START`, `TASK_COMPLETE`, etc.
- App events: `atlas:price_updated`, `odyssey:bet_settled`, etc.

### App Isolation via Manifests

Every app declares its identity in `apps/<name>/manifest.py`:

```python
from core.interfaces.app import IAppPlugin

manifest = IAppPlugin(
    id="atlas",
    name="ATLAS",
    version="0.1.0",
    description="Personal Investment Dashboard",
    icon="TrendingUp",
    order=2,
    db_path="atlas.db",
    models=[Asset, Portfolio, Transaction, Wallet],
    routers=[atlas_router],
    router_prefix="atlas",
    scheduler_jobs=[...],
    frontend_routes=[...],
    widgets=[...],
    providers=PROVIDERS,
)
```

The `AppRegistry` (`core/app_registry.py`) is a singleton that manages the full app lifecycle:

1. **Discovery**: On startup, `discover()` scans `apps/` for directories containing `manifest.py`. Each manifest is imported and validated.
2. **Database registration**: For apps with `db_path` set, the `DBManager` registers the database and runs SQLAlchemy migrations.
3. **Router mounting**: All app routers are mounted on the FastAPI instance via `mount_routers()`. Each app gets a `/api/{router_prefix}` prefix.
4. **Scheduler registration**: Scheduler jobs declared in manifests are registered with the `CoreScheduler`.
5. **Extension bridge**: `discover_extensions()` bridges to the `ExtensionRegistry`, discovering and loading hook-based extensions from `extensions/`.
6. **Status reporting**: The `/api/core/apps` endpoint exposes all registered apps with their version, capabilities, and health.

### App Database Isolation

Each app with persistent data gets its own SQLite database file:
- ATLAS: `~/.orion/data/atlas.db` (Asset, Portfolio, Transaction, Wallet tables)
- ODYSSEY: `~/.orion/data/odyssey.db` (Bankroll, Bet, Strategy tables)
- CATEYE: Uses the main `catseye.db` via the existing `database/db.py` (shared with legacy modules)

This isolation allows independent migrations, rollbacks, and potential future extraction of apps into separate processes.

### App Frontend Integration

Apps declare UI routes and widgets in their manifest:
- **Frontend routes**: Vue 3 component paths mapped to route names (e.g., `/atlas/dashboard` renders `DashboardAtlas` component)
- **Widgets**: KPI cards for the home shell dashboard (e.g., portfolio value, active targets, bankroll total)
- **Shell navigation**: The ORION Platform shell dynamically builds navigation from registered app manifests

### Hooks vs Events

The system has two extension mechanisms:

- **Hooks** (`core/extension/hooks.py`): Synchronous callbacks that extend core behavior at specific points (before/after operations). Can short-circuit operations. For trusted extensions.
- **Events** (`core/events/event_bus.py`, `cores/events/event_bus.py`): Asynchronous pub/sub for communication between apps. No return value. For system-wide notifications.

## 5. Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI |
| Frontend | Vue 3, TypeScript, Tailwind CSS v4, Vite, ShadCN Vue |
| Database | SQLite (dev), PostgreSQL (prod), SQLAlchemy ORM |
| Desktop | PyInstaller (Windows/Linux), Capacitor (Android) |
| Testing | pytest (backend, 516 tests), Vitest (frontend) |
| Linting | Ruff (Python), Biome (frontend) |
| Type Checking | mypy (Python, strict partial) |
| Crypto | cryptography.hazmat (AES-256-GCM, Ed25519) |
| AI | Google Gemini API, OpenRouter |
| Build | PyInstaller one-dir, Vite, Capacitor |

## 6. Data Flow

### Scan Pipeline (CATEYE)

```
                     +-----------+
                     | DISCOVER  |  Scrape platforms for new programs
                     +-----------+
                          |
                          v
                     +-----------+
                     |   RECON   |  Subfinder, Amass, httpx, nuclei
                     +-----------+
                          |
                          v
                     +-----------+
                     | HYPOTHESIS|  Generate vulnerability hypotheses
                     +-----------+
                          |
                          v
                     +-----------+     +--------------------+
                     | VALIDATE  | --> | HypothesisChallenger|  Alternative explanations
                     +-----------+     +--------------------+
                          |
                          v
                     +-----------+
                     |  REPORT   |  Generate and submit reports
                     +-----------+
```

Each stage publishes events to the EventBus (`opportunity:found`, `discovery:completed`, `report:generated`). The scheduler uses ORION's `next_action` and `RewardLearner` to prioritize targets.

### Financial Sync

```
     +------------------+     +------------------+
     | Platform Sync    |     | Crypto Sync      |
     | (HackerOne, etc.)|     | (BTC, ETH, SOL)  |
     +------------------+     +------------------+
              |                        |
              v                        v
     +------------------+     +------------------+
     |   TruthLayer     |     | CoinGeckoFeed    |
     | (verified/pending|     | (price oracle)   |
     |  /withdrawn)     |     +------------------+
     +------------------+            |
              |                      |
              v                      v
     +-------------------------------------------+
     |           Unified Dashboard                |
     |  patrimonio_total | ingresos | alerts      |
     +-------------------------------------------+
```

The `FinancialSyncScheduler` runs at configurable intervals (default 30 min), syncing platform earnings and crypto wallet balances. Results are published as `financial:sync_completed` events.

## 7. Middleware Stack

The FastAPI application (`api/main.py`) applies middleware in this order (outermost first):

```
Request
  -> SecurityHeadersMiddleware (CSP, HSTS, XFO, XCTO, Referrer-Policy)
    -> CSRFMiddleware (double-submit cookie, exempt: health, auth)
      -> RateLimitMiddleware (per-identity token bucket)
        -> AuthMiddleware (Bearer JWT verification)
          -> ErrorHandlingMiddleware (catch-all, generic error response)
            -> Router (endpoint handlers)
```

All middleware is optional per-endpoint:
- Security headers apply to all responses
- CSRF exempts 5 paths (`/api/health`, `/api/license/activate`, `/api/auth/*`)
- Rate limiting exempts health, version, docs paths
- Auth is optional per-router (some routers like health are public)

## 8. App Lifecycle (Startup)

The full bootstrap sequence in `api/main.py`:

1. Database initialization (`db.init_db()` — creates tables, runs migrations)
2. EventBus + SystemState initialization (registers core services)
3. Product behavior rules check
4. Identity system initialization
5. AuthHub initialization (Gmail OAuth defaults)
6. Orchestrator initialization (suppresses low-confidence noise)
7. Execution layer initialization (tracker, scorecard, memory stores)
8. Opportunity engine discovery (scans for new opportunities)
9. Background scan scheduler start (autonomous pipeline)
10. Notification poller, WS bridge, notification bridges
11. Financial event system, auto-report subscriber, FP feedback subscriber
12. Multi-agent system startup
13. Financial auto-sync scheduler
14. AgentBus -> EventBus bridge
15. Discovery monitor, recovery engine, health monitor
16. ORION Platform bootstrap (app registry, DB manager, core scheduler, extensions, secrets, health center)

Each step is independently wrapped in try/except — failures degrade gracefully without crashing the system.

## 9. Directory Structure

```
.
├── core/                    # ORION Platform shared layer
│   ├── api/routers.py       # Platform REST endpoints
│   ├── app_registry.py      # App discovery and lifecycle
│   ├── database/            # Multi-tenant DB manager
│   ├── events/              # Namespaced event bus
│   ├── extension/           # Plugin system
│   ├── health/              # Unified health center
│   ├── interfaces/          # IAppPlugin, IAgent, IEventBus
│   ├── scheduler/           # Core job scheduler
│   └── secrets/             # Secrets manager
├── cores/                   # CATEYE legacy modules
│   ├── events/              # System EventBus
│   ├── identity_vault.py    # AES-256-GCM vault
│   ├── auth/                # TokenService, SessionStore
│   ├── financial/           # Truth layer, dashboard, Takenos
│   ├── crypto/              # CoinGecko, wallet connectors
│   ├── recovery/            # RecoveryEngine, CircuitBreaker
│   ├── validation/          # Hypothesis Challenger
│   ├── agents/              # Multi-agent system
│   └── orion/               # AI decision-making
├── apps/                    # Self-contained apps
│   ├── cateye/              # Bug bounty intelligence
│   ├── atlas/               # Investment management
│   └── odyssey/             # Gambling analytics
├── extensions/              # Hook-based plugins
├── api/                     # FastAPI application
│   ├── main.py              # App entry point, middleware, routers
│   ├── scheduler.py         # Scan pipeline scheduler
│   └── routers/             # API route handlers
├── frontend/                # Vue 3 frontend
├── database/                # SQLAlchemy models and DB setup
├── desktop/                 # Desktop launcher, tray, watchdog
└── tests/                   # Test suite (516 tests)
```
