# Current State — Estado Real del Proyecto

> **v3.0.0 STABLE** — Release final. Lista para uso diario en bug bounty.
> Julio 2026.

## Testing

- **Total de tests**: 393 pasan, 2 xfailed, 0 fallos
- **Comando**: `.venv/bin/python -m pytest --timeout=60`
- `test_security.py` ahora incluido (34 tests, todos verdes — antes excluido con 3 fallos)
- **Lint**: Ruff configurado, limpio (solo 1 pre-existing style suggestion no crítica)

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

## FASE 5 — Release hardening audit y fixes (Julio 2026)

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

- Health snapshots persistence (deuda conocida)
- Unificar sistemas de salud (deuda conocida)
- Frontend tests (no existen actualmente)
- Pre-commit hooks (no configurados)
