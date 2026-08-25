# AUDIT BACKEND ALPHA 1.0 — Mapa Arquitectónico y Riesgos

> **Fecha:** 2026-08-25 · **Método:** inspección de código real (file:line), no docs.
> **Alcance:** backend Python (api/, core/, cores/, database/), scheduler, sidecar, persistencia,
> revenue pipeline. Frontend fuera de alcance (ver FRONTEND_VISUAL_AUDIT.md).
> Este documento es el mapa previo obligatorio antes de implementar (AGENT_CHARTER §3).

---

## 1. Arquitectura actual (verificada)

```
FastAPI monolito modular (api/main.py)
├── Middlewares: SecurityHeaders → CSRF → RateLimit → Auth → ErrorHandling
│   (api/middleware/*.py; operation_id por request en ErrorHandlingMiddleware)
├── Lifespan: api/lifespan.py — init_db → EventBus → init diferido en bg task;
│   shutdown detiene engines + ScanScheduler + poller (quick-exit path los saltea)
├── ScanScheduler (api/scheduler.py) — pipeline bug bounty: discover→recon→hypothesis→
│   validate→promote→report→ai_bounty con cooldown 1h/target (RAM) y stale-scan recovery
├── CoreScheduler (core/scheduler/scheduler.py) — 12 ciclos / ~49 jobs declarados
│   en core/scheduler/jobs.py, handlers resueltos por dotted-path en api/lifespan.py:366
├── Revenue stack:
│   ├── cores/direct_work_engine/ — DWE (discovery/scoring/recommendation/workbank/
│   │   economics/cashflow/calibration/income_plan/max_daily_income)
│   ├── core/opportunity/ — engine + scorer + adapters (bug bounty)
│   ├── cores/revenue_tracker/ — RevenueTracker + OpportunityStage (Fase A) +
│   │   calibration loop (Fase D)
│   ├── core/revenue/ — engine legacy free-string states (discovered→…→paid)
│   └── core/execution_queue.py — ExecState 13 estados + JSON store (SIN trackear)
├── Payment compat: cores/payment_compat/ (76 cuentas curadas, regla honestidad dura)
└── Ledger eventos: cores/ledger/ (LedgerEvent StrEnum, DB-persistido vía LedgerEntry)
```

## 2. Entrypoints y lifecycle

| Entrypoint | Comportamiento |
|---|---|
| `run.py --daemon` | modo resistente dev |
| sidecar Tauri (`start_backend.py`) | setea OWNEX_DATA_DIR/DB_DIR/DESKTOP=1, file logging DEBUG, watchdog SIGTERM→os._exit(0) tras 8s |
| `src-tauri/lib.rs` | puerto dinámico 8000–8099 probe+bind, reuse-guard si health responde, MAX_POLLS 45×2s=90s, RunEvent::Exit→kill_backend() |

**Riesgo residual sidecar:** SIGKILL/crash de Tauri no ejecuta kill_backend (sin PID file ni reap).
Debug builds no gestionan backend (:133-136). TOCTOU pequeño entre probe y bind.

## 3. Persistencia — inventario real de escrituras runtime

**Honran OWNEX_DATA_DIR ✅:** workbank.json, market_kb.json, applications.json, calibration,
knowledge index, capabilities registry/expansion, hhd_tracker, self_improvement config.

**Repo-relativo ❌ (rompe frozen):** `cores/result_based.py:162` (first_day.json),
`cores/direct_work_engine/profile_kit.py:23`, `cores/fiverr/engine.py:145`,
`cores/finance/store.py:32`, `cores/direct_work_engine/maximum_potential.py:356`,
`cores/tools/ecosystem.py:85` (tool_usage.json), **`core/execution_queue.py:66-69`
(execution_queue.json via parents[3] — el archivo NUEVO ya nace roto para bundle)**.

**CWD-relativo ❌❌:** threat_intel cache (`os.getcwd()`), distillation samples,
`core/trading/store.py:20` (`Path("data/trading")` — contradice DECISIONS que dice ~/.config/ownex).

**Quinta convención:** `cores/platform/system.py:get_data_dir()` → `%APPDATA%/CATEYE` o `~/.orion`
(usado por scan_service recon output).

**Split de nombre de DB:** `api/main.py:204-218` fuerza `DATABASE_URL=<data>/cateye.db`
al importar api.main; `database/db.py:76-77` default es `catseye.db`. Dos nombres según entrypoint.

## 4. Scheduler

### CoreScheduler (ciclos)
- Poll asyncio 5s, handler **inline await** → un job lento bloquea todo el loop (:105-128).
- add_job dedup por job_id ✅; **locking/duplicate-exec: NONE** (dos procesos api.main = doble ejecución).
- last_run solo RAM → restart pierde estado; stop() cancela la task pero **nunca la awaita** (:44-49).
- Sin run ledger (no job_id/run_id/attempt/error persistidos).

### ScanScheduler (pipeline)
- Cooldowns/pipelines en RAM; stale scans >6h → failed vía recover_stale_scans
  ⚠️ perdió su boot hook (docstring dice "called on boot", solo corre dentro del tick).
- ScanRun persiste solo para recon (scan_service.py:50,150-186).
- 🔴 `_copilot_hook` NO-OP: método externo (:386-389) solo tiene docstring; el def interno
  (:391-455) nunca se invoca → TODOS los eventos PIPELINE_STAGE_* y recomendaciones COPILOT muertos.
- 🟡 Log format malformado `"%.0%%"` (:592) → ValueError en cada emit de priorización EV.

## 5. Revenue architecture — convergencia pendiente

### 5.1 Dos máquinas de estado formales paralelas (P0)

| Máquina | Ubicación | Estados | Git |
|---|---|---|---|
| OpportunityStage | cores/revenue_tracker/revenue_tracker.py:30-44 | DISCOVERED→QUALIFIED→IN_PROGRESS→SUBMITTED→ACCEPTED→{REJECTED\|REWARDED}→PAID (8) | commiteada |
| ExecState | core/execution_queue.py:13-26 | DISCOVERED→QUALIFIED→READY→QUEUED→EXECUTING→WAITING_HUMAN→SUBMITTED→VERIFICATION→PAID + REJECTED/BLOCKED/FAILED/DEAD_LETTER (13) | SIN TRACKER |

Comparten DISCOVERED/QUALIFIED/SUBMITTED/PAID/REJECTED; divergen en el medio. Ninguna referencia a la otra.
Además: PaymentStatus enum (mismo archivo) y free-string states en core/revenue/engine.py:49-114.

### 5.2 EV SSOT aspiracional (P0)

SSOT real: `cores/direct_work_engine/economics.py` (compute_expected_value :67-110,
compute_expected_human_value :139-202, HTROI :270-320). Consumidores productivos: SOLO 2
(recommendation.py:567 delega ✅; autonomous_discovery.py:235 delega parcialmente pero calcula
ev_per_hour inline en :243 ❌). compute_expected_human_value y compute_htroi: cero callers productivos.

**Fórmulas duplicadas vivas:** core/priority/ev_engine.py:71-146 (priors propios),
core/opportunity/scoring.py:31-33+186, core/validation/economic_scorer.py:120,180,
core/report_pipeline/__init__.py:231, core/autonomy/workflow_engine.py:189,
cashflow_radar.py:170, max_daily_income.py:201, income_plan.py:162,209,
strategy.py (7 scores), revenue_tracker.py:144.

### 5.3 Availability Intelligence (GAP P0 confirmado)

TaskAvailability existe SOLO como tipo en economics.py:28-50. Cero producers.
Ambas llamadas productivas de EV omiten availability → todo EV hoy es partial-EV con warning.
STALE solo existe para freshness financiera (truth_layer), no para tareas.

### 5.4 Ledger

cores/ledger/ = event log append-only DB-persistido (bounty_created, payout_received…) —
responde replay de wallet, NO el ladder EXPECTED→PENDING→PAID→NET del spec.
RevenueStats pending/accepted/paid_usd (core/revenue/models.py:139-141) es agregado parcial.
calibration.py es prediction-ledger ($/h predicho vs real, JSONL).

## 6. Platform metadata

RawOpportunity (core/opportunity/adapters/__init__.py:13-29): id/name/description/platform/url/
reward/effort_hours/tags — SIN country/barrier/qualification/payment/payout-min/freshness por listing.
Metadata estructurada existe SOLO a nivel plataforma-curada: global_sources.py (~139 fuentes,
requires_* bools, region, last_verified static "2026-07-30"); campos ricos (rate_source,
time_to_first_work, payout_cadence) solo para 4 plataformas AI-training (:1732-1785).
legacy.py:80-147 aplica catálogo con fallbacks hardcoded (experience_required=NONE, stability=0.5).

## 7. API quality

Global error handling CONFIRMADO (error_handling.py: op-id, ≥500 masked, 4xx preservados).
Patrones fake-success detectados:
- trading.py `_safe(fn, default)` traga TODO → dashboard siempre 200 con secciones vacías (:42-64).
- direct_work.py devuelve HTTP 200 con body {"error": str(e)} (:1204-1207); except:pass (:236,:259).
- control.py detail=str(e) en todos los 500s (masked por global handler, pero log-only correcto).
Paginación: solo direct_work.py:1133 valida Query(ge,le); resto límites sin validar.

## 8. Observabilidad

setup_logging (cores/log_config.py) configura SOLO logger "CATEYE"; todos los loggers `ownex.*`
(scheduler/api/db/threat_intel) caen al lastResort WARNING+. api/main.py:221 corre basicConfig
competidor antes de setup_logging. Sin file handler/rotación (el sidecar sí loguea a archivo).
operation_id middleware funciona E2E. **Trace de una oportunidad discovery→score→recommend en logs: NO**
(eventos muertos por _copilot_hook, format roto, sin correlation id cross-step).

## 9. Seguridad

CORS SSOT configure_cors() con orígenes tauri ✅ (remediación 2026-08-25). Cookie httpOnly +
Bearer dual ✅. CSRF double-submit con tests ✅. Rate limit por identidad con tests ✅.
Guardian tests JWT-committed ✅ (62f3ee72). Pendiente auditoría filesystem perms subprocess/Tauri
commands (fuera de este corte).

---

## 10. Riesgos priorizados

### P0 (bloquean Alpha 1.0)
| # | Riesgo | Evidencia |
|---|---|---|
| P0-1 | `_copilot_hook` no-op: integración EventBus/COPILOT del pipeline muerta | api/scheduler.py:386-456 |
| P0-2 | Doble máquina de estado formal (OpportunityStage vs ExecState) sin mapeo | revenue_tracker.py:30 vs execution_queue.py:13 |
| P0-3 | EV SSOT violado: 10+ fórmulas paralelas; $/human-hour sin consumers | ver §5.2 |
| P0-4 | Availability: señal inexistente, todo EV partial-EV UNKNOWN | ver §5.3 |
| P0-5 | execution_queue.json persiste repo-relative (nace rota para bundle) | execution_queue.py:66-69 |

### P1
| # | Riesgo | Evidencia |
|---|---|---|
| P1-1 | CoreScheduler sin locking/idempotencia/run-ledger; stop() no awaita | scheduler.py:44-128 |
| P1-2 | Stale-scan recovery sin boot hook | api/scheduler.py:179 único caller |
| P1-3 | Split cateye.db/catseye.db por entrypoint | api/main.py:218 vs db.py:77 |
| P1-4 | Log format ValueError %.0%% | api/scheduler.py:592 |
| P1-5 | Fake-success patterns trading/_safe + direct_work 200-con-error | ver §7 |
| P1-6 | Persistencia fragmentada: 9 módulos repo/CWD-relative + 5ª convención CATEYE | ver §3 |

### P2
- RawOpportunity sin metadata estructurada por-listing (§6)
- ownex.* logging sin configurar/rotación; basicConfig competidor (§8)
- Paginación sin validar en routers menores (§7)

## 11. Código muerto / duplicaciones verificadas

- `core/revenue/engine.py` free-string machine: solapada por las 2 formales — candidata a
  mapper-only, NO borrar sin demostrar 0 callers (pendiente verificación en corte de implementación).
- Fórmulas EV duplicadas listadas en §5.2 — migración incremental a economics.py, cada una con
  test de equivalencia antes de eliminar la copia local.

## 12. Inconsistencias doc/código

| Doc dice | Código hace |
|---|---|
| CURRENT_STATE: recover_stale_scans "hookeada en boot" | Solo corre en tick del ScanScheduler |
| DECISIONS trading store "~/.config/ownex/trading.json" | core/trading/store.py:20 = Path("data/trading") CWD-relative |
| TASK_QUEUE execution_queue "13 estados 6/6 tests" | Archivo sin trackear + store JSON añadido sin commit |

## 13. Orden de remediación propuesto

1. Fix P0-1 (_copilot_hook) + P1-4 (format) — bugs puros, test-first.
2. Convergencia de estados: mappers canónicos SSOT + queue persistence OWNEX_DATA_DIR (P0-2/P0-5).
3. EV SSOT: autonomous_discovery delega completo; availability engine v1 con producers reales (P0-3/P0-4).
4. Scheduler hardening (P1-1/P1-2) + boot hook.
5. Tests E2E offline discover→paid + docs (REVENUE_ARCHITECTURE, AUTONOMY_MODEL, CURRENT_STATE, DECISIONS).
