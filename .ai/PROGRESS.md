# OWNEX — Progressive Advancement Ledger

> **Propósito**: una sola fuente de verdad del % de avance por módulo.
> Cada fila exige evidencia (commit/test/live-check) — nunca "parece listo".
> `scripts/progress.py` parsea este archivo y reporta el % global + delta
> vs. el último snapshot (`.ai/progress_snapshot.json`).
>
> Estados (canónicos, ver PROGRESSIVE_DEVELOPMENT_SYSTEM.md §4 + INTEGRATION_PROTOCOL): `NOT_STARTED` · `PLANNED` · `IN_PROGRESS` · `BLOCKED` · `IMPLEMENTED` · `TESTED` · `INTEGRATED` · `VERIFIED` · `ACCEPTED` · `DEPRECATED`
> Un módulo solo sube de estado con evidencia citada en la columna Evidence.

## Módulos

| Módulo | % | Estado | Evidencia | Bloqueo | Próxima acción |
|--------|---|--------|-----------|---------|----------------|
| Source Intelligence (catálogo 1000 + L1-L5) | 70 | IMPLEMENTED | `assess_integration`: 68 L2 / 932 L1 / 0 L3+ (commit `92f3605af`) | L3+ requiere cuentas del owner | Subir fuentes L1→L2 con fetchers agregadores |
| Discovery pipeline (fetchers→LiveStore→eligibility) | 85 | VERIFIED | 619 opps live, 22 fetchers, scan 6h verificado (`3c9803ed9`) | — | Mantener scans; monitorear freshness |
| Scoring / EV model | 75 | VERIFIED | AI-cost neto, budget $25, track-record, freshness, funding tri-state (`5ae053d59`,`eb17cff1d`) | P(éxito) formal pendiente | Calibrar pesos con outcomes reales |
| Work Bank / priorización | 80 | VERIFIED | 502 items, daily_cycle real, 369 ready_to_deliver post-repair | Ready ≠ ejecutable (ver Factory) | Separar "programa security" vs "task entregable" en ranking |
| Revenue Ledger / finanzas | 65 | IMPLEMENTED | `record_amount` con evidencia obligatoria para `paid`; summary por buckets | 0 payouts reales aún | Registrar primer `paid` con evidencia |
| Human Actions / aprobaciones | 75 | VERIFIED | `/api/human-actions` + UI `/operations/human-actions`, 21 acciones parseadas | — | Convertir needs_access en acciones concretas |
| Agent-market adapters (taskmarket/hansa/agentics) | 60 | IMPLEMENTED | 3 adapters read-only + write-client gated (`afc001d5c`) | Registro B6/B7/B10 = humano | Ejecutar primer pitch tras registro |
| Project Engineering Factory | 15 | IMPLEMENTED | `prepare_execution` clona repos, `analyze_workspace` existe | Sin loop dev→PR→entrega | Primer ciclo completo con task real |
| Multi-agent / workers | 10 | IMPLEMENTED | ExecutionQueueStore + states existen | Sin workers ejecutando | Planner→Implementer→Reviewer mínimo |
| Delivery / submission | 10 | NOT_STARTED | `record_approval`/`draft_payment_inquiry` existen | Sin submission real | Draft PR en primer proyecto |
| Security research (CATEYE core) | 50 | IMPLEMENTED | Pipeline hallazgos existe; 365 programas en LiveStore | Cuentas plataformas = humano | Elegir 1 programa + ciclo research |
| Sanitization / prompt-injection | 60 | VERIFIED | `core/security/sanitization.py` en `_to_live` (`eb17cff1d`) | Cobertura parcial del surface | Extender a otros puntos de entrada agent |
| Frontend / productization | 30 | IMPLEMENTED | 83 páginas, shell existe, HumanActions UI nueva | Multi-sesión, npm install pendiente | FASE 0-1: install + App Shell (directiva Hermes) |
| Desktop / Tauri | 40 | IMPLEMENTED | Scripts tauri:dev/build existen | Sin build verificado reciente | Build de prueba + runbook |
| Consolidación core/↔cores/ | 30 | IMPLEMENTED | CANONICAL_COMPONENTS.md existe; bridges temporales | Decisión por dominio pendiente | Auditoría de imports por dominio |
| Tests / quality gates | 65 | IMPLEMENTED | 1460+ tests focalizados verdes; suite completa rota por WIP paralelo | `test_cex_connector`/`INVESTMENT_GLOBAL` + permissions | Reconciliar WIP paralelo, suite verde |
| Investment Hub | 50 | UNKNOWN | Sesión paralela activa (no auditado por este lane) | WIP sin commitear | Auditar cuando commitee |

## Reglas del ledger

1. **Solo evidencia cuenta**: commit hash, test count, live-check con fecha, o URL verificable.
2. **Nada de % inflado**: "existe el módulo" ≠ "funciona". FUNCTIONAL exige uso real verificado.
3. **Cada sesión actualiza su fila** al cerrar trabajo — el delta entre snapshots es el progreso real.
4. **UNKNOWN es honesto**: mejor UNKNOWN que un número inventado.
5. **Bloqueos humanos se listan explícitamente** — no se disimulan como trabajo pendiente de código.

## Snapshot rule

`python3 scripts/progress.py` compara contra `.ai/progress_snapshot.json` y muestra
qué módulos subieron/bajaron desde la última medición. Regla: correrlo al inicio
y al cierre de cada sesión de trabajo.
