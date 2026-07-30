# MODULE INDEX — OWNEX OMEGA v7.0

**Generated from code investigation:** 2026-07-30

---

## Backend Modules (`core/`, `cores/`, `api/`)

| Module | Path | Purpose | Responsibility | Dependencies | Status | Stability | Coverage | Last Modified |
|--------|------|---------|----------------|--------------|--------|-----------|----------|---------------|
| **Cycles** | `core/cycles/` | Security, Forge, Pulse, Executive Dashboard, Knowledge Capture | Cycle lifecycle, stage estimates, offensive category | `database`, `models`, `scheduler` | 🟡 Security 85%, Forge/Pulse 🔴 | High | Partial | 2026-07-30 |
| **Scheduler** | `api/scheduler.py` | 10-stage autonomous pipeline | Discover→Recon→Hypothesis→Auto-validate→Promote→Validate→Report→AI Bounty | All cores, EventBus, COPILOT | ✅ Running | High | — | 2026-07-30 |
| **Opportunity** | `core/opportunity/` | Unified scoring, Top5, history | EV, acceptance, difficulty, competition, fit, personal history | `core/priority`, `core/revenue`, `cores/opportunity` | ✅ 23 tests | High | 100% | 2026-07-26 |
| **Revenue** | `core/revenue/` + `cores/financial/` | Multi-platform payouts, metrics | USD/ARS, 5 payment methods, USD/hour, dashboard | `database/models_economic`, `CoinGecko` | ✅ Production | High | — | 2026-07-24 |
| **Health** | `core/health/` | Unified checks, snapshots | 3 legacy systems → 1, green/yellow/red, WAL | `database`, all cores | ✅ 25 tests | High | 100% | 2026-07-23 |
| **Offensive** | `core/offensive/` | 5 reasoners | IDOR, Auth Bypass, SSRF, XSS, SQLi reasoning | `cores/validation`, `core/evidence` | ✅ 101 tests | High | 100% | 2026-07-23 |
| **Evidence** | `core/evidence/composer.py` | PoC, CVSS, CWE, CAPEC, OWASP, MITRE | Report-ready evidence packages | `core/offensive`, `core/reports` | ✅ 37 tests | High | 100% | 2026-07-23 |
| **Reports** | `core/reports/` | Quality gate, acceptance optimizer | Remediation DB (12 types), CWE_MAP, context builder | `core/evidence`, `core/learning` | ✅ 18 tests | High | 100% | 2026-07-23 |
| **Learning** | `core/learning/verdict_learner.py` | FeedbackTuner ↔ AcceptanceLearner | Auto-outcome recording, weight adjustments | `core/reports/acceptance` | ✅ 14+18 tests | High | 100% | 2026-07-23 |
| **Recon** | `cores/recon/` | NaabuRunner, dedup, ReconRunner | Port scanning, service detection, deduplication | `cores/tools/naabu`, `database` | ✅ 23 tests | High | 100% | 2026-07-23 |
| **Auto-Hunter** | `core/auto_hunter/` | AI Bounty (4 programs) | EV ranking, scheduler 2h, findings | `core/ai_bounty`, `scheduler` | ✅ 29 tests | High | 100% | 2026-07-23 |
| **Auto-Submit** | `core/auto_submit/pipeline.py` | Quality gate, platform detection | Submission automation, EventBus | `core/reports`, `EventBus` | ✅ 12 tests | High | 100% | 2026-07-23 |
| **Target Intel** | `core/target_intelligence/prioritizer.py` | EV + tech + attack plans | Budget-aware prioritization, ORION integration | `cores/orion`, `RewardLearner` | ✅ 22 tests | High | 100% | 2026-07-23 |
| **Agents (7)** | `cores/agents/` | 7 autonomous agents | Copilot, Recon, Hypothesis, Validation, Report, Economic, Orion | `EventBus`, `scheduler` | ✅ Wired | High | — | 2026-07-23 |
| **Agents (12 OMEGA)** | `cores/agents/omega/` | 12 autonomous agents | Observer, Researcher, Planner, Architect, Developer, Reviewer, Validator, Documentation, Repair, Infrastructure, Learning, Evolution | `EventBus`, `scheduler`, `cycles` | 🔴 Not created | — | — | — |
| **Commands** | `core/commands/` | 107 commands, 14 categories | Permission-gated execution, EventBus | `EventBus`, `permissions` | ✅ 45 tests | High | 100% | 2026-07-23 |
| **Hermes v2** | `apps/hermes/` | Events, permissions, security | 7 event types, 5 risk levels, path/PID validation | `EventBus`, `core/commands` | ✅ 48 tests | High | 100% | 2026-07-23 |
| **Secrets** | `core/secrets/manager.py` | Vault, AES-256-GCM | IdentityVault bridge, env fallback, REST API | `cryptography`, `database` | ✅ 11 tests | High | 100% | 2026-07-23 |
| **Extension SDK** | `core/extension/` | Manifest, hooks, capabilities, registry | Discovery, load, capability index, hot reload | `EventBus`, `settings` | 🟡 Discovery works | Medium | — | 2026-07-23 |
| **Workflows** | `core/workflows/` | Workflow engine | Definition, execution, state | `EventBus`, `database` | ✅ Production | Medium | — | 2026-07-23 |
| **Sync** | `core/sync/` | Sync engine | Multi-source synchronization | `database`, `EventBus` | ✅ Production | Medium | — | 2026-07-23 |
| **Documentation** | `core/documentation/` | Auto-generation | Models, registrar, introspect (18 modules) | `ast`, `inspect` | ✅ Production | Medium | — | 2026-07-23 |
| **Finance Core** | `core/finance/` | Models, engine | Ledger, transactions, accounts | `database` | ✅ Production | Medium | — | 2026-07-23 |
| **Reports Core** | `core/reports/` | Core module | Base report models, services | `database` | ✅ Production | Medium | — | 2026-07-23 |
| **Priority/EV** | `core/priority/ev_engine.py` | Expected Value computation | EV formula, multipliers, adjustments | `RewardLearner`, `TargetIntel` | ✅ Production | High | — | 2026-07-23 |
| **Tools** | `cores/tools/` | Amass, Naabu, Shodan, Uncover, Censys, Garak, Gitleaks, BrowserUse | External tool adapters, unified result | `subprocess`, `httpx` | ✅ Registered | High | — | 2026-07-24 |
| **Bounty Scraper** | `cores/bounty_scraper/` | Multi-platform discovery | ProgramChangeTracker, payout ranking | `httpx`, `database` | ✅ 25 tests | High | 100% | 2026-07-23 |
| **Validation** | `cores/validation/` | Loop engine, challenger, confidence | AlternativeExplainer (7), ContradictionTest, MissingVerifications | `core/offensive`, `core/evidence` | ✅ Production | High | — | 2026-07-23 |
| **Pipeline** | `cores/pipeline/` | Hypothesis bridge, report service | Hypothesis→Finding, report generation | `core/opportunity`, `core/evidence` | ✅ Production | High | — | 2026-07-23 |
| **Notifications** | `cores/notifications/` | Discord (12), intelligent manager | Smart notification routing, config API | `EventBus`, `discord.py` | ✅ Production | Medium | — | 2026-07-24 |
| **Integrations** | `cores/integrations/` | ARCA, Outlook | External platform connectors | `httpx`, `oauth` | ✅ Production | Medium | — | 2026-07-23 |
| **Crypto** | `cores/crypto/` | CoinGecko, technical analysis | 30+ prices, RSI/SMA/MACD, signals | `httpx` | ✅ Production | Medium | — | 2026-07-24 |
| **ORION** | `cores/orion/` | Next action, EVH scoring | Strategic recommendations, portfolio scoring | `RewardLearner`, `Program` | ✅ Production | High | — | 2026-07-23 |
| **AI Security** | `core/intel/llm_scanner.py` | Garak scanner, AI bounty | Local model scanning, 5 unit tests | `cores/tools/extra.py` | 🟡 Unit tests pass | Medium | 45% | 2026-07-23 |
| **Evolution** | `core/evolution/` | 9 modules (stubs) | Self-evolution, design, heal, test, watch | None (not wired) | 🔴 Stubs only | Low | 0% | 2026-07-30 |

---

## Frontend Modules (`frontend/src/`)

| Module | Path | Purpose | Data Source | Status | Stability |
|--------|------|---------|-------------|--------|-----------|
| **Pages** | `pages/` | 20+ route components | `ownexData.ts` service | 🟡 Mixed | High |
| **Services** | `services/ownexData.ts` | Central API client | 7+ real endpoints | ✅ Real | High |
| **Composables** | `composables/` | useAssistant, useCompanion | Local + API | ✅ Real | High |
| **UI Components** | `components/ui/` | DataTable, Drawer, Modal, Select | ShadCN Vue + Tailwind v4 | ✅ Production | High |
| **Aegis App** | `components/apps/aegis/` | Security app UI | Backend Aegis | ✅ Production | Medium |
| **Layout** | `layouts/` | MainLayout, Sidebar, Header | Local state | ✅ Production | High |

### Page Details

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

---

## Extension Modules (`extensions/`)

| Extension | Path | Domain | Capability | Manifest | Connector | Status |
|-----------|------|--------|------------|----------|-----------|--------|
| LightRAG | `extensions/lightrag/` | Knowledge Graph | RAG retrieval, graph query | ✅ | ✅ | Discovered |
| Cognee | `extensions/cognee/` | Cognitive Memory | Memory graph, reasoning | ✅ | ✅ | Discovered |
| Graphiti | `extensions/graphiti/` | Temporal KG | Temporal entities, relationships | ✅ | ✅ | Discovered |
| Skyvern | `extensions/skyvern/` | Browser Automation | Visual tasks, navigation | ✅ | ✅ | Discovered |
| Crawl4AI | `extensions/crawl4ai/` | Web Crawling | Structured extraction | ✅ | ✅ | Discovered |
| Composio | `extensions/composio/` | Tool Orchestration | 100+ tool integrations | ✅ | ✅ | Discovered |
| n8n | `extensions/n8n/` | Workflow Automation | Visual workflows, triggers | ✅ | ✅ | Discovered |
| Kestra | `extensions/kestra/` | Data Orchestration | Declarative pipelines | ✅ | ✅ | Discovered |
| Langfuse | `extensions/langfuse/` | LLM Observability | Traces, evals, prompts | ✅ | ✅ | Discovered |
| Graphify | `extensions/graphify/` | Graph Visualization | Interactive graphs | ✅ | ✅ | Discovered |
| Skill Seekers | `extensions/skill_seekers/` | Skill Discovery | Agent skill matching | ✅ | ✅ | Discovered |
| Promptfoo | `extensions/promptfoo/` | Prompt Evaluation | Test suites, regression | ✅ | ✅ | Discovered |
| Nanobot | `extensions/nanobot/` | Micro-agents | Tiny specialized agents | ✅ | ✅ | Discovered |

**All 13:** Structured, discoverable, loadable via `ExtensionRegistry`. **Not integrated** into scheduler cycles.

---

## Database Models (`database/models.py`, `database/models_economic.py`)

| Model Group | Models | Purpose |
|-------------|--------|---------|
| **Core** | Target, Endpoint, Finding, Report, Hypothesis, Cycle | Bug bounty pipeline |
| **Economic** | Program, PayoutRecord, RevenueMetrics, TargetIntel | Revenue tracking |
| **Agents** | AgentTask, AgentCapability, AgentState | Agent orchestration |
| **Commands** | Command, CommandExecution, CommandPermission | Command system |
| **Events** | EventLog, EventSubscription | EventBus persistence |
| **Health** | HealthSnapshot, HealthCheck | Observability |
| **Secrets** | Secret, SecretVersion, IdentityVault | Credentials |
| **Extensions** | ExtensionManifest, ExtensionCapability | Extension registry |
| **Evolution** | EvolutionProposal, EvolutionVote, EvolutionExecution | Self-evolution |
| **Workflows** | Workflow, WorkflowExecution, WorkflowStep | Workflow engine |
| **Sync** | SyncSource, SyncRecord, SyncConflict | Synchronization |
| **Notifications** | Notification, NotificationConfig, NotificationDelivery | Smart notifications |
| **AI Security** | LLMScan, LLMPrompt, LLMSecurityFinding | AI/LLM security |

---

## API Router Summary (`api/routers/`)

| Router | Endpoints | Auth | Status |
|--------|-----------|------|--------|
| mission | 3 | None | ✅ |
| cycles | 8 | None | ✅ |
| security_cycle | 3 | None | 🟡 85% |
| forge_cycle | 3 | None | 🔴 Not created |
| pulse_cycle | 3 | None | 🔴 Not created |
| opportunity_score | 5 | None | ✅ |
| targets | 12 | None | ✅ |
| findings | 10 | None | ✅ |
| reports_quality | 6 | None | ✅ |
| reports_acceptance | 7 | None | ✅ |
| offensive | 8 | None | ✅ |
| orion | 4 | None | ✅ |
| copilot | 2 | None | ✅ |
| commands | 6 | Permission | ✅ |
| system_state | 3 | None | ✅ |
| notifications | 3 | None | ✅ |
| ai_security | 4 | None | 🟡 |
| evolution | 5 | None | 🔴 Stubs |
| settings_unified | 8 | None | ✅ |
| vault | 5 | Permission | ✅ |
| backup | 3 | None | ✅ |
| cateye | 4 | None | ✅ |
| **TOTAL** | **~120** | | |

---

## New Module Requirements (OMEGA Multi-Cycle)

| Module | Path | Purpose | Priority |
|--------|------|---------|----------|
| **Forge Cycle** | `core/cycles/forge.py` | Dev bounty cycle (Algora, Opire, Superteam, IssueHunt) | PHASE 2 |
| **Pulse Cycle** | `core/cycles/pulse.py` | AI work/microtask cycle (Outlier, DataAnnotation, Mindrift) | PHASE 3 |
| **Forge Router** | `api/routers/forge_cycle.py` | Forge cycle endpoints | PHASE 2 |
| **Pulse Router** | `api/routers/pulse_cycle.py` | Pulse cycle endpoints | PHASE 3 |
| **Multi-Cycle Orchestrator** | `core/cycles/orchestrator.py` | Cross-cycle resource allocation, unified queue | PHASE 4 |
| **Omega Agents** | `cores/agents/omega/` | 12 autonomous agents | PHASE 5 |
| **Sensors** | `core/sensors/` | Continuous observation per domain | PHASE 6 |
| **Self-Repair** | `core/self_repair/` | Auto-diagnose, repair, validate | PHASE 7 |
| **Learning System** | `core/learning/system.py` | Post-cycle evaluation, improvement | PHASE 7 |
| **Mobile API** | `api/routers/companion.py` | Android/Wear OS endpoints | PHASE 8 |
| **Activity API** | `api/routers/activity.py` | Real activity events for GamingConsole | IP01 |
| **Financial API** | `api/routers/financial.py` | Real economic data for dashboards | IP01 |