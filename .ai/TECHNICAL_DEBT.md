# OWNEX TECHNICAL DEBT — Technical Debt Tracker

> **Última actualización**: 2026-08-24 — auditoría funcional completa del frontend.
> Matriz viva: `.ai/FRONTEND_FUNCTIONALITY_MATRIX.md` (fuente de verdad de estado por página).

---

## Frontend Debt (auditoría 2026-08-24)

### P1
- **PipelineMonitor/Detail + ActionsView apuntan a namespaces inexistentes** (`agents/pipelines/*`, `execution/actions`) — mapear a scan_runs/scheduler reales del backend. Impacto: monitoreo core sin datos.

### P2
- **Identity.vue**: botones sync-all/sync/{provider}/settings sin backend → ocultar o implementar.
- **OpportunityPlanner/ProgramCatalog**: llamadas muertas (`opportunity/catalog`, `economic/programs/{id}/plan`) → conectar a opportunity-score/top5 o retirar tabs.
- **Settings IA**: inputs config para providers que usan env vars (devin/freebuff/local).
- **OperationsDashboard**: `operations/metrics` ABSENT → mapear a core/health/summary.
- **KnowledgeGraphMini**: endpoints nodes/edges ABSENT → remapear a knowledge real o retirar widget.
- **EvidenceCenter**: listado genérico `/evidence` ABSENT → usar evidencia por finding.

### P3
- Wallets GET, ReplayCenter targets, ConfidenceDashboard audit — endpoints ABSENT, empty states honestos.

### Decisión producto (RESUELTA por owner: CONSTRUIR)
- **Investment sub-adapters**: RESUELTO — los adapters ya existían completos en core/investment/adapters/; el gap era solo routing. 34 rutas nuevas en api/routers/investment.py (commit wiring) exponen ccxt/defi×4/stocks/polymarket/backtest. Órdenes reales gated por risk (409 si paused). Tests: tests/test_investment_wiring.py 18/18. Backtest = MA-crossover determinista en pandas puro (vectorbt no instalado — sin dependencia nueva).

---

## Resuelto (histórico)

| Item | Fecha | Evidencia |
|---|---|---|
| Doble prefijo /api/api (~150 call sites, 404 silencioso) | 2026-08-24 | normalización en lib/api.ts::request() |
| Namespaces root-mounted (direct-work/mobile/wear-os → 404 total) | 2026-08-24 | resolveApiUrl() + vite proxies; E2E 11/11 |
| fetch crudos con path hardcodeado (evidence upload, chat stream, pdf export) | 2026-08-24 | getApiBase() request-time |
| Discovery sin recuperación (puerto cacheado forever, polling abandona) | 2026-08-24 | reset on network-error + rescan infinito |
| Fondo rojo inexplicable (banners destructivos ante fallos transitorios) | 2026-08-24 | ErrorState.vue ERROR/CAUSA/ACCIÓN + estados connecting calmados |
| 254 errores tsc preexistentes | 2026-08-24 | vue-tsc --noEmit = 0 errores (verificado) |
| Biome config rota (schema 1.9 vs CLI 2.5) | 2026-08-24 | biome migrate + overrides .vue (template-blindness: noUnused* off, vue-tsc es autoridad) |
| Test Settings stale ('cyber' theme inexistente) | 2026-08-24 | aserción alineada a render real |
| Android namespace (3 distintos) | 2026-08-10 | ai.rastro.app unificado (AUD-12) |
| WearOS no buildable | 2026-08-01 | descartado AUD-14 (ROI negativo) |
| console.log frontend móvil | 2026-08-10 | eliminados (quedan console.error legítimos) |

---

## Debt Budget

| Priority | Items | Estado |
|----------|-------|--------|
| P1 | PipelineMonitor/ActionsView mapping | abierto |
| P2 | Identity/OpportunityPlanner/Settings-fields/OpsMetrics/KGMini/EvidenceList | abierto |
| P3 | Wallets/Replay/ConfidenceAudit | abierto |
| Producto | investment sub-adapters build-or-remove | decisión owner |


---

## Minor Debt (P2)

### Auto Maintenance System Not Exists
- **Issue:** OWNEX cannot automatically detect errors, outdated libraries, old documentation, incorrect configurations
- **Impact:** Debt accumulates, system degrades over time
- **Cost:** Manual maintenance burden
- **Plan:** Implement basic auto-diagnosis and recommendation system
- **Estimate:** 12 hours
- **Owner:** Dev

### Lint Errors (Legacy)
- **Issue:** 30 remaining lint errors (legacy code, not new)
- **Impact:** Code style inconsistency, potential bugs
- **Cost:** Maintenance burden
- **Plan:** Fix remaining lint errors (E741, F401, F841)
- **Estimate:** 2 hours
- **Owner:** Dev

### Premium Sounds Not Fully Implemented
- **Issue:** Premium sounds not implemented in all interactions
- **Impact:** Inconsistent user experience
- **Cost:** Not achieving premium feel
- **Plan:** Implement sounds in all components
- **Estimate:** 4 hours
- **Owner:** Dev

---

## Decisions Made

### cores/ vs cores/ Decision (2026-07-31)
- **Decision:** cores/ is Single Source of Truth (SSOT)
- **Reason:** cores/ has 845 files vs 533 in core/, 2x more imports in API, contains productive CATEYE pipeline
- **Plan:** Migrate core/ to cores/ gradually
- **Status:** In progress
- **Estimate:** 8 hours

---

## Debt Reduction Strategy

### 1. Pay Critical Debt First
- Mobile Companion (configure Supabase)
- Android namespace (unify)
- WearOS (decision)

### 2. Pay Important Debt Second
- Fix tsc errors
- Remove console.log
- Implement auto maintenance

### 3. Pay Minor Debt Last
- Fix lint errors
- Implement premium sounds
- Complete cores/ migration

---

## Debt Budget

**Total Debt Cost Estimate:** 43.5 hours

| Priority | Debt Items | Hours | Completed | Remaining |
|----------|-----------|-------|-----------|-----------|
| P0 | Mobile Companion, Android, WearOS | 11.5 | 0 | 11.5 |
| P1 | tsc errors, console.log | 6.5 | 0 | 6.5 |
| P2 | Auto maintenance, lint, sounds | 18 | 0 | 18 |
| Decision | cores/ migration | 8 | 0 | 8 |

---

## Prevention

### Rules to Avoid New Debt

1. **No TODO without date** - Every TODO must have a deadline
2. **No dead code** - Delete obsolete code immediately
3. **No unused imports** - Remove unused imports immediately
4. **No console.log in production** - Use proper logging
5. **Type safety** - Use TypeScript strict mode
6. **Lint passing** - All code must pass lint
7. **Tests passing** - All tests must pass before commit
8. **Documentation** - Document complex logic

### Code Review Checklist

- [ ] No new TODOs without dates
- [ ] No dead code added
- [ ] No unused imports
- [ ] No console.log in production code
- [ ] TypeScript strict mode compliant
- [ ] Lint passing
- [ ] Tests passing
- [ ] Documentation updated

---

## Debt Payoff Log

| Date | Debt Item | Hours Spent | Status |
|------|-----------|-------------|--------|
| 2026-08-01 | N/A | 0 | N/A |

---

## Last Updated

**Date:** 2026-08-01
**Updated By:** CATEYE Excellence Protocol
**Version:** 1.0
