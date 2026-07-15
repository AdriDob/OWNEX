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

## Current Sprint — Consolidation & Security (v4.5.0 STABLE)

### Revenue Cycle Completion
- [x] Revenue Pipeline orchestrator (6 methods, 6 API endpoints, 31 tests)
- [x] Revenue event types (report_submitted, submission_failed, status_changed, sync_completed, sync_failed, payout_recorded)
- [x] Revenue capabilities registered in CapabilityRegistry

### Platform Hardening
- [x] COMPLETED_FEATURES.json — system of truth restored
- [x] Git working tree stabilized
- [ ] Documentation redesign (/docs)
- [ ] Hermes events: hermes:action_started, hermes:action_completed, hermes:action_failed
- [ ] ContradictionEngine: SSRF/XSS/SQLi/AuthBypass completion

## Next Evolution (v5.0 — ORION Evolution Program)

> Basado en `.ai/ORION_EVOLUTION_PROGRAM.md`

| Pilar | Prioridad | Dependencias |
|---|---|---|
| **1. Target Intelligence Engine** | Alta | Evolution Engine, Unified Memory |
| **2. Elite Research Mode** | Alta | Challenger, Evidence Graph |
| **3. Learning Engine** | Alta | FeedbackTuner, Knowledge Assets |
| **4. Quality Intelligence** | Media | Gate, Copilot Review |
| **5. Copilot Strategic Layer** | Media | Copilot, Evolution Engine |
| **6. Evolution Engine** | Media | Ya existe loop, falta automatización |
| **7. Statistical Command Center** | Alta | Mission Control 2.0, Activity Center |
| **8. Human Time Optimization** | Media | Hermes, auto-report |
| **9. External Intelligence Layer** | Baja | Integration Center, Unified Memory |
| **10. Reliability** | Always | Checks pre-commit |

## Definition of Done

Una funcionalidad se considera completa cuando:
1. Código implementado y funcionando en runtime real
2. Tests existentes y pasando
3. Integración verificada con módulos dependientes
4. Sin vulnerabilidades de seguridad conocidas
5. Produce output observable (UI / API / DB)
6. Sobrevive restart del backend
7. Estado registrado en COMPLETED_FEATURES.json
