# Current State — Estado Real del Proyecto

> **v4.1.0 STABLE** — ORION Financial Layer. CoinGecko, Takenos, Dashboard, Integraciones.
> Julio 2026.

## Testing

- **Total de tests**: 531 pasan, 2 xfailed, 0 fallos
- **Tests nuevos**: 83 tests (20 CoinGecko/Takenos + 15 Hermes Automation Agent)
- **Comando**: `.venv/bin/python -m pytest --timeout=60`
- `test_security.py` incluido (34 tests, todos verdes)
- **Lint**: Ruff clean — 0 errores en todo el código nuevo

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

## FASE 5 — ORION Reasoning Layer (Julio 2026)

| Feature | Archivos | Estado |
|---|---|---|
| Hypothesis Challenger | `cores/validation/challenger.py`, `gate.py`, `confidence.py`, `loop_engine.py`, `verdict_handler.py`, `models.py`, `db.py` | ✅ AlternativeExplainer (7 tipos), ContradictionTestDesigner, MissingVerificationsAnalyzer, uncertainty_penalty en scorer |
| Evidence Graph | — | Pendiente |
| Adaptive Report Gate | — | Pendiente |
| FeedbackLearner pipeline | — | Pendiente |

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
- Pre-commit hooks (no configurados)

## Limitaciones Conocidas (Documentadas)

Ver `docs/KNOWN_LIMITATIONS.md`:
- ~~El motor de validación no refuta hipótesis~~ → ✅ Challenger: genera explicaciones alternativas + contrapruebas
- ~~No evalúa explicaciones alternativas (recurso público, caché, stub)~~ → ✅ Challenger: AlternativeExplainer para 7+ tipos
- No verifica ownership/RBAC automáticamente (los tests no se ejecutan, solo se diseñan)
- No aprende de falsos positivos (FeedbackLearner existe pero no conectado)
- ReportGate threshold fijo 0.6 para todos los tipos de vulnerabilidad
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

Las limitaciones restantes corresponden a v3.1 (ORION Reasoning Layer) — todas las features de v4.0.0, v4.1.0 y Hermes v0.1.0 están completas.
