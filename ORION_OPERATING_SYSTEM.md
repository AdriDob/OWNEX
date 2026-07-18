# ORION Operating System

> **Master Reference Document — July 2026**
> Single source of truth for architecture, frontend, backend, design system, APIs, deployment, and operations.

---

## 1. Architecture

### 1.1 Principles

| Principle | Description |
|---|---|
| Modular Monolith | Single process, shared EventBus, isolated app modules |
| Event-Driven | Async communication via EventBus (SQLite-persisted) |
| Revenue First | Every feature must increase detection, evidence quality, or acceptance |
| Zero Debt | No `TODO` without date, no unused imports, no dead code |
| Restart-Proof | All critical state survives restart (SQLite, not RAM) |

### 1.2 Module Map

```
orion/
├── core/                    # Shared platform services
│   ├── events/              # EventBus, EventStore, correlation
│   ├── health/              # HealthCenter, checks, snapshots
│   ├── secrets/             # SecretsManager (AES-256-GCM vault)
│   ├── knowledge/           # Knowledge Graph (KGNode, KGEdge)
│   ├── capabilities/        # CapabilityRegistry
│   ├── memory/              # Unified Memory (namespaces, tags, embedding)
│   ├── extension/           # Extension SDK (hooks, manifest, hot reload)
│   ├── commands/            # Command system (107 registered commands)
│   ├── execution/           # EP-5 Runtime (state machine, worker, journal)
│   ├── setup/               # Configuration Wizard v2
│   ├── backup/              # Backup engine
│   ├── copilot/             # Senior Copilot Agent (5 authority levels)
│   └── revenue/             # RevenueMetrics, RevenuePipeline
├── cores/                   # Original CATEYE modules
│   ├── orion/               # ORION logic (next_action, reward_learning)
│   ├── validation/          # Hypothesis Challenger, ConfidenceScorer
│   ├── evidence/            # EvidenceComposer, PoC generation
│   ├── offensive/           # Reasoners (IDOR, SSRF, XSS, SQLi, Auth)
│   ├── evolution/           # EvolutionEngine (Observe→Improve cycle)
│   └── financial/           # Financial dashboard, crypto, takenos
├── api/                     # FastAPI backend
│   ├── main.py              # App factory, middleware, health, system/status
│   └── routers/             # Endpoints by domain
├── apps/                    # Self-contained application plugins
│   ├── hermes/              # Desktop automation agent
│   ├── aegis/               # Security audit app
│   └── atlas/               # Financial intelligence
├── frontend/                # Vue 3 + TypeScript + Tailwind v4
│   └── src/
│       ├── pages/           # Page components (MissionControl, etc.)
│       ├── components/      # UI components (GlassCard, KPIBlock, etc.)
│       └── lib/             # API client, utils
├── database/                # SQLAlchemy models + migrations
├── tests/                   # pytest suite (1401 tests)
└── desktop/                 # Tauri desktop shell
```

### 1.3 Event Bus

| Aspect | Detail |
|---|---|
| Type | In-process async pub/sub |
| Persistence | SQLite via EventStore for replay |
| Correlation | Contextvar-based CorrelationId propagation |
| Bridge | Legacy CATEYE EventBus ↔ CoreEventBus bidirectional |
| Key events | `finding:*`, `target:*`, `report:*`, `command:*`, `execution:*` |

### 1.4 Data Flow

```
Discovery → Targets → Scans → Hypotheses → Validation → Findings → Reports → Submission → Payout
     ↑                                                                                       |
     └────────────────────── RewardLearning (feedback loop) ─────────────────────────────────┘
```

---

## 2. Frontend

### 2.1 Tech Stack

| Layer | Technology |
|---|---|
| Framework | Vue 3 + Composition API (`<script setup lang="ts">`) |
| Language | TypeScript (strict) |
| Styling | Tailwind CSS v4 |
| Icons | Lucide Vue |
| Charts | D3.js (Knowledge Graph) |
| Build | Vite |
| Type Check | vue-tsc |

### 2.2 Design System

#### Palette

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#050508` | Base background |
| `--surface` | `#0d0d14` | Card surface |
| `--primary` | `#a855f7` | Purple accent |
| `--accent` | `#7c3aed` | Secondary accent |
| `--gold` | `#f5a623` | Revenue/gold |
| `--success` | `#00ff41` | Positive metrics |
| `--warning` | `#f59e0b` | Warnings |
| `--destructive` | `#ef4444` | Errors |
| `--info` | `#3b82f6` | Info |
| `--foreground` | `#f1f5f9` | Primary text |
| `--muted` | `#64748b` | Secondary text |

#### Typography

| Usage | Font |
|---|---|
| Headings | `Inter`, sans-serif (via font-display) |
| Body | `Inter`, sans-serif |
| Code/Metrics | `JetBrains Mono`, monospace (via font-mono) |

#### Components

| Component | Props | Variants |
|---|---|---|
| `GlassCard` | `variant`, `hover-lift` | default, premium, highlight, gold |
| `KPIBlock` | `value`, `label`, `format`, `color`, `size`, `trend` | number, currency, percent |
| `StatusDot` | `status`, `size`, `pulse` | online, offline, warning, error, info, gold |
| `PremiumButton` | `variant`, `loading`, `disabled`, `size` | default, gold, ghost, outline, danger |

#### Animations

| Class | Effect |
|---|---|
| `.animate-in` | Fade in + slide up on mount |
| `.hover-lift` | Subtle translateY + glow on hover |
| `.glow-premium` | Purple glow on interactive elements |
| `.scanline` | CRT scanline overlay (aesthetic) |

### 2.3 Pages

| Route | Page | Data Sources |
|---|---|---|
| `/` | MissionControl | /mission/status, /mission/widget, /activity, /system/status, /evolution/bottlenecks, /revenue/mission-summary, /revenue/metrics |
| `/targets` | TargetsPage | /targets, /targets/* |
| `/findings` | FindingsPage | /findings |
| `/reports` | ReportCenter | /reports |
| `/revenue` | RevenueDashboard | /revenue/metrics |
| `/knowledge-graph` | KnowledgeGraphPage | /knowledge/nodes, /knowledge/edges |
| `/health-center` | HealthCenter | /core/health/summary |
| `/workflows` | Workflows | /workflows |
| `/settings` | Settings | /settings/* |
| `/apps/aegis` | DashboardAegis | AEGIS API |

---

## 3. Backend

### 3.1 Core APIs

| Endpoint | Method | Description |
|---|---|---|
| `/api/mission/status` | GET | Unified status: system health, apps, next action, priorities, ingress |
| `/api/mission/widget` | GET | Compact KPI data (active targets, high priority, evidence ready, reports pending, expected value) |
| `/api/system/status` | GET | Full system health (uptime, watchdog, CPU/mem, agents, pipeline, DB size) |
| `/api/health` | GET | Minimal health check |
| `/api/stats` | GET | Entity counts (targets, findings, endpoints, etc.) |
| `/api/activity` | GET | Activity feed (findings, verdicts, scans, evidence) |
| `/api/overview` | GET | Overview statistics |

### 3.2 Revenue APIs

| Endpoint | Method | Description |
|---|---|---|
| `/api/revenue/mission-summary` | GET | Lightweight KPIs for Mission Control |
| `/api/revenue/metrics` | GET | Full dashboard: payout summary, monthly revenue, ROI by program/vuln type, acceptance rate, time metrics, finding pipeline |
| `/api/revenue/summary` | GET | Aggregate revenue stats |
| `/api/revenue/submissions` | GET | Submission records |
| `/api/revenue/payouts` | POST | Record a payout |
| `/api/revenue/submit` | POST | Submit finding to platform |
| `/api/revenue/sync/{platform}` | POST | Sync payouts from platform |

### 3.3 Intelligence APIs

| Endpoint | Method | Description |
|---|---|---|
| `/api/offensive/*` | GET/POST | Reasoners, planner, curiosity, triager |
| `/api/evolution/bottlenecks` | GET | Bottleneck analysis |
| `/api/evolution/analyze` | GET | Full evolution cycle results |
| `/api/reports/quality` | GET | Report quality scoring |

### 3.4 Core Platform APIs

| Endpoint | Method | Description |
|---|---|---|
| `/api/core/extensions` | GET | Extension registry |
| `/api/core/secrets` | GET/POST/DELETE | Secrets Manager |
| `/api/core/health/summary` | GET | Unified health summary |
| `/api/core/health/snapshots` | GET | Health history |
| `/api/core/health/checks` | GET | Individual check results |
| `/api/core/knowledge/nodes` | GET/POST/DELETE | KG nodes |
| `/api/core/knowledge/edges` | GET/POST | KG edges |
| `/api/core/knowledge/stats` | GET | KG statistics |
| `/api/core/integrations` | GET | Integration status list |
| `/api/core/integrations/{name}` | GET | Single integration status |
| `/api/core/integrations/{name}/test` | POST | Test integration connection |
| `/api/core/commands` | GET | Command registry |
| `/api/core/commands/{name}/execute` | POST | Execute a command |
| `/api/core/wizard/*` | GET/POST | Configuration wizard |

### 3.5 Mission Control Data Flow

```
MissionControl.vue
  ├── /api/mission/status        → system, apps, next_action, priorities, ingress
  ├── /api/mission/widget        → active_targets, high_priority, evidence_ready, reports_pending, expected_value
  ├── /api/activity              → events[{id, type, title, severity, timestamp}]
  ├── /api/system/status         → status, uptime, watchdog, system{mem/cpu}, agents, pipeline
  ├── /api/evolution/bottlenecks → bottlenecks[{name, runs, total_hours, status, avg_ms}]
  ├── /api/revenue/mission-summary → total_payout, total_pending, monthly_revenue, acceptance_rate
  └── /api/revenue/metrics       → payout_summary, roi_by_program, roi_by_vuln_type, time_metrics, finding_pipeline
```

---

## 4. Design System (Detailed)

### 4.1 GlassCard Variants

| Variant | Background | Border | Glow |
|---|---|---|---|
| `default` | `bg-surface/30` | `border-border/20` | None |
| `premium` | `bg-black/40` | `border-primary/10` | `shadow-[0_0_15px_-3px_rgba(168,85,247,0.15)]` |
| `highlight` | `bg-black/40` | `border-l-primary` | Same as premium |
| `gold` | `bg-black/40` | `border-gold/20` | `shadow-[0_0_15px_-3px_rgba(245,166,35,0.15)]` |

### 4.2 KPIBlock Formats

| Format | Display |
|---|---|
| `number` | `value.toLocaleString()` |
| `currency` | `$value.toLocaleString()` |
| `percent` | `(value / 100).toFixed(1) + '%'` |

### 4.3 StatusDot States

| State | Color | Ping Animation |
|---|---|---|
| `online` | `bg-success` | Yes |
| `offline` | `bg-destructive` | No |
| `warning` | `bg-warning` | Yes (slow) |
| `error` | `bg-destructive` | Yes |
| `info` | `bg-info` | No |
| `gold` | `bg-gold` | Yes |

---

## 5. Knowledge Graph

| Aspect | Detail |
|---|---|
| Storage | SQLite (nodes + edges tables) |
| Node types | TARGET, FINDING, ENDPOINT, CVE, REPORT, DECISION, TOOL |
| Edge types | RELATED_TO, LEADS_TO, EVIDENCE_FOR, PART_OF, MENTIONS |
| Scoring | Balance scoring (for/against/neutral with weighted confidence) |
| API | `/api/core/knowledge/*` |
| Integration | Auto-recorded via EventBus (`finding:*`, `target:*`) |
| Frontend | D3 force-directed graph with color-coded nodes, drag, glow |

---

## 6. Scheduler

| Stage | Action | Event |
|---|---|---|
| DISCOVER | Scrape + create targets → publish `opportunity:found` | Auto-discovers new targets |
| RECON | Scan targets → publish `discovery:completed` | Uses ORION next_action for priority |
| HYPOTHESIS | Generate hypotheses | Fixed: imports `generate_hypotheses` |
| VALIDATE | Evaluate hypotheses | Fixed: uses `ValidationLoopEngine` |
| REPORT | Generate reports | Fixed: `create_report_from_findings` |
| Auto-report | Event subscriber on `finding:confirmed` | Creates report draft automatically |

---

## 7. Senior Copilot Agent

| Component | Description |
|---|---|
| Authority Levels | Observer, Assistant, Operator, Senior Hunter, Administrator |
| Decision Confidence | no_action, request_approval, safe_execute, auto_close |
| Policy Engine | 6 centralized safety rules (add/remove at runtime) |
| Context Builder | Aggregates finding, evidence, verdict, confidence, memory |
| Explanation Engine | Verdict, confidence, action, changes, alternatives |
| Planner | 6 vuln type planners (IDOR, SSRF, XSS, SQLi, Auth Bypass, Generic) |
| Finding Analyzer | Evidence quality, inconsistencies, alternatives, confidence |
| Auditors | Health, Configuration, Security, Architecture |
| Pre-Report Review | 9 items: evidence, reproducibility, CVSS, CWE, impact, remediation |
| Recommender | Context-aware next-step suggestions |
| Memory Integration | Unified Memory with namespace isolation |

---

## 8. Revenue Pipeline

| Stage | Description |
|---|---|
| Submission | Submit finding → platform report |
| Status Check | Poll platform for acceptance/rejection |
| Payout Sync | Sync confirmed payouts from platform |
| Reward Learning | Adjust weights based on outcome |
| Metrics | Monthly revenue, ROI by program/vuln type, acceptance rate, time to payout |

### 8.1 Supported Platforms

| Platform | Submission | Payout Sync | Status | Priority |
|---|---|---|---|---|
| HackerOne | ✅ | ✅ | v1 | High |
| Bugcrowd | ✅ | ✅ | v1 | High |
| Intigriti | ✅ | ✅ | v1 | Medium |
| Immunefi | ❌ | ❌ | Pending | **P1** |
| Code4rena | ❌ | ❌ | Pending | P1 |
| YesWeHack | ❌ | ❌ | Pending | P5 |

---

## 9. Financial Intelligence

| Module | Description |
|---|---|
| CoinGecko feed | 30+ crypto prices, 24h change, cache, free tier |
| Takenos connector | Balance, CSV import, Solana USDC sync |
| Dashboard | Patrimonio total, breakdown, objetivo 30K, ingresos del mes |
| Integrations status | 🟢🟡🔴 per connector |

---

## 10. Deployment

| Mode | Command |
|---|---|
| Development | `python run.py --dev` |
| Desktop | `python run.py` (serves frontend from Vite) |
| Production | `python run.py --host 0.0.0.0 --port 8000` |
| Windows | `npx tauri dev` (Tauri desktop shell) |

### 10.1 Health Checks

| Check | What It Verifies |
|---|---|
| `python run.py --check` | System health, rolling 24h, 5 min critical window |
| `python run.py --doctor` | Deep diagnostics: DB, vault, EventBus, scheduler, agents |

### 10.2 Environment

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | AI provider |
| `GEMINI_API_KEY` | AI provider (fallback) |
| `CATEYE_DESKTOP` | Set to `1` in desktop mode |
| `RANCHER_API_KEY` | External API |
| `TAKENOS_API_KEY` | Takenos payments |

---

## 11. Testing

| Suite | Command | Tests |
|---|---|---|
| Backend | `.venv/bin/python -m pytest --timeout=60 -q` | 1401 |
| Frontend | `npm run test:unit` (vitest) | — (not yet) |
| Lint (Python) | `.venv/bin/python -m ruff check .` | 0 errors |
| Lint (Frontend) | `npx biome check .` | — |
| Type Check | `npx vue-tsc -b` | 15 pre-existing errors (non-blocking) |
| Build | `npm run build` | Passes |

### 11.1 Known Pre-Existing TypeScript Errors

| File | Error | Impact |
|---|---|---|
| `App.vue` | `computed` not imported | Cosmetic |
| `RevenueDashboard.vue` | Badge variant type mismatch (9x) | Badge styling |
| `DashboardAegis.vue` | Component type (2x) | Dynamic component rendering |
| `TargetsPage.vue` | Badge variant | Badge styling |
| `Workflows.vue` | Badge variant (2x) | Badge styling |
| `KnowledgeGraphPage.vue` | Router param undefined | Navigation edge case |

All are type-level, non-functional issues.

---

## 12. KPIs

| Metric | Source | Display |
|---|---|---|
| Health Score | `/api/mission/status → system.health_score` | Badge (0-100) |
| Active Targets | `/api/mission/widget → active_targets` | KPI |
| High Priority | `/api/mission/widget → high_priority` | KPI |
| Evidence Ready | `/api/mission/widget → evidence_ready` | KPI |
| Reports Pending | `/api/mission/widget → reports_pending` | KPI |
| Expected Value | `/api/mission/widget → expected_value` | KPI ($) |
| Total Payout | `/api/revenue/mission-summary → total_payout` | Revenue KPI |
| Monthly Revenue | `/api/revenue/mission-summary → monthly_revenue` | Revenue KPI |
| Acceptance Rate | `/api/revenue/mission-summary → acceptance_rate` | Revenue KPI |
| Top Programs | `/api/revenue/metrics → roi_by_program` | List |
| Top Vuln Types | `/api/revenue/metrics → roi_by_vuln_type` | List |
| Time to Payout | `/api/revenue/metrics → time_metrics` | Metrics row |

---

## 13. Status Indicators

| Component | Location | Update Interval |
|---|---|---|
| Mission Control data | Full page | 30s auto-refresh |
| Status Bar | Fixed bottom | 15s auto-refresh |
| System Health | Header badge | 30s |
| Revenue Pipeline | Revenue section | 30s |
| Recent Activity | Activity column | 30s |
| Knowledge Graph | KG column | On page load |

---

## 14. ORION Assistants

| Character | Context Trigger | Colors |
|---|---|---|
| Merlin (🧙 Wizard) | General wisdom | Purple primary |
| Clippy (📎 Office) | Discovery/recon | Blue accent |
| Rover (🐕 Dog) | Findings/evidence | Green success |
| Links (🔗 Chain) | Reports/quality | Gold |
| The Dot (🔴 Minimal) | Revenue/finance | Red/warning |
| F1 (🏎️ Pit Crew) | Performance/bottlenecks | Info/blue |

---

## 15. Recovery Procedures

| Scenario | Action |
|---|---|
| Backend crash | `python run.py` — auto-restores state from SQLite |
| DB corruption | `python run.py --backup` → restore from `~/.orion/backups/` |
| Vault corruption | Delete `~/.orion/identity_vault.key` and `~/.orion/identity.vault` → re-initialize |
| Lost API keys | Re-enter via Settings → Secrets Manager |
| Scheduler stuck | `python run.py --doctor` → inspect → restart |
| Frontend build failure | `cd frontend && npm ci && npm run build` |
| WAL file growth | Auto-checkpoint every scheduler cycle |
| Hermes action failure | Check `~/.orion/hermes_actions.jsonl` for error details |

---

## 16. Roadmap

See `.ai/ROADMAP.md` for prioritized roadmap with 5 phases.

**Current Priority**: P1 — Revenue Ready (HTTP probe, report templates, platform connectors, auto feedback loop)

---

*This document is the single source of truth for ORION system architecture. If any other document contradicts this, update this document.*
