# AUDIT_BACKEND_ALPHA_1.0 — auditoría con evidencia (2026-09-15)

> Primera acción del spec BACKEND ALPHA 1.0 (TASK_QUEUE.md). Regla de Oro aplicada:
> verificar qué existe antes de construir. Veredicto: el spec está **~85% construido
> bajo otros nombres**; los gaps son de frontera/nomenclatura, no de sistemas ausentes.
> NO se construye nada nuevo salvo el runner 1c ya implementado (ver abajo).

## Matriz spec vs realidad

| # | Pieza del spec | Estado real | Evidencia |
|---|---|---|---|
| 1 | Auditoría total | ✅ ESTE DOC | — |
| 2 | Revenue Orchestrator | ✅ EXISTE | `cores/direct_work_engine/engine.py::DirectWorkEngine` (discover→score→recommend→stats) + `cores/automation/daily_loop.py::run_daily_loop()` (SELECT→A1→A2→A3→payment→learning) |
| 3 | Economic Engine único | 🟡 DUAL con frontera real | V1 `economic_engine.py` (docstring "SSOT"): perfil económico por oportunidad (EV/h-humana, cash, acceptance) para **decidir**. V2 `economic_engine_v2.py`: máquina de estados de revenue (THEORETICAL→…→NET) para **contabilizar**. Dominios distintos (decisión vs contabilidad), no duplicación lógica. Gap = ambos docstrings reclaman "SSOT". Fix = aclarar frontera en docstrings, NO reescribir. Usuarios: V1 ← `income_target.py`; V2 ← `daily_brief_v2.py`, `ai/control_plane.py`, `worker_core/integration.py` |
| 4 | Zero-Barrier normalizado | ✅ EXISTE | `scoring.py::ZeroBarrierScorer` (espectro 0-100) + `models.py::is_zero_experience/is_zero_barrier` + `zero_barrier_mode.py`. Regla "Zero Experience ≠ Zero Barrier" vigente desde 2026-08-25 |
| 5 | Platform Intelligence | ✅ EXISTE | `source_intel.py::SourceIntelEngine` (135 fuentes, trust score, Argentina-compat) + `competition_intel.py` (`observed_claims`, UNKNOWN honesto) |
| 6 | Availability Engine | ✅ EXISTE | `availability.py::AvailabilityEngine` + `get_available_hours()`; `UserProfile.availability_hours` (default 40); `income_target.py` lo consume con fallback honesto |
| 7 | Execution Automation levels 0-4 | 🟡 OTRA TAXONOMÍA | No existen "niveles 0-4" con ese nombre. Lo que existe: ladder A0-A11+A6 (`cores/automation/ladder.py`, 2026-09-14) + `AutomationLevel` MANUAL/SEMIAUTOMATICA/AUTOMATICA/IMPOSIBLE (`cores/projects/models.py`) + A0 en `zero_barrier_engine`. Mapeo: A-ladder cubre la progresión; renombrar a 0-4 sería cosmético y rompería tests. Decisión: NO renombrar; el spec adopta la taxonomía A-ladder |
| 8 | Revenue Ledger | ✅ EXISTE | `cores/ledger/` (append-only, replay, `LEDGER_EVENTS`) + `revenue_tracker/execution_bridge.py` (SUBMITTED→REVIEWING, PAID inalcanzable) + `/direct-work/revenue-ledger` UI + `capital/timeline.py` (vista auditable). Rule §39 testeada |
| 9 | Scheduler idempotente | ✅ EXISTE | `cores/scheduler/jobs.py` (flock cross-proceso, anti-overlap, run ledger JSONL) + `test_cycle_task_handlers.py` (todos los handlers resuelven) |
| 10 | Sidecar lifecycle | ✅ EXISTE | `desktop/native/services/backend.py` + spec ONEFILE + smoke sidecar 7.1.x |
| 11 | Persistencia %LOCALAPPDATA% | ✅ EXISTE | `database/db.py::user_data_dir()` + `OWNEX_DATA_DIR`/`CATEYE_DATA_DIR` en WorkBank/MarketKB/submissions |
| 12 | Observabilidad estructurada | 🟡 TECHO DECLARADO | `operation_id` + `X-Operation-Id` + health endpoints + `/api/system/diagnostic-bundle`. Sin trace global ni logs JSON (techo honesto desde 100/100 Bloque 1) |
| 13 | E2E sin internet | 🟡 PARCIAL | Tests mockean red (httpx mock, fakes); `test_offline_degraded.py` pinea OFFLINE_AI. Sin suite E2E full-offline dedicada — follow-up, no bloqueante |

## Único gap real de código (cerrado hoy)

- **1c `investment_arbitrage_scan`**: job documentado en `get_investment_jobs()` pero runner
  inexistente (`cores.investment.tasks` nunca creado). Cerrado: `cores/investment/tasks.py`
  (`run_arbitrage_scan_once` inyectable + `run_investment_arbitrage_scan` thread-safe) +
  job cada 4h + `tests/test_investment_arbitrage_scan.py` 5/5. Solo lectura: jamás llama
  `execute_trade` (pineado por test). Respeta bloqueo de trading live del owner.
- **Restantes 1c**: `coder_autopilot` batch (requiere diseño: DevBountyPipeline exige bounty
  fully-specified; batch = discovery→filtro→queue, NO ejecución autónoma) y 8 fns trading
  (NO construir: trading live bloqueado por orden del owner; paper loop cada 15m ya corre).
  Ambos quedan como deuda explícita, no como jobs fantasmas.

## Decisión permanente

Ningún componente BACKEND ALPHA se reconstruye bajo otro nombre. Divergencias futuras de
taxonomía (0-4 vs A-ladder, V1 vs V2) se resuelven con frontera documentada, no con rewrites.
