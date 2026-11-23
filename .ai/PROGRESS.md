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
| Discovery pipeline (fetchers→LiveStore→eligibility) | 86 | VERIFIED | 619 opps live, 22 fetchers, scan 6h verificado (`3c9803ed9`); fuentes placeholder (RFC 2606/6761) en cuarentena y reportadas como `quarantined` (`04efdff36`, 208 tests focalizados) | — | Mantener scans; monitorear freshness |
| Scoring / EV model | 75 | VERIFIED | AI-cost neto, budget $25, track-record, freshness, funding tri-state (`5ae053d59`,`eb17cff1d`) | P(éxito) formal pendiente | Calibrar pesos con outcomes reales |
| Work Bank / priorización | 80 | VERIFIED | 502 items, daily_cycle real, 369 ready_to_deliver post-repair | Ready ≠ ejecutable (ver Factory) | Separar "programa security" vs "task entregable" en ranking |
| Revenue Ledger / finanzas | 70 | IMPLEMENTED | `record_amount` con evidencia obligatoria para `paid`; `progress.py::verified_revenue` solo cuenta `paid`+evidence (9 tests) | 0 payouts reales aún; 2 items `state=paid` sin evidencia flaggeados | Registrar primer `paid` con evidencia |
| Human Actions / aprobaciones | 80 | VERIFIED | `/api/human-actions` + UI, 22 acciones, estados canónicos (READY_FOR_OWNER/WAITING_EXTERNAL/EXPIRED…) + `by_state` | — | Convertir needs_access en acciones concretas |
| Agent-market adapters (taskmarket/hansa/agentics) | 70 | IMPLEMENTED | discovery read-only live (api.taskmarket.dev 200); `TaskmarketExecutor` en execution queue con doble gate (driver `approved` + `TaskmarketActions` authorized+creds); twins muertos eliminados | Registro B6/B7/B10 = humano | Ejecutar primer pitch tras registro |
| Project Engineering Factory | 15 | IMPLEMENTED | `prepare_execution` clona repos, `analyze_workspace` existe | Sin loop dev→PR→entrega | Primer ciclo completo con task real |
| Multi-agent / workers | 10 | IMPLEMENTED | ExecutionQueueStore + states existen | Sin workers ejecutando | Planner→Implementer→Reviewer mínimo |
| Delivery / submission | 15 | IMPLEMENTED | `TaskmarketExecutor` ruteado en execution_queue driver (`submit_pitch`/`submit_work`/`request_upload_url` gated); `record_approval`/`draft_payment_inquiry` existen | Sin submission real; sin credenciales B6 | Primer pitch Taskmarket tras registro B6 |
| Security research (CATEYE core) | 50 | IMPLEMENTED | Pipeline hallazgos existe; 365 programas en LiveStore | Cuentas plataformas = humano | Elegir 1 programa + ciclo research |
| Sanitization / prompt-injection | 60 | VERIFIED | `core/security/sanitization.py` en `_to_live` (`eb17cff1d`) | Cobertura parcial del surface | Extender a otros puntos de entrada agent |
| Security isolation (sandbox + credential broker) | 40 | TESTED | `core/security/{sandbox,credential_broker}.py` consolidados en el árbol canónico, duplicado `cores/security/` eliminado; 17 tests (`d7188cc24`) | Path Docker solo verificado a nivel args (sin Docker en el entorno); broker sin integrar a workers | Cablear broker a los workers de la Factory |
| Frontend / productization | 45 | TESTED | App Shell V2.1 (8 secciones, router-view real en ErrorBoundary, tokens.css :root fix); biome clean; 226 vitest pass; `vite build` OK; QA captures `frontend/qa/screenshots{,-auth}` + FRONTEND_RUNBOOK.md (2026-11-23) | Command Center con datos reales pendiente | Iterar Command Center sobre el shell nuevo |
| Desktop / Tauri | 40 | IMPLEMENTED | Scripts tauri:dev/build existen | Sin build verificado reciente | Build de prueba + runbook |
| Consolidación core/↔cores/ | 30 | IMPLEMENTED | CANONICAL_COMPONENTS.md existe; bridges temporales | Decisión por dominio pendiente | Auditoría de imports por dominio |
| Tests / quality gates | 65 | IMPLEMENTED | 1460+ tests focalizados verdes; suite completa rota por WIP paralelo | `test_cex_connector`/`INVESTMENT_GLOBAL` + permissions | Reconciliar WIP paralelo, suite verde |
| Investment Hub | 60 | TESTED | Strategy attribution (`TradeGroupMetrics`), `LEG_UNHEDGED` para patas sin fill, `net_pnl_completeness`+currency en `record_trade`, `strategy_attribution` en `/api/investment/metrics`, `GlobalArbitrageAdapter` + CLI paper-trade (`0c4162137`); 208 tests focalizados | Sin capital real; FX policy (#2) sigue bloqueada | Ejecutar paper-trade con datos live y revisar attribution |

## Métricas independientes (nunca promediadas)

| Indicador | Qué mide | Valor actual |
|-----------|----------|--------------|
| **PRODUCT_COMPLETENESS** | % de la tabla de módulos (software implementado+integrado+probado) | ver `progress.py` |
| **OPERATIONAL_READINESS** | % de cuentas/credenciales/integraciones externas conectadas y probadas | ver sección abajo |
| **REVENUE_PIPELINE_PROGRESS** | % de etapas técnicas del pipeline económico demostradas (antes llamado REVENUE_VALIDATION — NO es ingreso) | ver sección abajo |
| **VERIFIED_REVENUE** | USD efectivamente pagados con evidencia (solo bucket `paid` + evidence en RevenueLedger) | USD 0 |
| **VERIFIED_PAID_CYCLES** | Ciclos completos trabajo→pago comprobado | 0 |
| **REWARD_REALIZATION_RATE** | verified_revenue / comprometido (approved+pending+paid, USD) | null hasta primer compromiso |
| **TIME_TO_FIRST_PAYOUT** | Tiempo desde inicio verificable hasta primer pago recibido | null hasta primer payout |

Una acción humana pendiente bloquea OPERATIONAL/REVENUE, **no**
PRODUCT_COMPLETENESS. Un módulo "listo" sin cuenta conectada sigue
siendo producto completo — pero no operativamente ready.

**Regla de integridad**: progreso de pipeline ≠ ingreso. Ningún estado
(`accepted`, `submitted`, `ready`, `state=paid` sin evidence) puede
incrementar VERIFIED_REVENUE. Solo `finance.latest.paid` con `evidence`
no vacío cuenta como dinero cobrado.

## Operational Readiness (cuentas e integraciones)

| Ítem | Estado | Evidencia | Acción humana |
|------|--------|-----------|---------------|
| Taskmarket agent registration (B6) | BLOCKED | endpoint público verificado; write-client gated listo | registrar agente + identity_token |
| Agent Hansa registration (B7) | BLOCKED | adapter read-only live | cuenta + credenciales |
| BasedAgents/ClawHunt (B10) | BLOCKED | sin API pública verificada | evaluar registro manual |
| GitHub PAT para rate limits | PENDING | `gh` CLI autenticado como AdriDob (2026-11-21) | definir scope del token |
| IssueHunt cuenta + payout AR | PENDING | payout methods no confirmados para AR | verificar Stripe/PayPal/crypto |
| Cuentas security (H1/BC/Intigriti/YWH) | PENDING | fetchers públicos funcionan sin auth | API tokens opcionales |
| Wallet crypto (escrow payouts) | PENDING | taskmarket paga vía escrow on-chain Base | crear wallet + off-ramp |

## Revenue Pipeline (ciclos económicos)

| Etapa del ciclo | Estado | Evidencia |
|-----------------|--------|-----------|
| Oportunidad real descubierta | DONE | 619 live opps en LiveStore |
| Evaluada y priorizada | DONE | score_opportunity + rank_opportunities |
| Workspace preparado | PARTIAL | `prepare_execution` clona repos (sin proyecto real aún) |
| Desarrollada por agentes | NOT_STARTED | sin loop dev→PR ejecutado |
| Entrega enviada | NOT_STARTED | — |
| Aceptada por requester | NOT_STARTED | — |
| Pago recibido y verificado | NOT_STARTED | RevenueLedger: 0 `paid` con evidencia; 2 items `state=paid` sin evidencia (test pollution — flaggeados por progress.py, no cuentan) |
| Retiro/off-ramp | NOT_STARTED | — |

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
