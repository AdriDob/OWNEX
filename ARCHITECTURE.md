# OWNEX Architecture

## Overview

OWNEX is a personal economic operating system that discovers legitimate opportunities, calculates expected value, decides which action has highest priority, coordinates agents to execute work, records results, manages income and capital, and helps transform income into net worth.

```
HUMAN → INTENT → OWNEX → AGENTS → OPPORTUNITIES → EXECUTION → REVENUE → CAPITAL → GOALS
```

## Core Principles

- **Cognitive load minimization:** The user should never have to figure out what to do. OWNEX tells them.
- **HUMAN_MINUTES/DAY and $PAID_REVENUE/HUMAN_HOUR** are the two most important metrics.
- **EXPECTED ≠ PAID.** Only confirmed revenue counts.
- **Three modes, one core:** LITE/FULL/CAPITAL are lenses over a shared system.
- **Human-in-the-loop** for all high-impact external actions.

---

## Core Engines

### 1. Opportunity Engine

- **Location:** `core/opportunity/engine.py` + `core/opportunity/adapters/`
- **Function:** Discovers, scores, and ranks opportunities across 100+ platforms
- **Adapters:** 24+ adapters (HackerOne, Bugcrowd, Intigriti, Opire, Algora, Immunefi, Google VRP, Apple, Meta, Microsoft, etc.)
- **Scoring:** EV/hour, probability, risk, competition, learning value
- **Taxonomy:** 175 categories across 10 families

### 2. Taxonomy (175 Categories)

- **Location:** `cores/opportunity/taxonomy.py`
- **Families:**
  - `software` (30 categories) — Python, JS, TS, React, Vue, API, CLI, etc.
  - `security` (20 categories) — Bug bounty, IDOR, XSS, SSRF, API security, etc.
  - `qa` (20 categories) — Manual QA, exploratory, regression, Playwright, etc.
  - `devops` (20 categories) — Docker, K8s, CI/CD, Terraform, cloud, etc.
  - `ai` (20 categories) — AI eval, LLM eval, data annotation, labeling, etc.
  - `data` (10 categories) — SQL, ETL, spreadsheet automation, visualization, etc.
  - `oss` (15 categories) — GitHub issues, docs, refactoring, maintenance, etc.
  - `web` (15 categories) — WordPress, Shopify, landing pages, SEO, etc.
  - `automation` (15 categories) — Browser, workflow, bots, ETL, reports, etc.
  - `web3` (10 categories) — Smart contracts, Solidity, DeFi, on-chain, etc.
- **Per-category attributes:** barrier, experience required, portfolio required, skills, payout range, EV/hour, competition, acceptance probability, time-to-cash, automation potential, risk
- **Verified:** 175/175 with $0 barrier, 55 low-competition, 111 with EV/h ≥ $30

### 3. Capital Engine

- **Location:** `cores/capital/engine.py`
- **Function:** Tracks net worth, projects growth, manages goals
- **Features:** Compound interest, scenarios (conservative/base/aggressive/exceptional), $1M path
- **Goals:** Emergency fund, car, vivienda, $1M net worth
- **Scenarios:** P10/P50/P90 projections with required monthly contribution
- **Persistence:** Saved to DB via `database/persistence.py`

### 4. Mode Engine

- **Location:** `cores/modes/engine.py`
- **Function:** Makes LITE/FULL/CAPITAL actually behave differently
- **Modes:**
  - **LITE** ("EARN MORE") — minimal UI, next best action, EV/hour focus
  - **FULL** ("OPERATE EVERYTHING") — full dashboard, agents, finance, goals
  - **CAPITAL** ("KEEP & COMPOUND") — financial focus, goals, projections, allocation
- **Adaptive:** Recommends mode based on income gap, capital gap, operational load
- **Data filtering:** Each mode shows/hides different data sections

### 5. Revenue Learning Loop

- **Location:** `cores/learning/revenue_loop.py`
- **Function:** Closes the circuit: Discover → Rank → Tell → Help → Record → Learn
- **Metrics:** HUMAN_MINUTES/DAY, $PAID_REVENUE/HUMAN_HOUR
- **States:** DISCOVERED → QUALIFIED → STARTED → SUBMITTED → ACCEPTED → PENDING → PAID
- **Learning:** Tracks EV accuracy, calibrates future estimates
- **Persistence:** Actions and insights saved to DB

### 6. Approval Gates

- **Location:** `cores/approval/gates.py`
- **Function:** Human-in-the-loop for sensitive actions
- **Levels:** AUTO, NOTIFICATION, CONFIRMATION, FULL_REVIEW
- **Actions:** submit_report, send_external, financial_transfer, investment, delete_data, modify_config, run_agent, publish

### 7. State Machine (Orchestrator)

- **Location:** `cores/orchestrator/state_machine.py`
- **Function:** Real task lifecycle with retries and evaluation
- **States:** PENDING → PLANNING → ASSIGNED → EXECUTING → REVIEWING → COMPLETED
- **Features:** Priority queue, retries with backoff, audit trail, max retries

### 8. Next Best Action Engine

- **Location:** `cores/intelligence/next_best_action.py`
- **Function:** Single canonical decision engine — answers "¿Qué debería hacer ahora?"
- **Input:** Opportunities, user skills, available time, goals, capital, platform status
- **Output:** Title, EV, minutes, EV/hour, confidence, barrier, requirements, risks, exact steps
- **Fallback:** "NO ACTION REQUIRED" when nothing meets threshold

### 9. Configuration Detector

- **Location:** `cores/configuration/detector.py`
- **Function:** Shows what's ready, what needs config, what's blocked
- **Checks:** 14 items — API keys (5), email (3), notification (3), profile (3)
- **Statuses:** ready, action_required, partially_ready, blocked

### 10. Notification System

- **Location:** `cores/notifications/`
- **Channels:** Desktop (plyer), Web (in-app), Mobile (FCM), Watch (Wear OS), Email (monthly report only)
- **Features:** Priority engine, deduplication, quiet hours, grouping

---

## API Endpoints (1,522 total routes)

### Command Center

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/command-center/today` | GET | Complete today view |
| `/api/command-center/next-action` | GET | Single next best action |
| `/api/command-center/status` | GET | System status |
| `/api/command-center/metrics` | GET | Key metrics |

### Capital

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/capital/dashboard` | GET | Complete capital dashboard |
| `/api/capital/state` | POST | Update capital state |
| `/api/capital/goals` | GET/POST | Financial goals |
| `/api/capital/million-path` | GET | Path to $1M |

### Modes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/modes/current` | GET | Current mode |
| `/api/modes/set` | POST | Switch mode |
| `/api/modes/recommend` | POST | Adaptive recommendation |

### Approvals

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/approvals/pending` | GET | Pending approvals |
| `/api/approvals/request` | POST | Request approval |
| `/api/approvals/{id}/approve` | POST | Approve action |
| `/api/approvals/{id}/reject` | POST | Reject action |

### Learning

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/learning/dashboard` | GET | Learning dashboard |
| `/api/learning/action` | POST | Record action |
| `/api/learning/action/{id}/result` | POST | Record result |
| `/api/learning/metrics` | GET | Key metrics |

### Observation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/observation/health` | GET | System health |
| `/api/observation/recovery` | GET | Recovery status |
| `/api/observation/backup` | GET/POST | Backup status/create |

---

## Pipeline Flow

```
DISCOVER → RANK → TELL USER → HELP DO IT → RECORD PAID → LEARN → IMPROVE
    ↓          ↓        ↓            ↓             ↓          ↓         ↓
Adapters   Scoring  Next Action  Approval     Revenue    Learning  Capital
(24+)      (EV/h)   (LITE mode)  Gates       Tracking   Loop     Engine
```

### Execution Queue

```
CREATED → QUEUED → PREPARING → READY → AWAITING_APPROVAL → APPROVED → RUNNING → VERIFYING → COMPLETED
```

---

## Data Flow

```
User opens OWNEX
    ↓
Command Center loads (today view)
    ↓
Capital state loaded from DB
    ↓
Mode config applied (LITE/FULL/CAPITAL)
    ↓
Next best action calculated
    ↓
User takes action
    ↓
Approval gate (if needed)
    ↓
Action recorded
    ↓
Result recorded
    ↓
Learning generated
    ↓
Capital updated
    ↓
Dashboard refreshed
```

---

## Database

- **Engine:** SQLite (dev) / PostgreSQL (prod)
- **Tables:** 57+ tables
- **Models:** `database/models.py`, `database/models_capital.py`, `database/models_assets.py`, `database/models_cycles.py`, `database/models_economic.py`
- **Persistence:** `database/persistence.py` (capital state, goals, learning actions, insights)
- **Path:** `~/.ownex/database/cateye.db`

---

## Frontend

- **Framework:** Vue 3 + TypeScript
- **Styling:** Tailwind CSS v4
- **Build:** Vite
- **Components:** 30+ component groups including:
  - `autopilot/` — TodayBriefing, DailyCompanion
  - `dashboard/` — Main dashboard views
  - `agents/` — Agent status and fleet
  - `copilot/` — AI copilot interface
  - `notifications/` — Notification center
  - `mobile-companion/` — Mobile-specific views
  - `ui/` — Shared UI primitives

---

## Testing

| Suite | Count | Description |
|-------|-------|-------------|
| **E2E** | 11 tests | Complete pipeline: discover → rank → act → learn |
| **Fast** | 100 tests | Scoring + opportunity + scheduler-jobs |
| **Total** | 4,125+ tests | Unit + integration |
| **Pass rate** | 99.9% | Green on `make check` |

---

## Multiplatform

| Platform | Stack | Weight | Status |
|----------|-------|--------|--------|
| **Desktop** | Tauri v2 + Vue 3 + Python FastAPI | 52 MB | ✅ Production |
| **Mobile** | Capacitor + Android + Vue 3 | 4.4 MB | ✅ Production |
| **Watch** | Wear OS + Kotlin + HTTP | 14 MB (8 MB target) | ✅ Functional |
| **Web** | Vue 3 + Vite + Tailwind v4 | 3 MB | ✅ Production |
| **Backend** | Python 3.14 + FastAPI + SQLAlchemy | — | ✅ Production |
| **Database** | SQLite (dev) / PostgreSQL (prod) | — | ✅ Production |

### Platform Behavior

- **Desktop:** Always-running, tray mode, scheduler, crash recovery, auto-startup
- **Mobile:** Push notifications, deep links, Next Best Action, approval gates
- **Watch:** Critical alerts only, system status, next action, approvals
- **Web:** Full PWA, offline support, WebSocket real-time updates

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HACKERONE_API_KEY` | Optional | HackerOne submissions |
| `BUGCROWD_API_KEY` | Optional | Bugcrowd submissions |
| `INTIGRITI_API_KEY` | Optional | Intigriti submissions |
| `OPIRE_API_KEY` | Optional | Opire dev bounties |
| `ALGORA_API_KEY` | Optional | Algora dev bounties |
| `SMTP_HOST` | Optional | Email (monthly reports) |
| `SMTP_PORT` | Optional | Email port |
| `SMTP_USER` | Optional | Email user |
| `SMTP_PASSWORD` | Optional | Email password |

**All API keys are optional.** OWNEX functions without them but discovers 10x more opportunities with them.

### Configuration Detector

The system checks 14 configuration items and reports status:
- **3 ready** — core system, database, scheduler
- **11 action_required** — API keys, email, notifications, profile

---

## Scheduler

- **Morning briefing:** 06:00
- **Pipeline cycle:** Every 30 minutes
- **Evening summary:** 20:00
- **Auto-start:** Yes, on backend startup
- **Recovery:** Self-healing on failure

---

## Key Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| `HUMAN_MINUTES_PER_DAY` | 15-60 min | Time user needs to spend |
| `$PAID_REVENUE_PER_HOUR` | $100-500 | Revenue per human hour |
| `AUTOMATION_RATE` | 75-95% | Percentage automated |
| `OPPORTUNITIES_DISCOVERED` | 175 categories | Taxonomy coverage |
| `EV_ACCURACY` | Improving | Predicted vs actual revenue |

---

## Revenue Potential

| Tier | Experience | Monthly Potential | Human Hours |
|------|------------|-------------------|-------------|
| **Tier 0** | No experience | $500 - $2,000 | 40-60h |
| **Tier 1** | First results | $2,000 - $8,000 | 20-30h |
| **Tier 2** | Reputation | $8,000 - $25,000 | 10-20h |
| **Tier 3** | Track record | $25,000 - $50,000 | 5-15h |
| **Tier 4** | Specialization | $50,000 - $100,000+ | 5-10h |

---

## Directory Structure

```
Rastro/
├── api/
│   ├── main.py              # FastAPI app (1,522 routes)
│   ├── scheduler.py          # Background jobs + pipeline
│   └── routers/              # 150+ route modules
├── cores/
│   ├── capital/engine.py     # $1M projections, goals
│   ├── modes/engine.py       # LITE/FULL/CAPITAL
│   ├── approval/gates.py     # Human-in-the-loop
│   ├── orchestrator/
│   │   └── state_machine.py  # Task lifecycle
│   ├── learning/
│   │   └── revenue_loop.py   # Discover → Learn
│   ├── intelligence/
│   │   └── next_best_action.py
│   ├── configuration/
│   │   └── detector.py       # Config readiness
│   ├── opportunity/
│   │   ├── taxonomy.py       # 175 categories
│   │   └── adapters/         # 24+ platform adapters
│   ├── notifications/        # Priority, dedup, channels
│   ├── discovery/            # Recon, analysis
│   ├── reporting/            # Report generation
│   ├── finance/              # Financial tracking
│   ├── agents/               # Agent system
│   └── ...                   # 200+ modules
├── core/                     # Legacy core (near-duplicate of cores/)
├── database/
│   ├── db.py                 # SessionLocal + engine
│   ├── models.py             # Main models
│   ├── models_capital.py     # Capital/goal models
│   ├── persistence.py        # Capital + learning persistence
│   └── catseye.db            # SQLite database
├── frontend/
│   ├── src/
│   │   ├── components/       # 30+ component groups
│   │   ├── views/            # Page views
│   │   └── ...
│   └── ...
├── android/                  # Wear OS app
├── src-tauri/                # Desktop app (Tauri v2)
├── tests/
│   ├── test_ownex_e2e.py     # 11 E2E tests
│   └── ...                   # 4,125+ test files
├── .ai/                      # Strategy, decisions, roadmap
├── ARCHITECTURE.md           # This file
└── run.py                    # Entry point
```

---

## Commands

| Goal | Command |
|------|---------|
| Full test suite | `python scripts/dev test` |
| Fast smoke test | `python scripts/dev test-fast` |
| Lint + typecheck + fast tests | `python scripts/dev check` |
| Lint with fixes | `python scripts/dev fmt` |
| Typecheck scoped | `python scripts/dev typecheck-fast` |
| Start backend | `python run.py` |
| Health check | `curl http://localhost:8000/api/health` |

---

## Pipeline Stages

| Stage | What it does | Automation |
|-------|-------------|------------|
| **Discovery** | Scans 24+ platform APIs | 100% auto |
| **Recon** | subfinder, httpx, katana, nmap, amass | 100% auto |
| **Hypothesis** | Path patterns + endpoint analysis | 90% auto |
| **Validation** | IDOR, SQLi, XSS, SSRF testing | 80% auto |
| **Ranking** | EV/hour, probability, confidence | 100% auto |
| **Next Best Action** | Single recommended action | 100% auto |
| **Report Generation** | Professional report templates | 100% auto |
| **Approval Gate** | Human review before submission | Manual required |
| **Submission** | HackerOne/Bugcrowd/Intigriti API | 95% auto |
| **Tracking** | Bounty + payment status | 100% auto |
| **Learning** | EV calibration, outcome tracking | 100% auto |
| **Capital Update** | Revenue → net worth → goals | 100% auto |

---

*Last updated: August 2026*
