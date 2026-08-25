# FRONTEND FEATURE PARITY AUDIT — OWNEX

> **Spec**: FRONTEND FEATURE-PARITY TOTAL · **Fecha**: 2026-08-25
> **Método**: inventario de 1.303 endpoints reales vía `app.openapi()` → clasificación A-E → wiring de gaps críticos.
> **Estado**: FASE 1 COMPLETA — superficies de dinero/trabajo/IA/riesgo conectadas. Ver §Matriz para pendientes.

## 1. Inventario backend (fuente de verdad)

`api.main:app.openapi()` → **1.303 paths** en **305 grupos**. Top grupos:
core(74) cycles(58) investment(57) reports(31) personal-infrastructure(29) financial(24)
self-improvement(21) assistant/opportunity/economic(18 c/u) trading(17) knowledge(15) execution(13)
revenue(11) direct-work(30+ endpoints sueltos) wear-os(7) mobile(12).

## 2. Clasificación de capacidades

### A — VISIBLE Y OPERABLE (con acciones reales)

| Capacidad | Superficie | Acciones | Endpoints |
|---|---|---|---|
| Next Best Action + EV/hora | `IncomeHome.vue` (`/`) | Ejecutar/abrir acción, posponer | `/applications/income-plan` |
| Potencial HOY/SEM/QUINCENA/MES | IncomeHome | — | idem (income_command_center) |
| ESPERADO ≠ REALIZADO | IncomeHome | — | `/payment-tracker`, `/revenue/summary` |
| **Snapshot de capital (SSOT)** | IncomeHome (banda nueva) | — | `/financial/capital/snapshot` |
| Estado IA en Command Center | IncomeHome (badge nuevo) | — | `/settings/ai/config` |
| **Cola de trabajo ejecutable** | `WorkQueue.vue` (`/operations/work-queue`) NUEVA | Avanzar estado / Rechazar (transiciones validadas por backend) | `/execution-queue*` |
| **Ingresos: cobrado/pendiente/fuentes/envíos** | `RevenueCenter.vue` (`/revenue/center`) NUEVA | retry | `/revenue/summary`, `/revenue/submissions` |
| **Providers IA** | `AiCenter.vue` (`/ai`) NUEVA | ver estado honesto (nunca finge disponibilidad) | `/settings/ai/*`, `/oar/status` |
| **Riesgo + Kill Switch** | `RiskCenter.vue` (`/risk`) NUEVA | confirmación explícita para STOP | `/emergency-mode`, `/capital/risk`, `/copy/status` |
| Work Bank (preparar/entregar) | DirectWorkRadar.vue | preparar entrega, marcar entregado | `/direct-work/workbank/*` |
| Postulaciones AI-training | ApplicationAssistant.vue | completar pasos, cambiar status | `/applications/*` |
| Trading + Copy Trading | TradingIntelligence.vue | ingest/toggle/emergency-stop | `/trading/*` |
| Polymarket | PolymarketTrading.vue | — | `/polymarket` interno |
| Capital dashboard multi-tab | Capital.vue | settings, targets, pipeline | `/capital-bar`, `/finance/*` |
| Watch approvals | WatchApprovals.vue (`/watch/approvals`) | aprobar/rechazar one-tap | `/wear-os/approval` |

### B — VISIBLE SOLO LECTURA

Pipeline security (executive dashboard), findings/hypotheses/evidence, health center,
scheduler status, activity timeline, knowledge vault, métricas de ciclos.

### C — BACKEND-ONLY EXPLÍCITO (documentado, no es omisión)

- `/api/core/*` (74): motor de salud/memoria interno — visible vía Health Center agregado.
- `/api/cycles/*` bookkeeping DB: visible vía dashboards por ciclo.
- `/api/files`, `/api/sandbox`, migrations, locks, WS internals.
- `/mobile/*`: consumidos por la app Android nativa, no por el SPA desktop.
- `/devin/*`, `/cli/*`: interfaces de agente CLI, no UI web.

### D — INFRASTRUCTURE-ONLY

Auth tokens/refresh, CSRF, version backup internals, supabase sync opcional.

### E — MUERTO/MOCK detectado y tratado

- GamingConsole: ya sin mock (sesión previa AUD-7).
- Fleet de agentes falso: eliminado en sesión previa (`aab28579`).
- Los 4 feeds de ownexData propagan ApiError → ErrorState alcanzable.

## 3. Gaps restantes (priorizados, fase 2)

| Gap | Esfuerzo | Nota |
|---|---|---|
| Opportunity Radar card con progressive disclosure completa (barrier/qualif/dup-risk por tarjeta) | M | `/targets/prioritization` existe; falta detalle L3-L4 |
| Automation Center dedicado (jobs con run-now/pause) | M | Scheduler page existe; falta control fino |
| Knowledge search integrado a oportunidades | S | Knowledge.vue existe; falta link contextual |
| Notifications center con filtros por severidad | S | NotificationsPage existe |
| Mobile surfaces nativas (NOW/MONEY/APPROVE offline-first) | L | Companion existe; falta parity de las 4 superficies nuevas |
| Settings separados por dominio (spec §15) | M | Settings.vue monolítico hoy |

## 4. Verificación (evidencia)

- `vue-tsc --noEmit`: **0 errores** global.
- `vite build`: ✓ built in 14.34s con las 4 páginas nuevas emtidas como chunks.
- Tests backend nuevos: `test_income_target.py` (14) + `test_payment_pipeline.py` (20) = 34 passed.
- Suite fast backend: 100 passed / 1 skipped (baseline intacta).
- Contención documentada: `Capital.vue` bajo edición del proceso concurrente durante esta sesión
  (3 reversiones observadas); NO incluido en este commit — su estabilización es del dueño actual.

## 5. Regla aplicada

Toda superficie nueva usa **datos reales del backend o estado de error honesto** — cero fake UI.
Progressive disclosure: N1 número/acción → N2 fuentes/desglose → N3 JSON crudo expandible (AI/Risk).
