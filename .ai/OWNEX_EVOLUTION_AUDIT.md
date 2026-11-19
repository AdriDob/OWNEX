# OWNEX Evolution Audit — Phase 0/1 baseline

> Fecha: 2026-11-19 · Base auditada: `main@0d8a9deb` (HEAD commiteado) + worktree `agent/twin-tree-consolidation@2d8013f1`.
> Estado del worktree principal: **CONFLICTO SIN RESOLVER** (24 unmerged, 164 `cores/*` borrados staged, `database/models.py` con tablas duplicadas → pytest roto). Auditoría realizada sobre HEAD + filesystem; las cifras de worktree pueden diferir hasta resolver.

## Git baseline

| Item | Valor |
|---|---|
| Rama | `main` ↔ `origin/main` (+0/-0) |
| HEAD | `0d8a9deb` |
| Worktrees | `/home/adriel/projects/Rastro` (main, conflicted), `/home/adriel/projects/rastro-twin-tree` (`agent/twin-tree-consolidation`, limpio) |
| Tests baseline (último verde conocido) | ~5.689 passed / 18 skipped / 2 xfailed |
| Frontend build | verde (vite 17.9s, biome limpio) |
| Ingreso verificado | **USD 0.00** |

## Inventario de arquitectura (HEAD)

| Área | Implementación actual | Estado | Gaps |
|---|---|---|---|
| **Frontend** | Vue3 + Vite6 + Tailwind4 + Pinia3 + vue-router + axios + chart.js + xterm + Tauri2. **82 páginas**, ~25 dirs de componentes, 9 stores, `components/ui/` con design system propio (Ownex*/shadcn-style) | Implementado, build verde | 82 páginas = dispersión; CommandCenter/Discovery/MissionControl/ExecutiveDashboard/IncomeHome se solapan; sin TanStack Query (Pinia cubre); sin ECharts (chart.js presente — decidir si basta) |
| **Backend API** | FastAPI, **173 routers**, `api/main.py` | Implementado | Exceso de routers (auth×4, opportunity×2+, discovery duplicado legacy+live); contratos no centralizados |
| **Dominio core/** | 671 .py — opportunity engine, executors, autonomy, scheduler, events | Canónico (destino de consolidación) | — |
| **Dominio cores/** | 1.039 .py — gemelo legacy; contiene live_pipeline, live_connections, revenue_ledger, sources_expansion, security adapters | **Siendo eliminado por twin-tree** | Migrar live pipeline a `core/` antes de perderlo |
| **Persistencia** | SQLite (`database/`): db.py, models.py + models_assets/cycles/economic, migrations/, supabase_schema.sql | Implementado | models.py en consolidación (duplicados temporales); conviven db SQLite yPossible supabase — aclarar |
| **Scheduler/Jobs** | `api/scheduler.py`, `core/scheduler/`, `core/cron_scheduler.py`, `apps/*/scheduler.py` | **Múltiples schedulers** | Riesgo de jobs duplicados — auditar jobs activos |
| **Integraciones live** | 22 fetchers reales (12 forge en `core/` + 10 security en `cores/`), live_pipeline, eligibility, ethics screen, workbank bridge, execution queue, revenue ledger | Implementado+parcialmente testeado (48 tests) | Security adapters mueren con `cores/`; submission path inexistente; 392 needs_access |
| **Execution** | `core/execution_queue/` + executors de plataforma (mutaciones gated por aprobación) | Parcial | No hay path de submission para GitHub bounties; implement loop manual |
| **Financial** | revenue_ledger (5 buckets, evidencia obligatoria en paid), financial_intelligence | Implementado | USD 0 real; conectar payout evidence |
| **Investment** | cores/financial_intelligence, InvestmentHub.vue, trading modules (en borrado staged) | Parcial/unknown | Agentes borrando `cores/trading/*` — verificar destino en core/ |
| **Desktop** | Tauri v2 + xterm.js + FastAPI WS sidecar | Implementado | — |
| **Tests** | pytest (~257 archivos), vitest, playwright instalado | Implementado | Suite rota por conflicto actual, no por código |
| **Auth** | auth.py + auth_user(s).py + authhub.py + supabase | Parcial | 4 routers auth — consolidar; FastAPI Users rechazado (maintenance) |

## Decisiones de diseño ya tomadas (EVOLUTION_DIRECTIVE.md)

- **Design system**: extender `components/ui/` propio (ya existe base shadcn-style) — NO instalar template. Evaluar `reka-ui` solo para primitivas accesibles que falten.
- **Estado servidor**: Pinia actual resuelve; TanStack Query solo si polling/cache demuestra límite.
- **Charts**: chart.js+vue-chartjs presente → ECharts solo si se requiere interactividad financiera avanzada.
- **Gráficos de pipelines**: Vue Flow evaluar cuando Execution Studio lo necesite.
- **Browser automation**: Playwright autorizado, nunca evasión.
- **MCP**: SDK oficial v2 (verificar breaking vs v1) — un solo SDK, no FastMCP también.
- **Filas que NO se tocan**: ORION infra frozen; no borrar nada del trabajo del agente twin-tree.

## Riesgos críticos registrados

1. **Pérdida del live pipeline**: `cores/opportunity/{live_pipeline,live_connections,revenue_ledger,sources_expansion,adapters/security}` — 456 oportunidades + toda la lógica de revenue — en paquete marcado para borrado. Acción: migración atómica a `core/opportunity/` post-consolidación.
2. **Estado de git envenenado**: stash-pop conflict sin resolver en worktree principal; index staged revierte commits recientes (rank route, .ai docs, tests, store). Commits en origin/main seguros; el agente debe reconciliar.
3. **pytest roto** por `database/models.py` duplicando tablas de `cores/learning/profile.py` (WIP del agente).
4. **Dispersión frontend**: 82 páginas con dashboards solapados — Fase 2 del megaprompt debe consolidar IA de información, no agregar páginas.
5. **Duplicación de schedulers** — posible doble ejecución de scans.

## Hallazgos frontend — design system (verificado 2026-11-19)

**Tres sistemas de tokens coexisten:**

| Sistema | Archivo | Estado | Contenido |
|---|---|---|---|
| `--ownex-*` | `src/design/tokens.css` (247 líneas) | **SSOT** — directivas owner ("CERO rojo", danger=azul) | Colores, tipografía, espaciado |
| `--bg/--accent/--glass/--glow/--text-*` | `src/styles/tesla-jarvis-theme.css` (597 líneas) | **CARGADO en main.ts, en uso real** | ~40 vars alternativas — accent rojo/azul, glow effects (contradice tokens.css) |
| `.ownex-*` classes + vars | `src/styles/ownex-theme.css` (525 líneas) | **MUERTO — no importado** | 139 clases ownex-* |

- Vars tesla-jarvis en uso: `--bg-primary`, `--accent-primary`, `--glass-*`, `--glow-*`, `--text-*` (~70 referencias en vue/ts). Vars `--ownex-*`: 26 distintas también en uso. **Dos namespaces de tokens activos en paralelo.**
- CSS muerto confirmado: `ownex-theme.css`, `special-effects.css`, `accessibility.css` — ningún import.
- **Familias de componentes duplicadas**: `ui/Button|Card|Badge|Input` canónicos (~60 usos) vs `ui/Ownex*` (12 archivos, self-styled con `<style>` scoped — renderizan bien, son familia alternativa legacy).
- Falsos positivos descartados: las 89 clases `ownex-*` "faltantes" pertenecen a los Ownex* components (scoped styles) o a vars `--ownex-*` — no hay rotura visual.
- **Deuda real**: consolidar tesla-jarvis → tokens.css requiere mapeo var-a-var + QA visual (NO hacer a ciegas — los valores no son idénticos, aliasing cambiaría la apariencia).

## Siguiente acción recomendada (dependency order)

1. Esperar/resolver consolidación twin-tree (agente) → índice limpio.
2. Migrar live pipeline `cores/` → `core/` atómicamente + redirects.
3. Correr suite completa → nuevo baseline verde.
4. Phase 2: design tokens + consolidación de navegación (Command Center como hub único).
5. Phase 4: Connection Manager operacional con 3-5 plataformas completas (HIT0).
