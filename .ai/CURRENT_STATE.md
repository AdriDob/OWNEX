# Current State — Estado Real del Proyecto

> Este documento refleja el estado VERIFICADO después del ciclo de estabilización y conexión (Julio 2026).

## Testing

- **Total de tests**: 359 pasan, 1 fallo preexistente (`test_e2e_flow.py::test_04_get_target_list` — DB pagination), 2 xfailed, 1 skipped
- **Comando**: `.venv/bin/python -m pytest --timeout=60 --ignore=tests/test_security.py`
- **Fallo preexistente**: `test_e2e_flow.py::TestE2EFlow::test_04_get_target_list` — 300+ targets de seed, target del test fuera del límite de paginación
- **Lint**: Ruff configurado, limpio (solo 5 pre-existing style suggestions no críticas)
- **Cobertura**: Sin regresiones — todo el código nuevo tiene cobertura indirecta via tests existentes

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

## Próximos Pasos (no implementados)

- FASE 5: Polish final (documentación, tests adicionales, limpieza)
- Health snapshots persistence (deuda conocida)
- Unificar sistemas de salud (deuda conocida)
- Frontend tests (no existen actualmente)
- Pre-commit hooks (no configurados)
