# Current State — Estado Real del Proyecto

> **v4.5.0 STABLE** — Offensive Intelligence + Evidence Engine + Quality Gate + Evolution.
> Julio 2026.

## Testing

- **Total de tests**: 1401 pasan, 2 pre-existing, 2 xfailed, 0 fallos nuevos
- **Tests nuevos (sesión actual)**: 157 (offensive + evidence + quality + revenue + evolution + hermes v2)
- **Comando**: `.venv/bin/python -m pytest --timeout=60`
- `test_security.py` incluido (34 tests, todos verdes)
- **Lint**: Ruff clean — 0 errores en todo el código nuevo
- **Pre-commit**: Ruff + pytest hooks activos en cada commit

## FASE 1 — Base estabilizada (Julio 2026)

| Issue | Estado | Archivos |
|---|---|---|
| Evidence upload 404 (POST /api/evidence/upload) | ✅ Creado | `api/routers/evidence.py` |
| Target scan 404 (POST /api/targets/{id}/scan) | ✅ Creado | `api/routers/targets.py` |
| PWA assets faltantes | ✅ Creados | `frontend/public/manifest.json`, `icon-*.png`, `index.html`, `main.ts` |
| 32 bare `except Exception: pass` | ✅ Logeados | 15 archivos modificados |
| API keys hardcodeadas | ✅ Env vars | `cores/ai/orion_agent.py` |
| 14 empty `__init__.py` | ✅ Normal práctica | No requiere acción |
| `--color-info` undefined | ✅ No existe | False alarm del audit |
| Duplicate routes | ✅ No existen | False alarm del audit |

## FASE 2 — Módulos conectados (Julio 2026)

| Conexión | Estado | Archivos |
|---|---|---|
| OpportunityEngine → EventBus | ✅ `opportunity:found` / `opportunity:updated` publicados | `cores/opportunity/engine.py` |
| Scheduler + ORION SCORE | ✅ Scheduler usa Program.orion_score como multiplier | `api/scheduler.py` |
| Scheduler → EventBus | ✅ `report:generated`, `discovery:completed` publicados | `api/scheduler.py` |
| Findings → EventBus | ✅ `finding:created`, `finding:status_changed` publicados | `api/routers/findings.py` |
| AgentBus → EventBus | ✅ Bridge creado, todos los eventos forwardeados | `cores/agents/bus.py`, `api/main.py` |
| Ghost events (8 tipos) | ✅ Todos tienen publisher real | Múltiples archivos |

## FASE 3 — Pipeline E2E funcional (Julio 2026)

| Stage scheduler | Antes | Después |
|---|---|---|
| DISCOVER | ✅ Scrapea + crea targets | ✅ + publica `opportunity:found` |
| RECON | ✅ Escanea targets | ✅ + usa ORION next_action para priorizar |
| HYPOTHESIS | ❌ Import roto (`scan_service.generate_hypotheses`) | ✅ FIXED: `cores.engine.hypothesis.generators.generate_hypotheses` |
| VALIDATE | ❌ Import roto (`ValidationReplayer`) | ✅ FIXED: `ValidationLoopEngine.evaluate()` |
| REPORT | ❌ Import roto (`ReportService` class no existe) | ✅ FIXED: `create_report_from_findings()` |
| Auto-report | ❌ No existía | ✅ EventBus subscriber: finding confirmed → report draft |

## FASE 4 — Automatización ORION (Julio 2026)

| Feature | Estado | Detalle |
|---|---|---|
| Auto-priorización | ✅ | Scheduler consulta `ORION.get_next_action()` |
| Auto-explicación | ✅ | Scheduler logea `[ORION] Auto-prioritized X (priority=Y, why=Z)` |
| Auto-descubrimiento | ✅ | DISCOVER publica eventos con nuevos targets |
| EVH scoring | ✅ | Ya existe en `cores/orion/next_action.py` |
| Aprendizaje | ✅ | `RewardLearner.analyze()` + ajustes por tipo de vulnerabilidad |

## Funcionalidades Verificadas como Estables

| Funcionalidad | Archivos | Estado |
|---|---|---|
| Auth (TokenService + SessionStore) | `cores/auth/` | ✅ Estable |
| License Validator + Store | `cores/license/` | ✅ Production Ready |
| IdentityVault | `cores/identity_vault.py` | ✅ Estable |
| CSRF Middleware | `api/middleware/csrf_middleware.py` | ✅ Production Ready |
| Security Headers | `api/middleware/error_handling.py` | ✅ Production Ready |
| Audit Log | `cores/audit_log.py` | ✅ Estable |
| Ledger → SQLite | `cores/ledger/`, `database/models.py` | ✅ Persistente |
| Event Bus → SQLite | `cores/events/event_bus.py` | ✅ Persistente |
| System State → SQLite | `cores/system_state.py` | ✅ Persistente |
| Notification Dedup → SQLite | `cores/notifications/hub.py` | ✅ Persistente |
| Evidence Upload API | `api/routers/evidence.py` | ✅ Nueva |
| Target Scan Trigger | `api/routers/targets.py` | ✅ Nueva |
| PWA Assets | `frontend/public/` | ✅ Nuevos |
| Scheduler Pipeline | `api/scheduler.py` | ✅ FIXED (3 stages) |
| ORION → Scheduler | `api/scheduler.py` | ✅ Conectado |
| EventBus Ghost Events | Múltiples | ✅ Publicados |
| AgentBus → EventBus | `cores/agents/bus.py` | ✅ Bridge |
| Auto-report | `api/main.py` | ✅ Nuevo subscriber |
| except:pass → log | 15 archivos | ✅ Fixeado |
| Senior Copilot Agent | `core/copilot/` | ✅ Subsystem completo: authority, policy, context, planner, explain, analyzer, review, auditors, EventBus integration |

## FASE 5 — ORION Reasoning Layer (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| Hypothesis Challenger | `cores/validation/challenger.py`, `gate.py`, `confidence.py`, `loop_engine.py`, `verdict_handler.py`, `models.py`, `db.py` | ✅ AlternativeExplainer (7 tipos), ContradictionTestDesigner, MissingVerificationsAnalyzer, uncertainty_penalty en scorer |
| Evidence Graph | `core/evidence_graph/` | ✅ SQLite persistente, for/against/neutral, weight/confidence, edges, balance scoring, integrado con Copilot + EventBus |
| Adaptive Report Gate | — | Pendiente |
| FeedbackLearner pipeline | `core/validation/`, `api/main.py` | ✅ FeedbackTuner accumulates + applies weight adjustments (12 tests) |

## FASE 6 — Release hardening audit y fixes (Julio 2026)

| Fix | Archivos | Estado |
|---|---|---|
| FinancialSyncScheduler event-loop block | `cores/financial/scheduler.py` | ✅ `sync_all` → `asyncio.to_thread` |
| NotificationPoller no detenible | `api/routers/operations.py`, `api/main.py` | ✅ Stop flag + shutdown hook |
| Watchdog chequea bus equivocado | `desktop/watchdog.py` | ✅ `get_agent_bus()` → `get_event_bus()` |
| research.py imports rotos | `cores/agents/research.py` | ✅ Clases runner instanciadas correctamente |
| 14 índices DB faltantes | `database/db.py`, `database/models.py` | ✅ Migración CREATE INDEX |
| create_task orphans (3) | `api/main.py`, `api/routers/hunt.py` | ✅ Trackeados + done_callbacks |
| WAL checkpoint ausente | `database/db.py`, `api/scheduler.py` | ✅ PRAGMA wal_checkpoint(TRUNCATE) |
| CorrelationEngine dedup leak | `cores/engine/correlation.py` | ✅ MAX_DEDUP_CACHE=10K |
| ensure_future sin tracking | `cores/agents/base.py`, `cores/agents/bus.py` | ✅ Error logging en done_callbacks |
| _target_cooldowns sin poda | `api/scheduler.py` | ✅ Purga cíclica de stale entries |
| open() sin context manager | `cores/auth/session.py`, `cores/auth/token_service.py` | ✅ with open() |
| audit.jsonl sin rotación | `cores/audit_log.py` | ✅ Rotación cada 10MB (3 backups) |

## Próximos Pasos (no implementados)

- Frontend tests (no existen actualmente)

## Limitaciones Conocidas (Documentadas)

Ver `docs/KNOWN_LIMITATIONS.md`:
- ~~El motor de validación no refuta hipótesis~~ → ✅ Challenger: genera explicaciones alternativas + contrapruebas
- ~~No evalúa explicaciones alternativas (recurso público, caché, stub)~~ → ✅ Challenger: AlternativeExplainer para 7+ tipos
- No verifica ownership/RBAC automáticamente (los tests no se ejecutan, solo se diseñan)
- ~~No aprende de falsos positivos~~ → ✅ FeedbackTuner conectado (pesos se ajustan con feedback humano)
- ~~ReportGate threshold fijo 0.6~~ → ✅ Threshold adaptativo por tipo de vulnerabilidad
- El ContradictionTestDesigner diseña tests pero no los ejecuta (pendiente para v3.2)

## FASE 7 — ORION Platform v4.0.0 (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| Extension SDK | `core/extension/` | ✅ Manifest, hooks (before/after), capabilities, declarative settings, hot reload, failure isolation |
| Secrets Manager | `core/secrets/manager.py` | ✅ IdentityVault bridge (AES-256-GCM), env fallback, cache, REST API |
| Health Center | `core/health/engine.py`, `checks.py` | ✅ Unifica 3 sistemas legacy, green/yellow/red status, snapshots, checks por categoría, persistence via SystemState, unified summary endpoint |
| AppRegistry bridge | `core/app_registry.py` | ✅ discover_extensions() bridges to ExtensionRegistry |
| API Endpoints | `core/api/routers.py` | ✅ /extensions, /secrets, /health endpoints under /api/core |
| Documentation | `CONFIGURATION_GUIDE.md`, `EXTENSION_SDK.md`, `CONNECTOR_GUIDE.md`, `ARCHITECTURE_DECISIONS.md` | ✅ 4 complete guides |
| Example Extension | `extensions/hello/` | ✅ Minimal working example |

## FASE 8 — ORION Financial Layer (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| CoinGecko price feed | `cores/crypto/coingecko.py` | ✅ 30+ crypto prices, 24h change, cache, free tier |
| Takenos connector | `cores/financial/takenos/` | ✅ Balance manual, CSV import, Solana USDC sync |
| Dashboard unificado | `cores/financial/dashboard.py` | ✅ Patrimonio total, breakdown, objetivo libertad 30K, ingresos del mes, alertas |
| Integrations status | `api/routers/financial_truth.py` | ✅ /api/financial/integrations/status con 🟢🟡🔴 |
| Dashboard endpoint | `api/routers/financial_truth.py` | ✅ GET /api/financial/dashboard |
| Fix Coinbase (HMAC) | `apps/atlas/connectors/coinbase/` | ✅ CB-ACCESS-SIGN HMAC-SHA256 |
| Fix Kraken (portfolio) | `apps/atlas/connectors/kraken/` | ✅ Balance + ticker vía API privada con HMAC-SHA512 |

## FASE 9 — Hermes Automation Agent v1 (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| Manifest + AppRegistry | `apps/hermes/manifest.py` | ✅ Registrado como app "hermes" con scheduler job |
| Automation Engine | `apps/hermes/engine.py` | ✅ Safe mode, 6 comandos (backup/status/health/logs/doctor/help) |
| CLI via run.py | `run.py` | ✅ `python run.py --hermes <command>` |
| Action logging | `apps/hermes/engine.py` | ✅ JSONL persistente en `~/.orion/hermes_actions.jsonl` |
| Tests | `tests/test_hermes.py` | ✅ 15 tests, todos pasan |
| User Guide | `docs/HERMES_GUIDE.md` | ✅ Documentación completa con ejemplos |
| Windows shortcut | `scripts/hermes_shortcut.bat`, `scripts/hermes_silent.vbs` | ✅ Launcher para WSL |

Las limitaciones restantes corresponden a v3.1 (ORION Reasoning Layer) — todas las features de v4.0.0, v4.1.0, Hermes v0.1.0 y Senior Copilot Agent están completas.

## FASE 10 — Senior Copilot Agent (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| Authority Levels (5) | `core/copilot/permissions.py` | ✅ Observer, Assistant, Operator, Senior Hunter, Administrator |
| Decision Confidence (4 bandas) | `core/copilot/permissions.py` | ✅ no_action, request_approval, safe_execute, auto_close |
| Policy Engine (6 reglas) | `core/copilot/permissions.py` | ✅ Centralized safety rules, add/remove at runtime |
| Context Builder | `core/copilot/context.py` | ✅ Aggregates finding, evidence, verdict, confidence, memory |
| Explanation Engine | `core/copilot/explain.py` | ✅ Verdict, confidence, action, changes, alternatives |
| Planner (6 tipos vuln) | `core/copilot/planner.py` | ✅ IDOR, SSRF, XSS, SQLi, Auth Bypass, Generic |
| Finding Analyzer | `core/copilot/analyzer.py` | ✅ Evidence quality, inconsistencies, alternatives, confidence |
| Auditors (4 tipos) | `core/copilot/auditor.py` | ✅ Health, Configuration, Security, Architecture |
| Pre-Report Review (9 items) | `core/copilot/review.py` | ✅ Evidence, reproducibility, CVSS, CWE, impact, remediation |
| Recommender | `core/copilot/recommender.py` | ✅ Context-aware next-step suggestions |
| EventBus integration | `api/main.py` | ✅ finding:created + finding:status_changed subscribers |
| Tests | `tests/test_copilot_agent.py` | ✅ 80 tests, todos pasan |
| Architecture document | `.ai/COPILOT_ARCHITECTURE.md` | ✅ Responsabilities, boundaries, lifecycle, integration points |
| Unified Memory integration | `core/memory/`, `core/copilot/agent.py` | ✅ Namespaces, search, tags, priority, expiration, embeddings-ready |

## FASE 11 — Unified Memory (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| SQLAlchemy model | `core/memory/models.py` | ✅ MemoryEntry with namespace, content, tags, priority, embedding, expiration |
| CRUD operations | `core/memory/store.py` | ✅ store, get, delete, query, count |
| Namespace isolation | `core/memory/store.py` | ✅ Filtrable por namespace (global, cateye, atlas, odyssey, hermes, copilot) |
| Text search | `core/memory/store.py` | ✅ Búsqueda en content + key via ilike |
| Tag filtering | `core/memory/store.py` | ✅ Filtro por tags combinados |
| Priority sorting | `core/memory/store.py` | ✅ Priority desc + created_at desc |
| Optional expiration | `core/memory/store.py` | ✅ expires_at + auto-prune |
| Embedding storage | `core/memory/store.py` | ✅ store_embedding, get_without_embeddings |
| EventBus initialization | `api/main.py` | ✅ Boot init con stats |
| Copilot integration | `core/copilot/agent.py` | ✅ remember(), recall(), remember_analysis() |
| Tests | `tests/test_unified_memory.py` | ✅ 23 tests, todos pasan |

## FASE 13 — Event Foundation + Knowledge Graph (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| Events class (40+ constants) | `core/events/types.py` | ✅ EventEnvelope, Decision, CorrelationId |
| Correlation ID propagation | `core/events/correlation.py` | ✅ contextvar-based, with_correlation_id(), with_new_correlation_id() |
| Event Store (SQLite) | `core/events/store.py` | ✅ Persist, replay by time/cid/type, search, stats, prune, singleton |
| Capability Registry | `core/capabilities/registry.py` | ✅ register, find, list, has, unregister, clear, singleton |
| CopilotEventPublisher | `core/copilot/publisher.py` | ✅ 7 event types, decouples COPILOT from EventBus |
| COPILOT Decision Engine | `core/copilot/agent.py` | ✅ make_decision() with priority/reason/confidence/actions/eta/roi |
| COPILOT publishes events | `core/copilot/agent.py` | ✅ 5 methods → publisher.analysis_completed() et al |
| ARCA publishes events | `cores/integrations/arca/connector.py` | ✅ arca:cuit:validated, arca:invoice:created |
| Outlook publishes events | `cores/integrations/outlook/connector.py` | ✅ notification:sent, outlook:email:sent |
| Legacy ↔ CoreEventBus bridge | `api/main.py` | ✅ Bidirectional wildcard bridge |
| Knowledge Graph models | `core/knowledge/models.py` | ✅ KGNode, KGEdge, NodeTypes, EdgeTypes |
| Knowledge Graph engine | `core/knowledge/graph.py` | ✅ add_node/edge, get_neighbors, get_path, get_subgraph, stats, record_finding/report/decision |
| COPILOT → KG integration | `core/copilot/agent.py` | ✅ _knowledge_context() enriches decisions, record_decision() in make_decision(), record_finding/report in analyze/pre_report_review |
| KG API endpoints | `core/api/routers.py` | ✅ GET/POST/DELETE nodes, GET neighbors/path/subgraph/stats |
| KG Event bridge | `api/main.py` | ✅ finding:* and target:* auto-recorded to KG |
| Tests (event foundation) | `tests/test_event_foundation.py` | ✅ 32 tests |
| Tests (Knowledge Graph) | `tests/test_knowledge_graph.py` | ✅ 34 tests |
| Tests (KG API) | `tests/test_core_api_routers.py` | ✅ 9 tests |

## FASE 12 — Integration Center (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| Built-in integration definitions (23) | `core/integrations/discovery.py` | ✅ 7 categorías: platform, ai, exchange, blockchain, financial, messaging, infrastructure |
| IntegrationRegistry | `core/integrations/registry.py` | ✅ Runtime status checks (env vars, vault, custom health callables) |
| Singleton + init | `core/integrations/registry.py` | ✅ get_integration_registry(), init_integration_registry() |
| API: GET /integrations | `core/api/routers.py` | ✅ Summary with totals by status + category |
| API: GET /integrations/{name} | `core/api/routers.py` | ✅ Single integration with status, category, tags, checked_at |
| API: POST /integrations/{name}/test | `core/api/routers.py` | ✅ Test connection for a specific integration |
| Tests | `tests/test_core_api_routers.py` | ✅ 6 new tests (list, categories, known, unknown, test, test_unknown) |

## FASE 14 — EP-5 Execution Runtime (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| RuntimeContext + VirtualClock | `core/execution/runtime/context.py`, `clock.py` | ✅ Thread-safe context, deterministic clock, real/simulation modes |
| State Machine (12 node + 11 workflow states) | `core/execution/runtime/state_machine.py` | ✅ Validated transitions with TransitionError |
| ExecutionJournal | `core/execution/runtime/journal.py` | ✅ Per-execution log, replay, to_dict |
| ExecutionEventPublisher (26 types) | `core/execution/runtime/publisher.py` | ✅ Never calls EventBus directly, optional bind callback |
| ExecutionKernel | `core/execution/runtime/kernel.py` | ✅ Tiny orchestrator: context lifecycle, state, journal, variables |
| CapabilityDispatcher | `core/execution/runtime/dispatcher.py` | ✅ Permission→Secrets→RateLimit→Metrics→Execute pipeline |
| WorkerEngine (17 bytecode instructions) | `core/execution/runtime/worker.py` | ✅ NOP through PERSIST, full state tracking |
| CheckpointManager | `core/execution/runtime/checkpoint.py` | ✅ Snapshot save/restore every N nodes |
| RetryEngine (6 policies) | `core/execution/runtime/retry.py` | ✅ Immediate, Linear, Exponential, Jitter, Circuit Breaker, Manual |
| TimeoutEngine (4 types) | `core/execution/runtime/timeout.py` | ✅ Node, workflow, approval, resource timeouts via VirtualClock |
| RollbackEngine | `core/execution/runtime/rollback.py` | ✅ Checkpoint-based rollback with verification |
| Scheduler | `core/execution/runtime/scheduler.py` | ✅ Priority queue, dependency resolution, worker assignment |
| MetricsEngine (13 types) | `core/execution/runtime/metrics.py` | ✅ CPU, RAM, Tokens, $, API calls, bandwidth, cache, retries |
| ResourceManager | `core/execution/runtime/resource.py` | ✅ Named resources, acquire/release, concurrency, rate limiting |
| ApprovalManager | `core/execution/runtime/approval.py` | ✅ Request→Notify→Approve\|Reject\|Expire lifecycle |
| RuntimeAPI | `core/execution/runtime/api.py` | ✅ start/pause/resume/cancel + status/metrics/journal |
| Simulation Mode | `core/execution/runtime/simulation.py` | ✅ Fake capabilities, SimulationReport, deterministic clock |
| EventBus Bridge | `core/execution/runtime/integration.py` | ✅ Two-way bridge: execution→EventBus + EventBus→execution |
| KG Bridge | `core/execution/runtime/kg_bridge.py` | ✅ Execution→Knowledge Graph recording |
| COPILOT Execution Observer | `core/execution/runtime/observer.py` | ✅ COPILOT memory learning from execution outcomes |
| Tests | `tests/test_execution_runtime.py` | ✅ 111 tests, todos pasan, Ruff clean |

## FASE 15 — Configuration Wizard v2 (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| WizardStepDef + WizardState models | `core/setup/models.py` | ✅ Step registry with metadata, persistence, config output |
| Step registry + @define_step decorator | `core/setup/steps/__init__.py` | ✅ Extensible: new steps via decorator, no engine changes |
| Identity step | `core/setup/steps/identity_step.py` | ✅ Username, email, role selection |
| System step | `core/setup/steps/system_step.py` | ✅ Python, Node, Ollama, disk, permissions checks |
| COPILOT step | `core/setup/steps/copilot_step.py` | ✅ Authority level, auto-execute, LLM provider/model |
| Integrations step | `core/setup/steps/integrations_step.py` | ✅ Registry discovery, connected/disconnected status |
| Smartwatch step | `core/setup/steps/smartwatch_step.py` | ✅ Wear OS enable/disable, notification preferences |
| Test step | `core/setup/steps/test_step.py` | ✅ EventBus, DB, vault, COPILOT, scheduler verification |
| Wizard engine refactored | `core/setup/wizard.py` | ✅ go_back, skip_step, reset_wizard, state persistence |
| API endpoints | `core/api/routers.py` | ✅ Wizard CRUD + go-back/skip/reset/steps/list |
| Tests | `tests/test_setup.py` | ✅ 14 tests, todos pasan, Ruff clean |

## FASE 17 — Revenue Pipeline (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| RevenuePipeline orchestrator | `core/revenue/pipeline.py` | ✅ `submit_report()`, `check_submission_status()`, `sync_platform_payouts()`, `record_payout()`, `revenue_summary()`, `list_submissions()` |
| Revenue models | `database/models_economic.py` | ✅ PayoutRecord + RevenueEvent con FK a submission_records |
| Revenue events | `core/events/types.py` | ✅ 6 eventos: report_submitted, submission_failed, status_changed, sync_completed, sync_failed, payout_recorded |
| Revenue capabilities | `core/revenue/pipeline.py` | ✅ 5 capabilities registradas en CapabilityRegistry |
| API endpoints | `api/routers/revenue.py` | ✅ 6 endpoints bajo `/api/revenue/` |
| Router registration | `api/main.py` | ✅ Router registrado con tags ["revenue"] |
| Tests | `tests/test_revenue_pipeline.py` | ✅ 31 tests, todos pasan, Ruff clean |

## FASE 16 — Extreme Simplification (Julio 2026)

| Cambio | Archivos | Estado |
|---|---|---|
| Shared plugin discovery | `core/plugin/discovery.py` | ✅ `discover_manifests()` unifica el scanning/loading de apps y extensions |
| AppRegistry simplificado | `core/app_registry.py` | ✅ Sin bridge a ExtensionRegistry. Sin circular import. 75 líneas menos. |
| ExtensionRegistry simplificado | `core/extension/registry.py` | ✅ Sin dependencia de AppRegistry. `_check_dependencies()` via CapabilityRegistry. |
| Journal → EventStore persistencia | `core/events/types.py`, `core/execution/runtime/publisher.py`, `core/execution/runtime/worker.py`, `core/execution/runtime/api.py`, `core/events/store.py` | ✅ `execution:journal:entry` publicado al EventBus → EventStore. `RuntimeAPI.get_journal()` fallback a EventStore tras restart. |
| SecretsManager single path | `core/secrets/manager.py` | ✅ Vault-only path. `get_with_env_fallback()` transitional. `import_env_vars()` setup migration. |
| SecretsManager tests | `tests/test_core_secrets.py` | ✅ 11 tests (nuevo: test_get_no_env_bypass, test_get_with_env_fallback, test_import_env_vars) |
| Tests: AppRegistry | `tests/test_orion_core.py` | ✅ 28 tests pasan |
| Tests: ExtensionRegistry | `tests/test_core_extension.py` | ✅ 14 tests pasan |
| Tests: Event Foundation | `tests/test_event_foundation.py` | ✅ 32 tests pasan |
| Tests: Execution Runtime | `tests/test_execution_runtime.py` | ✅ 111 tests pasan |

## FASE 18 — Offensive Intelligence + Evidence + Quality (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| Offensive Intelligence Engine | `core/offensive/` | ✅ 5 reasoners (IDOR, SSRF, XSS, SQLi, Auth Bypass), Planner, Curiosity Engine, Relationship Graph, ContradictionEngine, Triager, Templates, Publisher |
| Offensive Intelligence API | `api/routers/offensive.py` | ✅ 8 endpoints |
| Evidence Composer | `core/evidence/composer.py` | ✅ PoC, requests, responses, curl, Python exploit, timeline, CVSS, CWE, CAPEC, OWASP, MITRE, report readiness score |
| Report Quality Gate | `api/routers/reports_quality.py` | ✅ Acceptance optimizer, triager simulation |
| Evolution Engine | `core/evolution/`, `api/routers/evolution.py` | ✅ Adaptive learning, analyze engine |
| Mission Control | `api/routers/mission.py`, `frontend/src/pages/MissionControl.vue` | ✅ API + frontend |
| Copilot API Router | `api/routers/copilot.py` | ✅ COPILOT API endpoints |
| Workflows Engine | `core/workflows/` | ✅ Workflow definitions and execution |
| Aegis App | `apps/aegis/`, `frontend/src/apps/aegis/` | ✅ Security app module |
| Sync Engine | `core/sync/` | ✅ Data synchronization |
| Finance Core | `core/finance/` | ✅ Models, engine |
| Reports Core | `core/reports/` | ✅ Report generation module |
| Documentation Platform | `core/documentation/` | ✅ Auto-generation, 18 modules registered |
| Tool: Amass | `cores/tools/amass.py` | ✅ External attack surface mapping |
| Tool: Naabu | `cores/tools/naabu.py` | ✅ Port scanning |
| Tool: Shodan | `cores/tools/shodan.py` | ✅ Shodan REST API intelligence |
| Tool: Uncover | `cores/tools/uncover.py` | ✅ Infrastructure discovery |
| Discord Notifications | `cores/notifications/discord.py` | ✅ Discord webhook bridge |
| ARCA Integration | `cores/integrations/arca/` | ✅ ARCA invoice/cuit validation |
| Outlook Integration | `cores/integrations/outlook/` | ✅ Email sending via Outlook |
| Tauri Desktop | `src-tauri/` | ✅ Rust+WebView desktop app |
| Linux Setup Script | `scripts/setup.sh` | ✅ Automated Linux dev setup |
| Windows Tools Installer | `scripts/install_desktop_tools.ps1` | ✅ 33 tools via winget |
| Unified Settings API | `api/routers/settings_unified.py` | ✅ Unified configuration endpoints |
| UI: DataTable, Drawer, Modal, Select | `frontend/src/components/ui/` | ✅ 4 reusable UI components |
| Assistant Composable | `frontend/src/composables/useAssistant.ts` | ✅ Chat assistant state management |
| Companion Composable | `frontend/src/composables/useCompanion.ts` | ✅ Mobile companion state |
| Health Center Page | `frontend/src/pages/HealthCenter.vue` | ✅ System health visualization |
| Mobile Companion Page | `frontend/src/pages/MobileCompanion.vue` | ✅ Companion UI for mobile |
| Workflows Page | `frontend/src/pages/Workflows.vue` | ✅ Workflow management UI |
| Tests: Offensive | `tests/test_offensive.py` | ✅ 101 tests |
| Tests: Evidence | `tests/test_evidence_composer.py` | ✅ 37 tests |
| Tests: Quality Gate | `tests/test_quality_gate.py` | ✅ New |
| Tests: Evolution Engine | `tests/test_evolution_engine.py`, `tests/test_evolution_analyze.py` | ✅ New |
| Tests: Execution Platform | `tests/test_execution_platform.py`, `tests/test_execution_compiler.py` | ✅ New |
| Tests: Deep Study | `tests/test_deep_study.py` | ✅ New |
| Tests: Copilot Everywhere | `tests/test_copilot_everywhere.py` | ✅ New |
| Tests: ARCA+Outlook | `tests/test_arca_connector.py`, `tests/test_outlook_connector.py` | ✅ New |
| Tests: Amass+Naabu+Shodan+Uncover | `tests/test_amass.py`, `tests/test_naabu.py`, `tests/test_shodan_uncover.py` | ✅ New |
| Tests: Chaos Workflows | `tests/test_chaos_workflows.py` | ✅ New |

## FASE 19 — Hermes v2: Professional Desktop Agent (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| Hermes EventBus events (7 types) | `core/events/types.py` | ✅ hermes:action:requested, hermes:action:approved, hermes:action:started, hermes:action:completed, hermes:action:failed, hermes:permission:required, hermes:security:blocked |
| HermesEventPublisher | `apps/hermes/publisher.py` | ✅ Silent-safe publisher, no-ops without EventBus, 7 publish methods |
| Permission System | `apps/hermes/permissions.py` | ✅ Risk levels (none/low/medium/high/critical), command risk registry, evaluate_action(), needs_confirmation(), ActionHistory with JSONL persistence |
| Security Layer | `apps/hermes/security.py` | ✅ PowerShell sanitization (13 injection patterns), file path validation (6 blocked paths), shell command validation (12 blocked commands), PID protection (PID 1, system PIDs) |
| Engine integration | `apps/hermes/engine.py` | ✅ Permission evaluation before execution, security validation pipeline, EventBus publishing for every lifecycle event, action history tracking |
| Tests: Events | `tests/test_hermes_events.py` | ✅ 10 tests (publisher noop, all 7 event types, event constants, ALL set registration) |
| Tests: Permissions | `tests/test_hermes_permissions.py` | ✅ 14 tests (risk levels, command risk, confirmation logic, evaluate_action, history) |
| Tests: Security | `tests/test_hermes_security.py` | ✅ 24 tests (PS sanitization, file paths, shell commands, PID validation, multi-violation) |
| Existing Hermes tests | `tests/test_hermes.py` | ✅ 15 tests, all pass (no regressions) |
| Manifest | `apps/hermes/manifest.py` | ✅ v0.3.0 |
