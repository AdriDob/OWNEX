# Roadmap — ORION Platform

> Priorizado por Expected Value Impact:
> Seguridad → Estabilidad → Learning → Quality → Intelligence → UX → Docs

## Completed (Verificado, Julio 2026)

### v3.0 — Base Hardening
- [x] Security Hardening (8 CVEs resueltos: HMAC, machine-id, tokens plano, CSRF, OAuth2, exception leak, CORS, audit log)
- [x] Persistencia: circuit breakers, reward learning, health snapshots
- [x] DedupTracker unificado con fingerprints normalizados
- [x] Scheduler adaptativo con priorización por reward learning
- [x] Rate limit por user-id + localStorage hardening
- [x] Release hardening (12 fixes: event-loop, WAL, tasks, indexes, ensure_future, cooldown, context managers, rotation)
- [x] Documentación consolidada + portable installer

### v3.1 — ORION Reasoning Layer
- [x] **Hypothesis Challenger**: AlternativeExplainer (7 tipos), ContradictionTestDesigner, MissingVerificationsAnalyzer
- [x] **Evidence Graph**: SQLite persistente, for/against/neutral, weight/confidence, edges, balance scoring
- [x] **Adaptive Report Gate**: Threshold dinámico por tipo de vulnerabilidad
- [x] **FeedbackLearner pipeline**: Pesos adaptativos del ConfidenceScorer
- [x] Unificar 3 sistemas de salud → HealthCenter (`core/health/`)
- [x] Health snapshots persistentes (últimos 100 in-memory)

### v4.0 — ORION Platform
- [x] Extension SDK (manifest, hooks, capabilities, settings, hot reload)
- [x] Secrets Manager (IdentityVault bridge, AES-256-GCM, env fallback)
- [x] AppRegistry bridge + discover_extensions()
- [x] Integration Center (23 built-in definitions, runtime status, API)
- [x] Documentation: CONFIGURATION_GUIDE, EXTENSION_SDK, CONNECTOR_GUIDE, ARCHITECTURE_DECISIONS

### v4.1 — Financial Layer
- [x] CoinGecko price feed (30+ cryptos, cache, free tier)
- [x] Takenos connector (balance, CSV import, Solana USDC sync)
- [x] Dashboard unificado: patrimonio, breakdown, objetivo 30K, ingresos
- [x] Integrations status endpoint (🟢🟡🔴)
- [x] Coinbase ATLAS fix (HMAC-SHA256)
- [x] Kraken ATLAS fix (private API + HMAC-SHA512)

### v4.2 — Automation + Intelligence
- [x] **Hermes Automation Agent** (6 comandos, JSONL, tests, Windows launcher)
- [x] **Senior Copilot Agent** (80 tests, Authority 5 niveles, Policy Engine, 4 Auditors, Recommender)
- [x] **Unified Memory** (23 tests, namespaces, tags, priority, embeddings-ready, auto-prune)
- [x] **Evolution Engine** (Observe→Analyze→Hypothesize→Experiment→Measure→Knowledge→Improve)
- [x] Pre-commit hooks (Ruff + pytest)
- [x] Scheduler pipeline E2E (DISCOVER→RECON→HYPOTHESIS→VALIDATE→REPORT + auto-report)

### v4.3 — Product Polish
- [x] **Design System**: Modal, Select, DataTable, Drawer, LoadingState, ErrorState
- [x] **Global Command Center**: CommandPalette con scopes (`>` `/` `@` `#` `$`), búsqueda paralela targets+findings+reports, 26 páginas dinámicas, 8 acciones
- [x] **UX Audit**: 47 páginas revisadas, 26 componentes auditados, roadmap de fixes

### v4.4 — Extreme Simplification
- [x] Plugin discovery unificado (`core/plugin/discovery.py`)
- [x] AppRegistry + ExtensionRegistry sin circular imports
- [x] Journal → EventStore persistencia
- [x] SecretsManager single Vault path

### v4.5 — Offensive Intelligence + Revenue (Current)
- [x] **Offensive Intelligence Engine**: 5 reasoners (IDOR, SSRF, XSS, SQLi, Auth Bypass), Planner, Curiosity Engine, Relationship Graph, ContradictionEngine, Triager, Templates, Publisher (101 tests)
- [x] **Evidence Engine**: PoC, requests, responses, curl, Python exploit, timeline, CVSS, CWE, CAPEC, OWASP, MITRE, report readiness score (37 tests)
- [x] **Revenue Pipeline**: Finding→Evidence→Report→Platform→Payout. 6 API endpoints, 6 events, 31 tests
- [x] **Report Quality Gate**: Acceptance optimizer, triager simulation
- [x] **Evolution Engine**: Adaptive learning loop (Observe→Analyze→Hypothesize→Experiment→Measure→Knowledge→Improve)
- [x] **Mission Control** API + frontend
- [x] **Event Foundation**: 40+ event types, Correlation ID propagation, Event Store (SQLite)
- [x] **Knowledge Graph**: SQLite persistente, node/edge engine, API, COPILOT integration
- [x] **Configuration Wizard v2**: 6 steps, persistent, API, 14 tests
- [x] **Integration Center**: 23 definitions, runtime status, 7 categories
- [x] **Workflows Engine**: Workflow definitions and execution
- [x] **Tools**: Amass, Naabu, Shodan, Uncover
- [x] **Integrations**: ARCA, Outlook, Discord
- [x] **Desktop**: Tauri (Rust+WebView), Linux setup script, Windows 33-tool installer
- [x] **UI**: HealthCenter, MobileCompanion, Workflows pages, Assistant/Companion composables, DataTable/Drawer/Modal/Select components

## 🔄 **Sprints v4.5.0 STABLE (Revenue Intelligence + Quick Wins)**

### 🚀 Revenue Intelligence ✅
- **EconomicMemory** - UnifiedMemory namespace "economic" for program-level tracking
- **USD/hour** - Dynamic metrics from payout history  
- **Platform Speed** - Real-time estimation from actual data
- **TargetPrioritizer** - EV-based ranking with economic signals
- **RevenuePipeline** - Complete journey: Finding→Evidence→Report→Platform→Payout
- **70 tests** - All passing, Ruff clean

### 📊 **Expansion Quick Wins** ✅
- **TargetPrioritizer** - 22 tests, EV engine + RevenueMetrics integration
- **RevenuePipeline** - 31 tests, 6 API endpoints, 6 events
- **IntegrationCenter** - 23 definitions, runtime status checks
- **Hermes v2 Events** - 48 tests, 7 event types
- **Command System v1** - 107 commands, 45 tests
- **ReportAcceptanceOptimizer** - 32 tests

## ✅ **Completed Features (v5.0)**

- **Frontend Consolidation Fase 1**: Capital Dashboard Unificado (5→1 páginas)
- **Frontend Consolidation Fase 2**: Router 50→8 secciones + Sidebar unificado
- **Frontend Consolidation Fase 2b**: Mission Control actualizado con nuevas rutas

## 🔄 **Next Evolution (v5.0)**

1. **Baby Mode (HUNT Button)** ✅ Current
2. **Command Palette como Nav Principal**
3. **Auto-Submission Pipeline (S-6)**
4. **Design System Unificado**
5. **Target Intelligence Engine**

## 📋 **Pendientes (Post-v4.5.0)**

### **Sprints En Curso**
- **S-4** AI Bounty Auto-Hunter (29 tests)
- **S-5** Revenue Dashboard V2 (0 tests) 
- **UX-1** Baby Mode (0 tests)
- **S-6** Auto-Submission Pipeline (12 tests)
- **S-7** Target Discovery Automator (25 tests)
- **S-8** Report Optimizer V2 (23 tests)
- **S-9** Auto-Recon Enhancement (23 tests)
- **S-10** Verdict Auto-Learner (14 tests)

### **No to Do**
- **New reasoners** (CSRF, LFI, etc.) - More hypotheses without probes don't help
- **Dashboard polish** - No reports to display yet
- **Hermes desktop features** - Desktop execution needs pipeline
- **Docker** - Premature optimization
- **sentence-transformers** - Memory without revenue = data cemetery
- **Financial analytics** - No money to analyze yet
- **Memory Intelligence** - Valuable but requires outcomes to remember
- **ROI Engine** - Depends on Acceptance Intelligence + data

## 🚫 **Lo que NO hacer en el próximo sprint**

| Item | Why not |
|------|---------|
| New reasoners (CSRF, LFI...) | More hypotheses without probe don't help |
| Dashboard polish | No reports to display yet |
| Hermes desktop features | Desktop execution without pipeline = no value |
| Docker | Premature optimization |
| sentence-transformers | Memory without revenue = data cemetery |
| Financial analytics | No money to analyze yet |
| Memory Intelligence | Valuable but depends on having outcomes to remember |
| ROI Engine | Depends on Acceptance Intelligence + outcome data |

---
