# Current State — Estado Real del Proyecto

> **v4.3.2 STABLE** — Senior Copilot Agent + Evidence Graph + Unified Memory + Integration Center + Pre-commit hooks.
> Julio 2026.

## Testing

- **Total de tests**: 663 pasan, 2 xfailed, 0 fallos
- **Tests nuevos**: 80 (Copilot) + 28 (Evidence Graph) + 23 (Unified Memory) + 6 (Integration Center)
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
| Health Center | `core/health/engine.py`, `checks.py` | ✅ Unifica 3 sistemas legacy, green/yellow/red status, snapshots, checks por categoría |
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
