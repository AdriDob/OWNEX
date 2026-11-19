# OWNEX EVOLUTIONARY REFACTOR & INTEGRATION — Directiva vigente

> Estado: **ACTIVA** · 2026-11-19 · Complementa `.ai/REVENUE_FIRST_ENGINEERING.md` (que sigue siendo la directiva de prioridad económica suprema).
> Principio rector: **EVOLUCIÓN, NO REEMPLAZO.** Siempre construir sobre la base de código más reciente; nunca borrar trabajo válido.

## Reglas absolutas de preservación

1. **Base más reciente siempre**: inspeccionar git (status/branches/log/diff/PRs/worktrees) antes de modificar. `main` no se asume completo — determinar la base real desde commits remotos + locales + trabajo sin commitear.
2. **Prohibido**: `git reset --hard`, `git clean -fdx`, force push, borrar ramas, sobrescribir archivos sin comparar, reemplazar carpetas por templates, eliminar módulos "redundantes" sin demostrarlo, eliminar tests para verde, `--no-verify`, merges a ciegas.
3. **Trabajo local = válido hasta demostrar lo contrario.** No stashear automáticamente, no cambiar de rama sobre cambios sin inspección, no mezclar agentes sin control.
4. **Un solo frontend canónico.** No desarrollar frontends paralelos.
5. **`core/` vs `cores/`**: no asumir duplicación por nombre — comparar responsabilidades, imports y consumidores. La reconciliación exige mapa de dependencias + plan de migración + tests + rollback (ver `agent/twin-tree-consolidation`, ADR-0002).

## Ciclo operativo objetivo

Connect → Authenticate → Synchronize → Discover → Evaluate → Prepare → Execute → Review → Submit → Verify Acceptance → Track Payment → Receive → Reinvest.

Ninguna integración se considera completa con solo URL/ficha/botón inerte.

## Biblioteca de referencia — decisiones de adopción

**Adoptar como dependencia solo con necesidad demostrada. Referencias ≠ instalación.**

| Repo | Decisión | Uso |
|---|---|---|
| unovue/shadcn-vue | ADAPTAR | Base del design system propio (componentes selectivos, propiedad del código en repo) |
| unovue/reka-ui | ADOPTAR (vía shadcn-vue) | Primitivas accesibles headless |
| vbenjs/vue-vben-admin | REFERENCIA | Navegación/layout/permisos/i18n — nunca reemplazo |
| unovue/inspira-ui | REFERENCIA | Microinteracciones con moderación |
| lucide-icons/lucide | YA EN USO | Iconografía uniforme |
| vueuse/vueuse | EVALUAR | Composables — adoptar si cubre necesidad real sin duplicar Pinia |
| apache/echarts | ADOPTAR cuando haya dashboards financieros | Gráficos de portfolio/ingresos/riesgo |
| bcakmakoglu/vue-flow | EVALUAR | Solo si grafos de pipelines/agentes aportan de verdad |
| TanStack/query | EVALUAR | Server-state — solo si Pinia actual no resuelve cache/polling |
| FormKit | DIFERIR | Solo si formularios actuales fallan |
| hey-api/openapi-ts | EVALUAR | Cliente TS tipado desde OpenAPI si el contrato lo justifica |
| fastapi/full-stack-fastapi-template | REFERENCIA backend | Auth/tests/CI — NO importar su frontend React |
| sqlalchemy / alembic | MANTENER | Persistencia y migraciones incrementales |
| encode/httpx | YA EN USO | Cliente async de integraciones |
| hynek/structlog | EVALUAR | Logs estructurados si tracing lo requiere |
| playwright-python | ADOPTAR (acotado) | Automatización de navegador AUTORIZADA — nunca evadir CAPTCHA/MFA/ToS |
| modelcontextprotocol/python-sdk | ADOPTAR (v2 estable) | MCP — verificar major version antes de usar ejemplos v1 |
| PrefectHQ/fastmcp | ELEGIR UNO | SDK oficial vs FastMCP — no acumular ambos sin motivo |
| taskiq / temporal | DIFERIR | Solo si scheduler actual demuestra límite real |
| Hypothesis | ADOPTAR (tests) | Property-based testing en lógica crítica |
| semgrep / gitleaks / bandit | ADOPTAR (CI) | Análisis estático + detección de secretos |
| tauri v2 + plugins-workspace | MANTENER | Desktop — permisos mínimos |
| ccxt | ADOPTAR (scoped) | Datos crypto — trading real deshabilitado por defecto |
| openbq-org/OpenBB | REFERENCIA | Ojo: migró de organización (OpenBB → openbq-org) |
| freqtrade / nautilus_trader | REFERENCIA | Arquitectura de bots/backtesting — no dependencia central |
| FastAPI Users | RECHAZAR | Mantenimiento — no usar como base de auth |

## Arquitectura de integración (contrato por provider)

Cada adapter declara: `provider_id`, `category`, `auth_type`, `required_credentials`, `connection_state`, `capabilities` (discovery, authenticated_sync, browser_sync, email_sync, webhook_sync, task_creation, execution_support, submission_support, acceptance_tracking, payment_tracking, withdrawal_support), `country_eligibility`, `payment_methods`, `last_sync_at`, `last_error`, `integration_maturity`.

Ciclo de vida: registrar → validar metadata → onboarding → conectar (auth real) → verificar identidad → sincronizar → normalizar → deduplicar → provenance → modelo canónico → Work Bank → operaciones permitidas → evidencia → monitoreo.

Sin API ≠ inútil (browser autorizado, MCP, email, webhooks, manual guiado) — pero debe declarar honestamente qué se puede automatizar.

## Fases (incrementales, nunca big-bang)

- **P0** Preservación de estado + baseline (git, tests, worktrees).
- **P1** Auditoría arquitectura/integraciones (mapa, capability matrix, risk register).
- **P2** UX/UI — design system propio (tokens, semántica, densidad profesional oscura-first).
- **P3** Command Center + Work Bank conectados a datos reales.
- **P4** Connection Manager operacional (pocas integraciones completas > cientos superficiales).
- **P5** Work Execution Studio (workspace → código → tests → review → aprobación → entrega).
- **P6** Payment/Financial Hub con evidencia.
- **P7** Investment Hub (datos → portfolio → paper trading; real-money gated).
- **P8** Automatización/agentes (consolidar paths duplicados solo tras entenderlos).
- **P9** Seguridad/confiabilidad/performance (pipeline completo).
- **P10** Aceptación end-to-end de journeys reales.

## Clasificación de capacidades (obligatoria en auditorías)

`implemented+tested` · `implemented, insufficient tests` · `partial` · `simulated/mocked` · `planned` · `broken` · `unknown`. Un adapter registrado sin ser llamado NO es integración operacional. Un test con mocks NO prueba el servicio real.

## Estado del repo al activar esta directiva (2026-11-19)

- `main` = `0d8a9deb` (pusheado). Live pipeline + revenue ledger + scoring + frontend panel en `cores/opportunity/` y `core/`.
- Worktree `/home/adriel/projects/rastro-twin-tree` en branch `agent/twin-tree-consolidation` (`2d8013f1`) — codemod fase-1 + ADR-0002.
- Worktree principal en **estado de conflicto sin resolver**: 24 unmerged entries + 164 borrados staged de `cores/*` + `database/models.py` con tablas duplicadas (colisión `investigator_profiles`). pytest roto repo-wide hasta que se resuelva. Preservar — no tocar.
- Ingreso verificado: **USD 0.00**.
